import os
import logging
import pandas as pd
import json
import requests

# Configure logger
logger = logging.getLogger(__name__)
from io import BytesIO
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import supabase
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .models import UploadedFile, FileProcessing
from celery import shared_task

# Initialize Supabase client
def get_supabase_client():
    try:
        client = supabase.create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY
        )
        return client
    except Exception as e:
        logging.error(f"Error initializing Supabase client: {str(e)}")
        raise

from rest_framework.decorators import authentication_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_file(request):
    """Upload Excel/CSV file to Supabase storage."""
    logger = logging.getLogger(__name__)
    logger.info("File upload request received")
    
    try:
        if 'file' not in request.FILES:
            logger.error("No file provided in request")
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name
        file_size = uploaded_file.size
        logger.info(f"Processing file: {file_name}, size: {file_size} bytes")

        # Validate file type
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        file_extension = os.path.splitext(file_name)[1].lower()

        if file_extension not in allowed_extensions:
            logger.error(f"Invalid file extension: {file_extension}")
            return Response(
                {'error': 'Only Excel (.xlsx, .xls) and CSV files are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            logger.error(f"File size {file_size} exceeds maximum allowed size {max_size}")
            return Response(
                {'error': 'File size must be less than 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate unique filename using user's ID or a unique identifier
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        user_identifier = str(getattr(request.user, 'supabase_id', request.user.id))
        unique_filename = f"{user_identifier}_{timestamp}_{file_name}"
        logger.info(f"Generated unique filename: {unique_filename}")

        try:
            # Read file content
            file_content = uploaded_file.read()
            logger.info("File content read successfully")
            
            # Get Supabase client and upload file to bucket
            supabase_client = get_supabase_client()
            logger.info("Supabase client initialized")
            
            # Check if bucket exists, create if not
            try:
                bucket_name = 'data-files'
                bucket_response = supabase_client.storage.from_(bucket_name).upload(
                    unique_filename,
                    file_content,
                    {"content-type": uploaded_file.content_type}
                )
                logger.info(f"File uploaded to Supabase: {bucket_response}")
                
            except Exception as upload_error:
                logger.error(f"Error uploading to Supabase: {str(upload_error)}")
                # Try to create the bucket if it doesn't exist
                if "Bucket not found" in str(upload_error):
                    try:
                        logger.info(f"Creating bucket: {bucket_name}")
                        supabase_client.storage.create_bucket(bucket_name, public=True)
                        logger.info(f"Bucket {bucket_name} created")
                        # Retry upload after creating bucket
                        bucket_response = supabase_client.storage.from_(bucket_name).upload(
                            unique_filename,
                            file_content,
                            {"content-type": uploaded_file.content_type}
                        )
                        logger.info(f"File uploaded to Supabase after bucket creation: {bucket_response}")
                    except Exception as bucket_error:
                        logger.error(f"Failed to create bucket: {str(bucket_error)}")
                        return Response(
                            {'error': f'Failed to create storage bucket: {str(bucket_error)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                else:
                    raise upload_error

            # Determine file type
            if file_extension in ['.xlsx', '.xls']:
                file_type = 'excel'
            else:
                file_type = 'csv'

            # Save file metadata to database
            uploaded_file_obj = UploadedFile.objects.create(
                user=request.user,
                file_name=unique_filename,
                original_name=file_name,
                file_type=file_type,
                file_size=file_size,
                supabase_path=unique_filename,
                mime_type=uploaded_file.content_type
            )
            logger.info(f"File metadata saved to database with ID: {uploaded_file_obj.id}")

            # Get public URL for the uploaded file
            try:
                file_url = supabase_client.storage.from_(bucket_name).get_public_url(unique_filename)
                logger.info(f"Generated public URL: {file_url}")
            except Exception as url_error:
                logger.error(f"Error generating public URL: {str(url_error)}")
                file_url = None
            
            # Mark the file as processed immediately
            uploaded_file_obj.is_processed = True
            uploaded_file_obj.save()
            
            return Response({
                'message': 'File uploaded successfully',
                'file_id': str(uploaded_file_obj.id),
                'filename': unique_filename,
                'file_url': file_url,
                'supabase_path': f"{bucket_name}/{unique_filename}",
                'status': 'completed',
                'is_processed': True
            }, status=status.HTTP_201_CREATED)

        except Exception as upload_error:
            logger.error(f"Error during file upload: {str(upload_error)}", exc_info=True)
            return Response(
                {'error': f'Error during file upload: {str(upload_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Unexpected error in upload_file: {str(e)}", exc_info=True)
        return Response(
            {'error': f'An unexpected error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except Exception as e:
        return Response(
            {'error': f'Upload failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def connect_google_sheet(request):
    """Connect to Google Sheets and save sheet data."""
    sheet_url = request.data.get('sheet_url')
    sheet_name = request.data.get('sheet_name', 'Sheet1')

    if not sheet_url:
        return Response(
            {'error': 'Google Sheet URL is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Extract sheet ID from URL
        if 'docs.google.com/spreadsheets' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        else:
            return Response(
                {'error': 'Invalid Google Sheet URL format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # For demo purposes, we'll create a placeholder record
        # In production, you'd implement OAuth2 and API calls to Google Sheets
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{request.user.id}_{timestamp}_google_sheet_{sheet_id}"

        # Create file record for Google Sheet
        uploaded_file_obj = UploadedFile.objects.create(
            user=request.user,
            file_name=unique_filename,
            original_name=f"Google Sheet - {sheet_id}",
            file_type='google_sheet',
            file_size=0,  # Unknown size for Google Sheets
            supabase_path=unique_filename,
            mime_type='application/vnd.google-apps.spreadsheet'
        )

        # Create processing record
        FileProcessing.objects.create(file=uploaded_file_obj)

        return Response({
            'message': 'Google Sheet connected successfully',
            'file_id': uploaded_file_obj.id,
            'sheet_id': sheet_id,
            'status': 'processing'
        })

    except Exception as e:
        return Response(
            {'error': f'Connection failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_files(request):
    """List all uploaded files for the current user."""
    files = UploadedFile.objects.filter(user=request.user)
    file_data = []

    for file in files:
        processing = FileProcessing.objects.filter(file=file).first()

        file_data.append({
            'id': file.id,
            'file_name': file.original_name,
            'file_type': file.file_type,
            'file_size': file.file_size,
            'uploaded_at': file.uploaded_at,
            'is_processed': file.is_processed,
            'processing_status': processing.status if processing else 'unknown',
            'row_count': processing.row_count if processing else None,
            'column_count': processing.column_count if processing else None,
        })

    return Response({'files': file_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_file_preview(request, file_id):
    """Get preview of processed file data."""
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)
        processing = FileProcessing.objects.filter(file=uploaded_file).first()

        if not processing or not processing.data_preview:
            return Response(
                {'error': 'File not processed yet'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'file_name': uploaded_file.original_name,
            'data_preview': processing.data_preview,
            'row_count': processing.row_count,
            'column_count': processing.column_count,
        })

    except UploadedFile.DoesNotExist:
        return Response(
            {'error': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_file(request, file_id):
    """Delete uploaded file and its data."""
    try:
        # Get the file from the database
        uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)
        
        try:
            # Get Supabase client and delete the file from storage
            supabase_client = get_supabase_client()
            # Delete the file from Supabase storage
            try:
                supabase_client.storage.from_('data-files').remove([uploaded_file.supabase_path])
            except Exception as e:
                print(f"Error deleting file from storage: {str(e)}")
                # Continue with database cleanup even if file deletion from storage fails
        except Exception as e:
            print(f"Error initializing Supabase client: {str(e)}")
            # Continue with database cleanup even if Supabase client fails

        # Delete database records
        FileProcessing.objects.filter(file=uploaded_file).delete()
        uploaded_file.delete()

        return Response({'message': 'File deleted successfully'})

    except UploadedFile.DoesNotExist:
        return Response(
            {'error': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Error deleting file: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
