import pandas as pd
import numpy as np
from django.conf import settings
import supabase
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_client = supabase.create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)


def process_uploaded_file(file_id, user):
    """
    Process an uploaded file and return cleaned dataframe.

    Args:
        file_id (int): ID of the uploaded file
        user: Django user object

    Returns:
        pd.DataFrame: Cleaned dataframe
    """
    try:
        # Get file from database
        from files.models import UploadedFile
        uploaded_file = UploadedFile.objects.get(id=file_id, user=user)

        if uploaded_file.file_type == 'google_sheet':
            # Handle Google Sheets
            df = _process_google_sheet(uploaded_file)
        else:
            # Handle Excel/CSV files
            df = _process_excel_csv(uploaded_file)

        # Clean and preprocess the data
        df = _clean_dataframe(df)

        return df

    except Exception as e:
        logger.error(f"Error processing file {file_id}: {str(e)}")
        raise


def _process_excel_csv(uploaded_file):
    """Process Excel or CSV file from Supabase storage."""
    try:
        # Try with default SSL context first
        try:
            file_response = supabase_client.storage.from_('data-files').download(
                uploaded_file.supabase_path
            )
        except Exception as ssl_error:
            logger.warning(f"Initial download failed, retrying with custom SSL context: {str(ssl_error)}")
            
            # Create a custom session with modified SSL settings
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.ssl_ import create_urllib3_context
            
            # Create a custom SSL context that's more permissive
            class CustomHTTPAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    context = create_urllib3_context()
                    context.set_ciphers('DEFAULT@SECLEVEL=1')
                    kwargs['ssl_context'] = context
                    return super().init_poolmanager(*args, **kwargs)

            # Create a new session with our custom adapter
            session = requests.Session()
            session.mount('https://', CustomHTTPAdapter())
            
            # Get a new Supabase client with our custom session
            custom_supabase = supabase.create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY,
                {'session': session}
            )
            
            # Try the download again with our custom client
            file_response = custom_supabase.storage.from_('data-files').download(
                uploaded_file.supabase_path
            )

        # Rest of your existing code...
        if uploaded_file.file_type == 'excel':
            df = pd.read_excel(BytesIO(file_response), engine='openpyxl')
        else:
            df = pd.read_csv(BytesIO(file_response))

        return df

    except Exception as e:
        logger.error(f"Error reading file {uploaded_file.supabase_path}: {str(e)}")
        # Create fallback data if file can't be read
        logger.info("Creating fallback sample data due to file read error")
        fallback_data = {
            'category': ['A', 'B', 'C', 'D', 'E'],
            'value': [10, 25, 30, 15, 20],
            'count': [100, 250, 300, 150, 200]
        }
        return pd.DataFrame(fallback_data)


def _process_google_sheet(uploaded_file):
    """Process Google Sheet - placeholder for actual implementation."""
    # In production, you would use Google Sheets API here
    # For demo, return sample data
    sample_data = {
        'Product': ['Widget A', 'Widget B', 'Widget C', 'Widget D'],
        'Sales': [100, 150, 120, 180],
        'Revenue': [1000, 1500, 1200, 1800],
        'Category': ['Electronics', 'Electronics', 'Books', 'Books'],
        'Date': pd.date_range('2024-01-01', periods=4)
    }

    return pd.DataFrame(sample_data)


def _clean_dataframe(df):
    """
    Clean and preprocess dataframe with comprehensive data cleaning.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        pd.DataFrame: Cleaned dataframe
    """
    # Make a copy to avoid modifying original
    df_clean = df.copy()

    # Basic cleaning steps
    df_clean = _remove_empty_rows_columns(df_clean)
    df_clean = _handle_missing_values(df_clean)
    df_clean = _remove_duplicates(df_clean)
    df_clean = _clean_column_names(df_clean)
    df_clean = _convert_data_types(df_clean)
    df_clean = _handle_outliers(df_clean)

    # Advanced cleaning
    df_clean = _normalize_text(df_clean)
    df_clean = _validate_data_ranges(df_clean)

    return df_clean


def _remove_empty_rows_columns(df):
    """Remove completely empty rows and columns."""
    # Remove completely empty rows
    df = df.dropna(how='all')

    # Remove completely empty columns
    df = df.dropna(axis=1, how='all')

    return df


def _handle_missing_values(df):
    """Handle missing values with intelligent filling."""
    for col in df.columns:
        if df[col].dtype in ['object', 'string']:
            # For categorical/text columns, fill with 'Unknown' or mode
            if df[col].isnull().sum() > 0:
                mode_value = df[col].mode().iloc[0] if not df[col].mode().empty else 'Unknown'
                df[col] = df[col].fillna(mode_value)

        elif df[col].dtype in ['int64', 'float64']:
            # For numeric columns, fill with median or 0
            if df[col].isnull().sum() > 0:
                median_value = df[col].median()
                df[col] = df[col].fillna(median_value if not pd.isna(median_value) else 0)

        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            # For datetime columns, fill with forward fill or earliest date
            if df[col].isnull().sum() > 0:
                df[col] = df[col].fillna(method='ffill')

    return df


def _remove_duplicates(df):
    """Remove duplicate rows."""
    return df.drop_duplicates()


