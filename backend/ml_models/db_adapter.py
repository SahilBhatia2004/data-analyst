import pandas as pd
import re
import logging
from django.conf import settings
from .files_processor import process_uploaded_file

logger = logging.getLogger(__name__)


def execute_query(sql_query, file_id, user, limit=1000):
    """
    Execute SQL query on dataframe and return results.

    Args:
        sql_query (str): SQL query to execute
        file_id (int): ID of the uploaded file
        user: Django user object
        limit (int): Maximum number of rows to return

    Returns:
        list: Query results as list of dictionaries, or None if error
    """
    try:
        # Get dataframe
        df = process_uploaded_file(file_id, user)

        # Add row index for easier querying
        df = df.reset_index()

        # Execute SQL query using pandasql or similar
        results_df = _execute_sql_pandasql(sql_query, df)

        if results_df is None or results_df.empty:
            return []

        # Convert to list of dictionaries
        results = results_df.head(limit).to_dict('records')

        # Add metadata
        metadata = {
            'total_rows': len(results_df),
            'returned_rows': len(results),
            'columns': results_df.columns.tolist(),
            'dtypes': {col: str(results_df[col].dtype) for col in results_df.columns}
        }

        return results

    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}")
        return None


def _execute_sql_pandasql(sql_query, df):
    """
    Execute SQL query using pandasql-like functionality.

    Args:
        sql_query (str): SQL query to execute
        df (pd.DataFrame): Dataframe to query

    Returns:
        pd.DataFrame: Query results or None if error
    """
    try:
        # For this implementation, we'll use a simple SQL parser
        # In production, you'd use a proper SQL engine like pandasql or duckdb

        # Parse and execute simple SQL queries
        if sql_query.strip().upper().startswith('SELECT'):
            return _execute_select_query(sql_query, df)
        else:
            logger.error(f"Unsupported SQL query type: {sql_query}")
            return None

    except Exception as e:
        logger.error(f"Error in SQL execution: {str(e)}")
        return None


def _execute_select_query(sql_query, df):
    """
    Execute SELECT query on dataframe.

    Args:
        sql_query (str): SELECT SQL query
        df (pd.DataFrame): Dataframe to query

    Returns:
        pd.DataFrame: Query results
    """
    try:
        # Simple SQL parser for basic SELECT queries
        # This is a simplified implementation - in production use a proper SQL engine

        # Parse SELECT clause
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, sql_query, re.IGNORECASE | re.DOTALL)

        if not select_match:
            return df  # Return all if no specific SELECT

        select_clause = select_match.group(1).strip()

        # Handle simple cases
        if select_clause == '*':
            result_df = df
        else:
            # Parse column names
            columns = [col.strip() for col in select_clause.split(',')]
            # Validate columns exist
            available_columns = [col for col in columns if col in df.columns]
            result_df = df[available_columns]

        # Parse WHERE clause
        where_pattern = r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$|;)'
        where_match = re.search(where_pattern, sql_query, re.IGNORECASE | re.DOTALL)

        if where_match:
            where_clause = where_match.group(1).strip()
            result_df = _apply_where_clause(result_df, where_clause)

        # Parse GROUP BY clause
        groupby_pattern = r'GROUP\s+BY\s+(.*?)(?:\s+ORDER\s+BY|\s+LIMIT|$|;)'
        groupby_match = re.search(groupby_pattern, sql_query, re.IGNORECASE | re.DOTALL)

        if groupby_match:
            groupby_clause = groupby_match.group(1).strip()
            result_df = _apply_groupby_clause(result_df, groupby_clause)

        # Parse ORDER BY clause
        orderby_pattern = r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$|;)'
        orderby_match = re.search(orderby_pattern, sql_query, re.IGNORECASE | re.DOTALL)

        if orderby_match:
            orderby_clause = orderby_match.group(1).strip()
            result_df = _apply_orderby_clause(result_df, orderby_clause)

        # Parse LIMIT clause
        limit_pattern = r'LIMIT\s+(\d+)'
        limit_match = re.search(limit_pattern, sql_query, re.IGNORECASE)

        if limit_match:
            limit_value = int(limit_match.group(1))
            result_df = result_df.head(limit_value)

        return result_df

    except Exception as e:
        logger.error(f"Error executing SELECT query: {str(e)}")
        return None


