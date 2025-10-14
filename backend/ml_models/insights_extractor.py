import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging
from .files_processor import process_uploaded_file
from .model import query_llama, analyze_data_insights

logger = logging.getLogger(__name__)


def extract_insights(file_id, query_context, user):
    """
    Extract comprehensive insights from data including KPIs, trends, anomalies, and correlations.

    Args:
        file_id (int): ID of the uploaded file
        query_context (str): Context about the user's query
        user: Django user object

    Returns:
        dict: Comprehensive insights dictionary
    """
    try:
        # Get cleaned dataframe
        df = process_uploaded_file(file_id, user)

        # Create detailed data summary for AI
        data_summary = _create_detailed_data_summary(df)
        
        # Use AI to generate comprehensive insights
        ai_insights = _generate_ai_insights(data_summary, query_context)
        
        if ai_insights:
            # Use AI insights as primary source
            return ai_insights
        else:
            # Fallback to statistical methods
            insights = {
                'kpis': _extract_kpis(df),
                'trends': _extract_trends(df),
                'anomalies': _detect_anomalies(df),
                'correlations': _find_correlations(df),
                'distributions': _analyze_distributions(df),
                'summary': _generate_insights_summary(df, query_context),
                'recommendations': _generate_recommendations(df, query_context)
            }
            return insights

    except Exception as e:
        logger.error(f"Error extracting insights: {str(e)}")
        return {
            'kpis': [],
            'trends': [],
            'anomalies': [],
            'correlations': [],
            'distributions': [],
            'summary': 'Unable to generate insights at this time.',
            'recommendations': []
        }


def _create_detailed_data_summary(df):
    """
    Create a detailed summary of the dataset for AI analysis.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        str: Detailed data summary
    """
    if df.empty:
        return "Empty dataset provided."
    
    summary = f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns.\n"
    
    # Data types
    dtypes_summary = "\nData Types:\n"
    for col in df.columns:
        dtypes_summary += f"- {col}: {df[col].dtype}\n"
    
    summary += dtypes_summary
    
    # Numeric columns summary
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        numeric_summary = "\nNumeric Columns Summary:\n"
        for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
            numeric_summary += f"- {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}\n"
        summary += numeric_summary
    
    # Categorical columns summary
    cat_cols = df.select_dtypes(include=['object']).columns
    if len(cat_cols) > 0:
        cat_summary = "\nCategorical Columns Summary:\n"
        for col in cat_cols[:5]:  # Limit to first 5 categorical columns
            unique_count = df[col].nunique()
            cat_summary += f"- {col}: {unique_count} unique values\n"
        summary += cat_summary
    
    return summary