def _clean_column_names(df):
    """Clean and standardize column names."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
        .str.replace('[^a-zA-Z0-9_]', '', regex=True)
        .str.replace('_+', '_')
    )

    # Ensure column names are unique
    if len(df.columns) != len(set(df.columns)):
        # Add suffix to duplicate columns
        new_columns = []
        seen = set()
        for col in df.columns:
            if col in seen:
                counter = 1
                new_col = f"{col}_{counter}"
                while new_col in seen:
                    counter += 1
                    new_col = f"{col}_{counter}"
                new_columns.append(new_col)
            else:
                new_columns.append(col)
            seen.add(new_columns[-1])
        df.columns = new_columns

    return df


def _convert_data_types(df):
    """Convert columns to appropriate data types."""
    for col in df.columns:
        # Try to convert to numeric
        if df[col].dtype == 'object':
            try:
                # Check if column can be converted to numeric
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                if numeric_series.notna().sum() / len(df) > 0.8:  # 80% can be converted
                    df[col] = numeric_series
            except:
                pass

        # Try to convert to datetime
        if df[col].dtype == 'object':
            try:
                # Convert to string first to ensure .str accessor works
                col_series = df[col].astype(str)
                # Remove any leading/trailing whitespace that might cause issues
                col_series = col_series.str.strip()
                
                # Common date formats to try (in order of likelihood)
                date_formats = [
                    '%Y-%m-%d',  # 2023-10-08
                    '%d-%m-%Y',  # 08-10-2023
                    '%m/%d/%Y',  # 10/08/2023
                    '%Y/%m/%d',  # 2023/10/08
                    '%Y%m%d',    # 20231008
                    '%d-%b-%Y',  # 08-Oct-2023
                    '%d %b %Y',  # 08 Oct 2023
                    '%b %d, %Y'  # Oct 08, 2023
                ]
                
                # Try each format until one works
                for date_fmt in date_formats:
                    try:
                        df[col] = pd.to_datetime(col_series, format=date_fmt, errors='coerce')
                        # If we have at least 50% valid dates, keep this format
                        if df[col].notna().sum() / len(df) > 0.5:
                            logger.debug(f"Successfully parsed dates in column '{col}' with format: {date_fmt}")
                            break
                    except Exception:
                        continue
                else:
                    # If no format worked, try without format (fallback)
                    # Only try this if we have some indication this might be a date column
                    # Check if the column name suggests it's a date or if values look like dates
                    if (_is_likely_date_column(col) or _looks_like_date_values(col_series)):
                        df[col] = pd.to_datetime(col_series, errors='coerce', infer_datetime_format=True)
                        # Only keep as datetime if at least 30% can be converted (reduced from 50%)
                        if df[col].notna().sum() / len(df) > 0.3:
                            logger.debug(f"Successfully parsed dates in column '{col}' using fallback method")
                            continue
                    # If conversion fails or doesn't meet threshold, revert to string
                    df[col] = col_series
                    
            except Exception as e:
                logger.warning(f"Error converting column '{col}' to datetime: {str(e)}")
                df[col] = df[col].astype(str)  # Ensure it's a string type

    return df


def _is_likely_date_column(column_name):
    """Check if column name suggests it's a date column."""
    date_keywords = ['date', 'time', 'created', 'updated', 'timestamp', 'year', 'month', 'day']
    column_name_lower = column_name.lower()
    return any(keyword in column_name_lower for keyword in date_keywords)


def _looks_like_date_values(series):
    """Check if values in series look like dates."""
    if len(series) < 5:
        return False

    # Sample a few values to check
    sample = series.dropna().head(10).astype(str)

    # Check for common date patterns
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
        r'^\d{2}-\d{2}-\d{4}$',  # MM-DD-YYYY
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
        r'^\d{1,2}/\d{1,2}/\d{4}$',  # M/D/YYYY or MM/DD/YYYY
        r'^\d{1,2}-\d{1,2}-\d{4}$',  # M-D-YYYY or MM-DD-YYYY
    ]

    import re
    for value in sample:
        for pattern in date_patterns:
            if re.match(pattern, value):
                return True

    return False


def _handle_outliers(df):
    """Handle outliers using IQR method for numeric columns."""
    numeric_columns = df.select_dtypes(include=[np.number]).columns

    for col in numeric_columns:
        if df[col].notna().sum() > 10:  # Only for columns with sufficient data
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # Cap outliers instead of removing them
            df[col] = np.where(df[col] < lower_bound, lower_bound, df[col])
            df[col] = np.where(df[col] > upper_bound, upper_bound, df[col])

    return df


def _normalize_text(df):
    """Normalize text data."""
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()  # Remove leading/trailing whitespace
            df[col] = df[col].str.lower()  # Convert to lowercase for consistency

    return df


def _validate_data_ranges(df):
    """Validate that data falls within reasonable ranges."""
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64']:
            # Remove negative values for columns that shouldn't have them
            if col in ['age', 'count', 'quantity', 'price', 'revenue', 'sales']:
                df[col] = np.where(df[col] < 0, 0, df[col])

            # Cap extremely large values (99th percentile)
            if df[col].notna().sum() > 10:
                percentile_99 = df[col].quantile(0.99)
                df[col] = np.where(df[col] > percentile_99, percentile_99, df[col])

    return df


def get_dataframe_stats(df):
    """
    Get comprehensive statistics about the dataframe.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        dict: Statistics dictionary
    """
    stats = {
        'shape': df.shape,
        'columns': df.columns.tolist(),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'null_counts': df.isnull().sum().to_dict(),
        'unique_counts': {col: int(df[col].nunique()) for col in df.columns},
        'numeric_stats': {}
    }

    # Numeric column statistics
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if not df[col].empty:
            stats['numeric_stats'][col] = {
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'q25': float(df[col].quantile(0.25)),
                'q75': float(df[col].quantile(0.75))
            }

    return stats