def _apply_where_clause(df, where_clause):
    """
    Apply WHERE clause to dataframe.

    Args:
        df (pd.DataFrame): Input dataframe
        where_clause (str): WHERE clause

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    try:
        # Simple WHERE clause parser - handles basic cases
        # For production, use a proper SQL parser

        # Handle simple equality: column = value
        equality_pattern = r'(\w+)\s*=\s*[\'""]?([^\'"\s]+)[\'"]?'
        matches = re.findall(equality_pattern, where_clause)

        for col, value in matches:
            if col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    try:
                        value = float(value)
                        df = df[df[col] == value]
                    except:
                        pass  # Skip if conversion fails
                else:
                    df = df[df[col] == value]

        # Handle LIKE clauses
        like_pattern = r'(\w+)\s+LIKE\s+[\'""]?([^\'"\s]+)[\'"]?'
        like_matches = re.findall(like_pattern, where_clause, re.IGNORECASE)

        for col, pattern in like_matches:
            if col in df.columns:
                df = df[df[col].astype(str).str.contains(pattern, case=False, na=False)]

        # Handle IN clauses
        in_pattern = r'(\w+)\s+IN\s*\(([^)]+)\)'
        in_matches = re.findall(in_pattern, where_clause, re.IGNORECASE)

        for col, values_str in in_matches:
            if col in df.columns:
                values = [v.strip().strip('\'"') for v in values_str.split(',')]
                df = df[df[col].isin(values)]

        return df

    except Exception as e:
        logger.error(f"Error applying WHERE clause: {str(e)}")
        return df


def _apply_groupby_clause(df, groupby_clause):
    """
    Apply GROUP BY clause to dataframe.

    Args:
        df (pd.DataFrame): Input dataframe
        groupby_clause (str): GROUP BY clause

    Returns:
        pd.DataFrame: Grouped dataframe
    """
    try:
        # Parse GROUP BY columns
        groupby_cols = [col.strip() for col in groupby_clause.split(',')]

        # Validate columns exist
        valid_cols = [col for col in groupby_cols if col in df.columns]

        if valid_cols:
            # Group by and aggregate (simple aggregation)
            # This is a simplified approach - in production, parse aggregation functions
            result_df = df.groupby(valid_cols).size().reset_index(name='count')

            # For more complex aggregations, you'd need to parse the SELECT clause
            # This is a basic implementation

            return result_df

        return df

    except Exception as e:
        logger.error(f"Error applying GROUP BY clause: {str(e)}")
        return df


def _apply_orderby_clause(df, orderby_clause):
    """
    Apply ORDER BY clause to dataframe.

    Args:
        df (pd.DataFrame): Input dataframe
        orderby_clause (str): ORDER BY clause

    Returns:
        pd.DataFrame: Sorted dataframe
    """
    try:
        # Simple ORDER BY parser
        # Handle "column ASC/DESC" patterns
        order_parts = re.split(r'\s*,\s*', orderby_clause.strip())

        sort_columns = []
        ascending = []

        for part in order_parts:
            part = part.strip()
            if part.upper().endswith(' DESC'):
                col = part[:-5].strip()
                sort_columns.append(col)
                ascending.append(False)
            elif part.upper().endswith(' ASC'):
                col = part[:-4].strip()
                sort_columns.append(col)
                ascending.append(True)
            else:
                sort_columns.append(part)
                ascending.append(True)

        # Validate columns exist
        valid_cols = [col for col in sort_columns if col in df.columns]

        if valid_cols:
            df = df.sort_values(by=valid_cols, ascending=ascending[:len(valid_cols)])

        return df

    except Exception as e:
        logger.error(f"Error applying ORDER BY clause: {str(e)}")
        return df


def get_table_schema(file_id, user):
    """
    Get schema information for a file.

    Args:
        file_id (int): ID of the uploaded file
        user: Django user object

    Returns:
        dict: Schema information
    """
    try:
        df = process_uploaded_file(file_id, user)
        return {
            'columns': df.columns.tolist(),
            'dtypes': {col: str(df[col].dtype) for col in df.columns},
            'shape': df.shape,
            'sample_data': df.head(5).to_dict('records')
        }

    except Exception as e:
        logger.error(f"Error getting table schema: {str(e)}")
        return None


def validate_query(sql_query, file_id, user):
    """
    Validate SQL query against dataframe schema.

    Args:
        sql_query (str): SQL query to validate
        file_id (int): ID of the uploaded file
        user: Django user object

    Returns:
        dict: Validation result with errors if any
    """
    try:
        df = process_uploaded_file(file_id, user)

        # Extract column references from SQL
        column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        sql_columns = set(re.findall(column_pattern, sql_query.upper()))

        # Remove SQL keywords
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT',
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'AS', 'AND', 'OR',
            'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'JOIN', 'INNER', 'LEFT',
            'RIGHT', 'ON', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'DATA'  # Table name
        }

        referenced_columns = sql_columns - sql_keywords

        # Check if all referenced columns exist
        missing_columns = []
        for col in referenced_columns:
            if col.lower() not in [c.lower() for c in df.columns]:
                missing_columns.append(col)

        if missing_columns:
            return {
                'valid': False,
                'errors': [f"Column '{col}' not found in data" for col in missing_columns]
            }

        return {'valid': True, 'errors': []}

    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Error validating query: {str(e)}"]
        }