def _generate_ai_insights(data_summary, query_context):
    """
    Generate comprehensive insights using AI model.

    Args:
        data_summary (str): Detailed summary of the data
        query_context (str): User's query context

    Returns:
        dict: AI-generated insights or None if error
    """
    try:
        prompt = f"""Based on this dataset and user query, generate comprehensive business insights:

Dataset Summary:
{data_summary}

User Query Context:
{query_context}

Please provide insights in this exact JSON format:
{{
    "kpis": [
        {{
            "name": "Metric Name",
            "value": 123.45,
            "formatted_value": "123.45",
            "type": "sum|average|count|percentage|ratio",
            "insight": "Why this metric is important for decision making"
        }}
    ],
    "trends": [
        {{
            "metric": "Column Name",
            "direction": "increasing|decreasing|stable",
            "change_percentage": 15.5,
            "time_period": "description",
            "description": "Business implications of this trend"
        }}
    ],
    "anomalies": [
        {{
            "column": "Column Name",
            "value": 123.45,
            "row_index": 0,
            "type": "outlier|spike|drop",
            "severity": "high|medium|low",
            "description": "Business impact of this anomaly"
        }}
    ],
    "correlations": [
        {{
            "column1": "Column Name 1",
            "column2": "Column Name 2",
            "coefficient": 0.75,
            "strength": "strong|moderate|weak",
            "direction": "positive|negative",
            "description": "Business significance of this correlation"
        }}
    ],
    "patterns": [
        {{
            "type": "seasonal|cyclical|cluster|distribution",
            "columns": ["col1", "col2"],
            "description": "Business relevance of this pattern",
            "significance": "High|Medium|Low"
        }}
    ],
    "summary": "Executive summary of key findings with business implications",
    "recommendations": [
        {{
            "type": "analysis|data_quality|visualization|business",
            "priority": "high|medium|low",
            "title": "Recommendation Title",
            "description": "Actionable business recommendation based on the data"
        }}
    ]
}}

Focus on actionable insights that would help with decision making. Provide specific business context and implications."""

        response = query_llama(prompt, max_tokens=2000)
        
        if response:
            # Try to parse the response as JSON
            import json
            import re
            
            # Clean the response by removing markdown code blocks and any surrounding text
            clean_response = response.strip()
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0].strip()
            elif '```' in clean_response:
                clean_response = clean_response.split('```')[1].split('```')[0].strip()
                
            # Try to parse the cleaned response
            try:
                ai_insights = json.loads(clean_response)
                # Validate that we have the required structure
                required_keys = ['kpis', 'trends', 'anomalies', 'correlations', 'summary', 'recommendations']
                if all(key in ai_insights for key in required_keys):
                    return ai_insights
                else:
                    logger.warning(f"AI response missing required keys: {response}")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing AI-generated insights JSON: {str(e)}")
                logger.error(f"AI response was: {response}")
                return None
            
        return None
    except Exception as e:
        logger.error(f"Error generating AI insights: {str(e)}")
        return None


def _extract_kpis(df):
    """
    Extract key performance indicators from dataframe.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        list: List of KPI dictionaries
    """
    kpis = []

    # Numeric columns for KPIs
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        if df[col].notna().sum() > 0:
            try:
                # Sum KPI
                kpi = {
                    'name': f'Total {col.replace("_", " ").title()}',
                    'value': float(df[col].sum()),
                    'formatted_value': f"{df[col].sum():,.2f}",
                    'type': 'sum'
                }
                kpis.append(kpi)

                # Average KPI
                avg_kpi = {
                    'name': f'Average {col.replace("_", " ").title()}',
                    'value': float(df[col].mean()),
                    'formatted_value': f"{df[col].mean():,.2f}",
                    'type': 'average'
                }
                kpis.append(avg_kpi)

                # Count KPI
                count_kpi = {
                    'name': f'{col.replace("_", " ").title()} Count',
                    'value': int(df[col].count()),
                    'formatted_value': f"{df[col].count():,}",
                    'type': 'count'
                }
                kpis.append(count_kpi)

                # Min/Max KPIs
                if df[col].count() > 0:
                    min_kpi = {
                        'name': f'Min {col.replace("_", " ").title()}',
                        'value': float(df[col].min()),
                        'formatted_value': f"{df[col].min():,.2f}",
                        'type': 'min'
                    }
                    kpis.append(min_kpi)

                    max_kpi = {
                        'name': f'Max {col.replace("_", " ").title()}',
                        'value': float(df[col].max()),
                        'formatted_value': f"{df[col].max():,.2f}",
                        'type': 'max'
                    }
                    kpis.append(max_kpi)
            except Exception as e:
                logger.warning(f"Error calculating KPIs for column {col}: {str(e)}")
                continue

        # Limit to first 3 numeric columns to avoid too many KPIs
        if len(kpis) >= 15:  # 5 KPIs per column * 3 columns = 15
            break

    return kpis


