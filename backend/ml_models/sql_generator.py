import re
import json
import logging
from django.conf import settings
from .model import query_llama
from .files_processor import process_uploaded_file, get_dataframe_stats

logger = logging.getLogger(__name__)


def generate_sql(natural_query, file_id, user):
    """
    Generate SQL query from natural language using AI model.

    Args:
        natural_query (str): Natural language query
        file_id (int): ID of the uploaded file
        user: Django user object

    Returns:
        str: Generated SQL query or None if error
    """
    try:
        # Get dataframe and schema information
        df = process_uploaded_file(file_id, user)
        schema_info = get_dataframe_schema(df)

        # Use AI model to generate SQL
        sql_query = query_llama(
            _build_sql_generation_prompt(natural_query, schema_info),
            max_tokens=800
        )

        if sql_query:
            # Clean and validate the generated SQL
            cleaned_sql = _clean_generated_sql(sql_query)

            # Validate SQL against dataframe schema
            if _validate_sql_against_schema(cleaned_sql, schema_info):
                return cleaned_sql
            else:
                logger.warning(f"Generated SQL doesn't match schema: {cleaned_sql}")
                # Try fallback method
                return _generate_sql_fallback(natural_query, df)

        return None

    except Exception as e:
        logger.error(f"Error generating SQL for query '{natural_query}': {str(e)}")
        return None


def get_dataframe_schema(df):
    """
    Extract schema information from dataframe.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        dict: Schema information
    """
    schema = {
        'columns': [],
        'row_count': len(df),
        'column_count': len(df.columns),
        'dtypes': {}
    }

    for col in df.columns:
        col_info = {
            'name': col,
            'type': str(df[col].dtype),
            'unique_count': int(df[col].nunique()),
            'null_count': int(df[col].isnull().sum())
        }

        # Add sample values for context
        non_null_values = df[col].dropna()
        if len(non_null_values) > 0:
            if df[col].dtype in ['object', 'string']:
                sample_values = non_null_values.unique()[:5].tolist()
            else:
                sample_values = [float(x) for x in non_null_values.head(3).tolist()]
            col_info['sample_values'] = sample_values

        schema['columns'].append(col_info)
        schema['dtypes'][col] = str(df[col].dtype)

    return schema


def _build_sql_generation_prompt(natural_query, schema_info):
    """
    Build a comprehensive prompt for SQL generation.

    Args:
        natural_query (str): Natural language query
        schema_info (dict): Schema information

    Returns:
        str: Complete prompt for AI model
    """
    # Format schema for prompt
    columns_str = ""
    for col in schema_info['columns']:
        sample_vals = ""
        if 'sample_values' in col:
            sample_vals = f", sample values: {col['sample_values']}"

        columns_str += f"- {col['name']} ({col['type']}){sample_vals}\n"

    prompt = f"""You are a SQL expert. I need you to convert a natural language query into a valid SQL query.

Available data:
- Table name: 'data' (this is a pandas DataFrame)
- Total rows: {schema_info['row_count']}
- Columns:
{columns_str}

Natural language query: "{natural_query}"

Please generate a SQL query that answers this question. Consider:
1. Use appropriate column names (case-sensitive)
2. Apply proper filtering, grouping, and aggregation
3. Use standard SQL syntax
4. Return only the SQL query, no explanations or markdown

SQL Query:"""

    return prompt


def _clean_generated_sql(sql_query):
    """
    Clean and format the generated SQL query.

    Args:
        sql_query (str): Raw SQL from AI model

    Returns:
        str: Cleaned SQL query
    """
    if not sql_query:
        return None

    # Remove markdown formatting
    sql_query = re.sub(r'```sql\s*', '', sql_query)
    sql_query = re.sub(r'```\s*$', '', sql_query)

    # Remove leading/trailing whitespace
    sql_query = sql_query.strip()

    # Fix common issues
    # Ensure SELECT is uppercase
    sql_query = re.sub(r'\bselect\b', 'SELECT', sql_query, flags=re.IGNORECASE)

    # Ensure FROM is uppercase
    sql_query = re.sub(r'\bfrom\b', 'FROM', sql_query, flags=re.IGNORECASE)

    # Ensure WHERE is uppercase
    sql_query = re.sub(r'\bwhere\b', 'WHERE', sql_query, flags=re.IGNORECASE)

    # Ensure GROUP BY is uppercase
    sql_query = re.sub(r'\bgroup by\b', 'GROUP BY', sql_query, flags=re.IGNORECASE)

    # Ensure ORDER BY is uppercase
    sql_query = re.sub(r'\border by\b', 'ORDER BY', sql_query, flags=re.IGNORECASE)

    # Fix table name if not specified (assume 'data')
    if 'FROM' in sql_query and not re.search(r'FROM\s+\w+', sql_query):
        sql_query = re.sub(r'FROM\s+', 'FROM data ', sql_query)

    return sql_query


