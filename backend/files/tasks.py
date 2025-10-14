import os
import pandas as pd
import numpy as np
from io import BytesIO
from celery import shared_task
from django.conf import settings
import supabase
from .models import UploadedFile, FileProcessing

# Initialize Supabase client
supabase_client = supabase.create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)


@shared_task
def process_file_async(file_id):
    """Async task to process uploaded files."""
    try:
        # Get file record
        uploaded_file = UploadedFile.objects.get(id=file_id)

        # Update status to processing
        processing = FileProcessing.objects.get(file=uploaded_file)
        processing.status = 'processing'
        processing.save()

        if uploaded_file.file_type == 'google_sheet':
            # Process Google Sheet
            success = process_google_sheet(uploaded_file, processing)
        else:
            # Process Excel/CSV file
            success = process_excel_csv(uploaded_file, processing)

        if success:
            # Refresh the uploaded_file instance to get the latest data
            uploaded_file.refresh_from_db()
            uploaded_file.is_processed = True
            uploaded_file.save(update_fields=['is_processed'])
            
            # Ensure processing status is marked as completed
            processing = FileProcessing.objects.get(file=uploaded_file)
            if processing.status != 'completed':
                processing.status = 'completed'
                processing.save(update_fields=['status'])

    except Exception as e:
        # Update status to failed
        processing = FileProcessing.objects.get(file_id=file_id)
        processing.status = 'failed'
        processing.error_message = str(e)
        processing.save()


def process_excel_csv(uploaded_file, processing):
    """Process Excel or CSV file."""
    try:
        # Download file from Supabase
        file_response = supabase_client.storage.from_('data-files').download(
            uploaded_file.supabase_path
        )

        # Read file content
        if uploaded_file.file_type == 'excel':
            df = pd.read_excel(BytesIO(file_response))
        else:
            df = pd.read_csv(BytesIO(file_response))

        # Clean data
        df = clean_dataframe(df)

        # Get basic stats
        row_count, column_count = df.shape

        # Create data preview (first 100 rows, sample columns)
        preview_data = df.head(100).to_dict('records')

        # Update processing record
        processing.status = 'completed'
        processing.row_count = row_count
        processing.column_count = column_count
        processing.data_preview = {
            'columns': df.columns.tolist(),
            'data': preview_data,
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'null_counts': df.isnull().sum().to_dict(),
            'unique_counts': {col: int(df[col].nunique()) for col in df.columns[:10]}  # First 10 columns
        }
        processing.processed_at = pd.Timestamp.now()
        processing.save()

        return True

    except Exception as e:
        processing.status = 'failed'
        processing.error_message = str(e)
        processing.save()
        return False


def process_google_sheet(uploaded_file, processing):
    """Process Google Sheet - placeholder implementation."""
    # In a real implementation, you would:
    # 1. Use Google Sheets API to read the sheet
    # 2. Convert to DataFrame
    # 3. Process the data

    # For demo, create sample data
    sample_data = {
        'Name': ['Alice', 'Bob', 'Charlie', 'Diana'],
        'Age': [25, 30, 35, 28],
        'City': ['New York', 'London', 'Tokyo', 'Paris'],
        'Salary': [50000, 60000, 55000, 65000]
    }

    df = pd.DataFrame(sample_data)

    # Get basic stats
    row_count, column_count = df.shape

    # Create data preview
    preview_data = df.head(100).to_dict('records')

    # Update processing record
    processing.status = 'completed'
    processing.row_count = row_count
    processing.column_count = column_count
    processing.data_preview = {
        'columns': df.columns.tolist(),
        'data': preview_data,
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'null_counts': df.isnull().sum().to_dict(),
        'unique_counts': {col: int(df[col].nunique()) for col in df.columns}
    }
    processing.processed_at = pd.Timestamp.now()
    processing.save()

    return True


def clean_dataframe(df):
    """Clean and preprocess dataframe."""
    # Remove completely empty rows
    df = df.dropna(how='all')

    # Fill missing values with appropriate defaults
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('Unknown')
        elif df[col].dtype in ['int64', 'float64']:
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna('Unknown')

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Basic column name cleaning
    df.columns = df.columns.str.strip().str.replace(' ', '_').str.lower()

    return df