def _extract_trends(df):
    """
    Extract trends from time-series or sequential data.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        list: List of trend dictionaries
    """
    trends = []
    
    if df.empty:
        return trends

    try:
        # Look for datetime columns
        datetime_cols = df.select_dtypes(include=['datetime64']).columns

        if len(datetime_cols) == 0:
            return trends
            
        date_col = datetime_cols[0]
        
        # Ensure the date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Drop rows where date is NaT
        df = df.dropna(subset=[date_col])
        
        if df.empty:
            return trends

        # Look for numeric columns to trend
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return trends

        for num_col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            try:
                # Ensure the numeric column is numeric
                if not pd.api.types.is_numeric_dtype(df[num_col]):
                    df[num_col] = pd.to_numeric(df[num_col], errors='coerce')
                
                # Drop rows where numeric value is NaN
                temp_df = df[[date_col, num_col]].dropna()
                
                if len(temp_df) < 3:  # Need at least 3 data points
                    continue
                    
                # Group by month and calculate trends
                monthly_data = temp_df.groupby(temp_df[date_col].dt.to_period('M'))[num_col].agg(['sum', 'mean', 'count'])

                if len(monthly_data) >= 3:  # Need at least 3 periods for trend
                    # Calculate trend direction
                    first_value = monthly_data['sum'].iloc[0]
                    last_value = monthly_data['sum'].iloc[-1]
                    
                    # Handle division by zero
                    if first_value == 0:
                        change_pct = 0
                        direction = 'stable'
                    else:
                        if last_value > first_value:
                            direction = 'increasing'
                            change_pct = ((last_value - first_value) / abs(first_value)) * 100
                        elif last_value < first_value:
                            direction = 'decreasing'
                            change_pct = ((first_value - last_value) / abs(first_value)) * 100
                        else:
                            direction = 'stable'
                            change_pct = 0
                    
                    # Safely format the metric name
                    try:
                        metric_name = str(num_col).replace('_', ' ').title()
                    except:
                        metric_name = "Metric"

                    trend = {
                        'metric': metric_name,
                        'direction': direction,
                        'change_percentage': round(change_pct, 2),
                        'time_period': f"{len(monthly_data)} months",
                        'description': f"{metric_name} has {direction} by {abs(change_pct):.1f}% over {len(monthly_data)} months"
                    }
                    trends.append(trend)

            except Exception as e:
                logger.warning(f"Error calculating trend for {num_col}: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error in trend analysis: {str(e)}")
        return trends

    return trends


def _detect_anomalies(df):
    """
    Detect anomalies in the data using statistical methods.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        list: List of anomaly dictionaries
    """
    anomalies = []

    # Numeric columns for anomaly detection
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols[:3]:  # Limit to first 3 columns
        try:
            data = df[col].dropna()

            if len(data) > 10:  # Need sufficient data
                # Use IQR method for anomaly detection
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                # Find anomalies
                anomalies_in_col = data[(data < lower_bound) | (data > upper_bound)]

                for idx, value in anomalies_in_col.items():
                    anomaly = {
                        'column': col,
                        'value': float(value),
                        'row_index': int(idx),
                        'type': 'outlier',
                        'severity': 'high' if abs(value - data.mean()) > 2 * data.std() else 'medium',
                        'description': f"Unusual {col.replace('_', ' ')} value: {value:.2f}"
                    }
                    anomalies.append(anomaly)

        except Exception as e:
            logger.warning(f"Error detecting anomalies in {col}: {str(e)}")
            continue

    return anomalies


def _find_correlations(df):
    """
    Find correlations between numeric columns.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        list: List of correlation dictionaries
    """
    correlations = []

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) >= 2:
        try:
            # Calculate correlation matrix
            corr_matrix = df[numeric_cols].corr()

            # Find significant correlations
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols):
                    if i < j:  # Avoid duplicate pairs
                        corr_value = corr_matrix.loc[col1, col2]

                        if abs(corr_value) > 0.3:  # Significant correlation threshold
                            strength = 'strong' if abs(corr_value) > 0.7 else 'moderate'

                            correlation = {
                                'column1': col1.replace('_', ' ').title(),
                                'column2': col2.replace('_', ' ').title(),
                                'coefficient': round(corr_value, 3),
                                'strength': strength,
                                'direction': 'positive' if corr_value > 0 else 'negative',
                                'description': f"{strength.title()} { 'positive' if corr_value > 0 else 'negative'} correlation between {col1.replace('_', ' ')} and {col2.replace('_', ' ')}"
                            }
                            correlations.append(correlation)

        except Exception as e:
            logger.warning(f"Error calculating correlations: {str(e)}")

    return correlations


