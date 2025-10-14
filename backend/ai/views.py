from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import json
import uuid
import logging
from .models import ChatSession, ChatMessage, Dashboard, DashboardExport
from ml_models.model import query_llama
from ml_models.sql_generator import generate_sql
from ml_models.db_adapter import execute_query
from ml_models.insights_extractor import extract_insights
from ml_models.dashboard_generator import generate_dashboard
from ml_models.dashboard_exporter import export_dashboard

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handle chat queries and return responses."""
    message = request.data.get('message')
    file_id = request.data.get('file_id')
    session_id = request.data.get('session_id')

    if not message or not file_id:
        return Response(
            {'error': 'Message and file_id are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get or create chat session
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return Response(
                    {'error': 'Chat session not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            session = ChatSession.objects.create(user=request.user)

        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            message=message,
            is_user=True
        )

        # Generate SQL from natural language
        sql_query = generate_sql(message, file_id, request.user)

        if not sql_query:
            ai_response = "I'm sorry, I couldn't generate a valid query from your request. Please try rephrasing your question."

            # Save AI response
            ChatMessage.objects.create(
                session=session,
                message=ai_response,
                is_user=False
            )

            return Response({
                'response': ai_response,
                'session_id': session.id,
                'sql_query': None,
                'data': None
            })

        # Execute query
        query_results = execute_query(sql_query, file_id, request.user)

        if query_results is None:
            ai_response = "I generated a query but couldn't execute it. Please check your data and try again."

            # Save AI response
            ChatMessage.objects.create(
                session=session,
                message=ai_response,
                is_user=False
            )

            return Response({
                'response': ai_response,
                'session_id': session.id,
                'sql_query': sql_query,
                'data': None
            })

        # Generate AI response
        ai_response = query_llama(f"Based on this data: {str(query_results[:5]) if len(query_results) > 5 else str(query_results)}, explain the results of this query: {message}")

        # Save AI response
        ChatMessage.objects.create(
            session=session,
            message=ai_response,
            is_user=False
        )

        return Response({
            'response': ai_response,
            'session_id': session.id,
            'sql_query': sql_query,
            'data': query_results[:100]  # Limit to first 100 rows for response
        })

    except Exception as e:
        return Response(
            {'error': f'Chat processing failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_dashboard_view(request):
    """Generate dashboard with insights and visualizations."""
    file_id = request.data.get('file_id')
    query = request.data.get('query', 'Analyze the data and provide insights')
    theme = request.data.get('theme', {
        'colors': {
            'text': '#333333',
            'chart': '#1f77b4',
            'background': '#ffffff'
        }
    })

    if not file_id:
        return Response(
            {'error': 'file_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Extract insights from the data
        try:
            insights = extract_insights(file_id, query, request.user)
        except Exception as e:
            logger.error(f"Error extracting insights: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to extract insights: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Generate dashboard with insights
        try:
            dashboard_data = generate_dashboard(file_id, query, insights, theme, request.user)
            
            # Debug logging for chart data structure
            if 'sections' in dashboard_data:
                for section in dashboard_data['sections']:
                    if section.get('type') == 'charts_section':
                        logger.info(f"Chart section found with {len(section.get('charts', []))} charts")
                        for i, chart in enumerate(section.get('charts', [])):
                            logger.info(f"Chart {i + 1}:")
                            logger.info(f"  Title: {chart.get('title')}")
                            logger.info(f"  Data length: {len(chart.get('data', []))}")
                            logger.info(f"  Data structure: {chart.get('data')}")

        except Exception as e:
            logger.error(f"Error generating dashboard: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to generate dashboard: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Save dashboard
        try:
            dashboard = Dashboard.objects.create(
                user=request.user,
                file_id=file_id,
                query=query,
                dashboard_data=dashboard_data,
                theme=theme
            )
        except Exception as e:
            logger.error(f"Error saving dashboard: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to save dashboard: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Debug: Log chart data lengths
        if dashboard_data and 'sections' in dashboard_data:
            for section in dashboard_data['sections']:
                if section.get('type') == 'charts_section' and 'charts' in section:
                    for chart in section['charts']:
                        logger.debug(f"Chart title: {chart.get('title')}, data length: {len(chart.get('data', []))}")
                        # If chart data is empty, add a warning
                        if not chart.get('data') or len(chart.get('data')) == 0:
                            chart['title'] = chart.get('title', 'Chart') + ' (No Data)'
                            chart['layout'] = chart.get('layout', {})
                            chart['layout']['annotations'] = [{
                                'text': 'No data available',
                                'xref': 'paper',
                                'yref': 'paper',
                                'showarrow': False,
                                'font': {'size': 18, 'color': 'red'},
                                'x': 0.5,
                                'y': 0.5
                            }]
        return Response({
            'dashboard_id': dashboard.id,
            'dashboard_data': dashboard_data,
            'insights': insights
        })

    except Exception as e:
        logger.error(f"Unexpected error in dashboard generation: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Dashboard generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_view(request, dashboard_id):
    """Get existing dashboard data."""
    try:
        dashboard = Dashboard.objects.get(id=dashboard_id, user=request.user)
        return Response({
            'dashboard_id': dashboard.id,
            'dashboard_data': dashboard.dashboard_data,
            'theme': dashboard.theme,
            'created_at': dashboard.created_at
        })

    except Dashboard.DoesNotExist:
        return Response(
            {'error': 'Dashboard not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_dashboard_view(request, dashboard_id):
    """Export dashboard as PDF or image."""
    export_format = request.data.get('format', 'pdf')  # pdf, png, html

    try:
        dashboard = Dashboard.objects.get(id=dashboard_id, user=request.user)

        # Generate export link (now returns Supabase public URL directly)
        export_link = export_dashboard(dashboard, export_format)

        # Since we're using Supabase storage, the export_link is already a complete public URL
        # No need to build absolute URI as it's already from Supabase

        # Save export record
        export_record = DashboardExport.objects.create(
            dashboard=dashboard,
            format=export_format,
            export_link=export_link or ''
        )

        return Response({
            'export_id': export_record.id,
            'export_link': export_link,
            'format': export_format
        })

    except Dashboard.DoesNotExist:
        return Response(
            {'error': 'Dashboard not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Export failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_dashboard_to_supabase_view(request, dashboard_id):
    """Save dashboard to Supabase storage for persistence across sessions."""
    try:
        dashboard = Dashboard.objects.get(id=dashboard_id, user=request.user)
        
        # Get Supabase client
        from ml_models.dashboard_exporter import get_supabase_client
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'
        
        # Generate unique filename with user identifier
        import pandas as pd
        import json
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        user_id = getattr(request.user, 'id', 'unknown')
        filename = f"dashboard_{user_id}_{dashboard_id}_{timestamp}.json"
        
        # Convert dashboard data to JSON
        dashboard_json = json.dumps({
            'dashboard_id': dashboard.id,
            'dashboard_data': dashboard.dashboard_data,
            'theme': dashboard.theme,
            'created_at': dashboard.created_at.isoformat() if dashboard.created_at else None,
            'updated_at': dashboard.updated_at.isoformat() if dashboard.updated_at else None,
            'file_id': dashboard.file_id,
            'query': dashboard.query
        }, indent=2)
        
        # Upload to Supabase storage
        try:
            upload_response = supabase_client.storage.from_(bucket_name).upload(
                filename,
                dashboard_json.encode('utf-8'),
                {"content-type": "application/json"}
            )
            logger.info(f"Dashboard saved to Supabase: {upload_response}")
        except Exception as upload_error:
            logger.error(f"Error uploading dashboard to Supabase: {str(upload_error)}")
            # Try to create the bucket if it doesn't exist
            if "Bucket not found" in str(upload_error):
                try:
                    logger.info(f"Creating bucket: {bucket_name}")
                    supabase_client.storage.create_bucket(bucket_name, public=False)
                    logger.info(f"Bucket {bucket_name} created")
                    
                    # Retry upload after creating bucket
                    upload_response = supabase_client.storage.from_(bucket_name).upload(
                        filename,
                        dashboard_json.encode('utf-8'),
                        {"content-type": "application/json"}
                    )
                    logger.info(f"Dashboard saved to Supabase after bucket creation: {upload_response}")
                except Exception as bucket_error:
                    logger.error(f"Failed to create bucket: {str(bucket_error)}")
                    return Response(
                        {'error': f'Failed to create storage bucket: {str(bucket_error)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                raise upload_error

        # Get public URL for the uploaded file (though it's private)
        try:
            file_url = supabase_client.storage.from_(bucket_name).get_public_url(filename)
            logger.info(f"Generated file URL: {file_url}")
        except Exception as url_error:
            logger.error(f"Error generating file URL: {str(url_error)}")
            file_url = None

        return Response({
            'message': 'Dashboard saved successfully',
            'file_name': filename,
            'file_url': file_url
        })

    except Dashboard.DoesNotExist:
        return Response(
            {'error': 'Dashboard not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error saving dashboard to Supabase: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to save dashboard: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_dashboards_view(request):
    """List all dashboards saved in Supabase storage for the current user."""
    try:
        # Get Supabase client
        from ml_models.dashboard_exporter import get_supabase_client
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'
        
        # List files in the bucket for the current user
        user_id = getattr(request.user, 'id', 'unknown')
        try:
            # List all dashboard files for this user
            response = supabase_client.storage.from_(bucket_name).list()
            user_dashboards = []
            
            if response:
                for file_info in response:
                    filename = file_info.get('name', '')
                    if filename.startswith(f'dashboard_{user_id}_'):
                        user_dashboards.append({
                            'file_name': filename,
                            'created_at': file_info.get('created_at'),
                            'updated_at': file_info.get('updated_at'),
                            'id': filename  # Use filename as ID
                        })
            
            return Response({
                'dashboards': user_dashboards
            })
            
        except Exception as list_error:
            logger.error(f"Error listing dashboards: {str(list_error)}")
            return Response(
                {'error': f'Failed to list dashboards: {str(list_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error listing user dashboards: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to list dashboards: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def load_user_dashboard_view(request, filename):
    """Load a specific dashboard from Supabase storage for the current user."""
    try:
        # Get Supabase client
        from ml_models.dashboard_exporter import get_supabase_client
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'
        
        # Download the dashboard file
        try:
            # Download the file content
            file_content = supabase_client.storage.from_(bucket_name).download(filename)
            
            # Parse the JSON content
            import json
            saved_data = json.loads(file_content.decode('utf-8'))
            
            # Return the dashboard data structure directly
            return Response({
                'dashboard_data': saved_data['dashboard_data'],
                'file_id': saved_data.get('file_id'),
                'theme': saved_data.get('theme')
            })
            
        except Exception as download_error:
            logger.error(f"Error downloading dashboard: {str(download_error)}")
            return Response(
                {'error': f'Failed to download dashboard: {str(download_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error loading user dashboard: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to load dashboard: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