def _validate_sql_against_schema(sql_query, schema_info):
    """
    Basic validation of SQL query against dataframe schema.

    Args:
        sql_query (str): SQL query to validate
        schema_info (dict): Schema information

    Returns:
        bool: True if query seems valid
    """
    if not sql_query:
        return False

    # Extract column names from SQL
    column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
    sql_columns = set(re.findall(column_pattern, sql_query.upper()))

    # Get available columns (case-insensitive)
    available_columns = {col.lower() for col in schema_info['dtypes'].keys()}

    # Remove SQL keywords and functions
    sql_keywords = {
        'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'AS', 'AND', 'OR',
        'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'JOIN', 'INNER', 'LEFT',
        'RIGHT', 'ON', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'
    }

    sql_columns = sql_columns - sql_keywords

    # Check if all referenced columns exist
    for col in sql_columns:
        if col.lower() not in available_columns:
            logger.warning(f"Column '{col}' not found in schema")
            return False

    return True


def _generate_sql_fallback(natural_query, df):
    """
    Fallback method for SQL generation using simple pattern matching.

    Args:
        natural_query (str): Natural language query
        df (pd.DataFrame): Dataframe for context

    Returns:
        str: Generated SQL query or None
    """
    query_lower = natural_query.lower()
    columns = df.columns.tolist()

    # Simple pattern-based SQL generation
    if 'count' in query_lower and 'group by' in query_lower:
        # Count with grouping
        group_cols = _extract_columns_from_query(natural_query, columns)
        if group_cols:
            group_col = group_cols[0]
            return f"SELECT {group_col}, COUNT(*) as count FROM data GROUP BY {group_col}"

    elif 'sum' in query_lower or 'total' in query_lower:
        # Sum aggregation
        numeric_cols = [col for col in columns if df[col].dtype in ['int64', 'float64']]
        if numeric_cols:
            sum_col = numeric_cols[0]
            group_cols = _extract_columns_from_query(natural_query, columns)
            if group_cols:
                group_col = group_cols[0]
                return f"SELECT {group_col}, SUM({sum_col}) as total FROM data GROUP BY {group_col}"
            else:
                return f"SELECT SUM({sum_col}) as total FROM data"

    elif 'average' in query_lower or 'avg' in query_lower:
        # Average aggregation
        numeric_cols = [col for col in columns if df[col].dtype in ['int64', 'float64']]
        if numeric_cols:
            avg_col = numeric_cols[0]
            group_cols = _extract_columns_from_query(natural_query, columns)
            if group_cols:
                group_col = group_cols[0]
                return f"SELECT {group_col}, AVG({avg_col}) as average FROM data GROUP BY {group_col}"
            else:
                return f"SELECT AVG({avg_col}) as average FROM data"

    elif 'top' in query_lower or 'highest' in query_lower:
        # Top values
        limit = 10
        order_col = _extract_columns_from_query(natural_query, columns)
        if order_col:
            order_col = order_col[0]
            if df[order_col].dtype in ['int64', 'float64']:
                return f"SELECT * FROM data ORDER BY {order_col} DESC LIMIT {limit}"

    # Default: simple SELECT all
    return "SELECT * FROM data LIMIT 100"


def _extract_columns_from_query(query, available_columns):
    """
    Extract column names mentioned in a natural language query.

    Args:
        query (str): Natural language query
        available_columns (list): Available column names

    Returns:
        list: Extracted column names
    """
    query_words = set(query.lower().split())
    found_columns = []

    for col in available_columns:
        col_lower = col.lower()
        # Check if column name appears in query (as whole word or substring)
        if col_lower in query_words or any(word in col_lower for word in query_words if len(word) > 2):
            found_columns.append(col)

    return found_columns