def _analyze_distributions(df):
    """
    Analyze distributions of numeric columns.

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        list: List of distribution analysis dictionaries
    """
    distributions = []

    # Numeric columns for distribution analysis
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols[:3]:  # Limit to first 3 columns
        try:
            data = df[col].dropna()

            if len(data) > 20:  # Need sufficient data
                # Basic distribution statistics
                skewness = data.skew()
                kurtosis = data.kurtosis()

                # Determine distribution type
                if skewness < -1:
                    dist_type = 'left_skewed'
                elif skewness > 1:
                    dist_type = 'right_skewed'
                else:
                    dist_type = 'normal'

                distribution = {
                    'column': col.replace('_', ' ').title(),
                    'distribution_type': dist_type,
                    'skewness': round(skewness, 3),
                    'kurtosis': round(kurtosis, 3),
                    'description': f"{col.replace('_', ' ')} follows a {dist_type.replace('_', ' ')} distribution"
                }
                distributions.append(distribution)

        except Exception as e:
            logger.warning(f"Error analyzing distribution for {col}: {str(e)}")
            continue

    return distributions


def _generate_insights_summary(df, query_context):
    """
    Generate a summary of insights using AI model.

    Args:
        df (pd.DataFrame): Input dataframe
        query_context (str): Context about the user's query

    Returns:
        str: AI-generated insights summary
    """
    try:
        # Create data summary for AI model
        summary_stats = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': {col: str(df[col].dtype) for col in df.columns},
            'missing_data': df.isnull().sum().to_dict(),
            'numeric_summary': {}
        }

        # Add numeric column summaries
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            summary_stats['numeric_summary'][col] = {
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max())
            }

        data_summary = f"Dataset with {summary_stats['shape'][0]} rows and {summary_stats['shape'][1]} columns. " \
                      f"Query context: {query_context}"

        return analyze_data_insights(data_summary, query_context)

    except Exception as e:
        logger.error(f"Error generating insights summary: {str(e)}")
        return "Unable to generate comprehensive insights summary."


def _generate_recommendations(df, query_context):
    """
    Generate data-driven recommendations.

    Args:
        df (pd.DataFrame): Input dataframe
        query_context (str): Context about the user's query

    Returns:
        list: List of recommendation dictionaries
    """
    recommendations = []

    try:
        # Basic recommendations based on data characteristics
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) > 0:
            recommendations.append({
                'type': 'analysis',
                'priority': 'high',
                'title': 'Statistical Analysis',
                'description': f'Consider performing correlation analysis between {", ".join(numeric_cols[:3])}'
            })

        # Check for missing data
        missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
        if missing_pct > 10:
            recommendations.append({
                'type': 'data_quality',
                'priority': 'medium',
                'title': 'Handle Missing Data',
                'description': f'Dataset has {missing_pct:.1f}% missing values. Consider imputation strategies.'
            })

        # Check for potential time series
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        if len(datetime_cols) > 0:
            recommendations.append({
                'type': 'visualization',
                'priority': 'high',
                'title': 'Time Series Analysis',
                'description': f'Create time series visualizations using {datetime_cols[0]} as the time axis'
            })

        # AI-generated recommendations
        ai_recommendations = query_llama(
            f"Based on this data analysis context: {query_context}, provide 2-3 specific recommendations for further analysis or action."
        )

        if ai_recommendations:
            # Parse AI recommendations
            rec_lines = ai_recommendations.split('\n')
            for line in rec_lines[:3]:
                if line.strip():
                    recommendations.append({
                        'type': 'ai_suggested',
                        'priority': 'medium',
                        'title': 'AI Recommendation',
                        'description': line.strip()
                    })

    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")

    return recommendations
