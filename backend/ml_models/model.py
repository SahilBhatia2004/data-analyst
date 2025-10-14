import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def query_llama(prompt, context=None, max_tokens=1000):
    """
    Query the LLaMA model via Grok Cloud API.

    Args:
        prompt (str): The prompt to send to the model
        context (str, optional): Additional context
        max_tokens (int): Maximum tokens in response

    Returns:
        str: Model response or None if error
    """
    try:
        # Prepare the API request
        api_key = settings.GROK_API_KEY
        api_url = settings.GROK_API_URL
        model = settings.LLAMA_MODEL

        if not api_key:
            logger.error("GROK_API_KEY not configured")
            return "AI service not configured. Please contact administrator."

        logger.info(f"Attempting to connect to AI service at: {api_url}")

        # Construct the full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\n\nQuery: {prompt}"

        # Prepare request payload
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful data analyst assistant. Provide clear, accurate, and insightful responses about data analysis, statistics, and business intelligence."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        # Set headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Making request to {api_url}")

        # Make API request
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30
        )

        logger.info(f"API response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get('choices') and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                logger.info(f"Successfully received AI response: {len(content)} characters")
                return content
            else:
                logger.error(f"Unexpected API response format: {result}")
                return "Received unexpected response format from AI service."
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return f"AI service error (status {response.status_code}). Please try again later."

    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return "AI service request timed out. Please try again."

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to AI service: {str(e)}")
        return "Unable to connect to AI service. Please check your connection and API configuration."

    except Exception as e:
        logger.error(f"Unexpected error querying LLaMA: {str(e)}")
        return "An unexpected error occurred while processing your request."


def generate_sql_from_natural_language(natural_query, schema_info=None):
    """
    Generate SQL query from natural language using LLaMA.

    Args:
        natural_query (str): Natural language query
        schema_info (dict, optional): Database schema information

    Returns:
        str: Generated SQL query or None if error
    """
    try:
        # Create prompt for SQL generation
        schema_context = ""
        if schema_info:
            schema_context = f"""
Available tables and columns:
{schema_info}

"""

        prompt = f"""{schema_context}Convert this natural language query to a valid SQL query:

"{natural_query}"

Requirements:
- Use appropriate table and column names from the schema
- Include proper JOINs if needed
- Add WHERE clauses for filtering
- Use appropriate aggregation functions (COUNT, SUM, AVG, etc.)
- Return only the SQL query, no explanations

SQL Query:"""

        response = query_llama(prompt, max_tokens=500)

        if response:
            # Extract SQL query from response (remove any markdown formatting)
            sql_query = response.strip()
            if sql_query.startswith('```sql'):
                sql_query = sql_query[6:]
            if sql_query.endswith('```'):
                sql_query = sql_query[:-3]

            sql_query = sql_query.strip()

            # Basic validation - check if it looks like SQL
            if sql_query.upper().startswith(('SELECT', 'WITH')):
                return sql_query
            else:
                logger.warning(f"Generated query doesn't look like valid SQL: {sql_query}")
                return None

        return None

    except Exception as e:
        logger.error(f"Error generating SQL from natural language: {str(e)}")
        return None


def suggest_visualizations(data_description, data_columns):
    """
    Suggest appropriate visualizations for the data.

    Args:
        data_description (str): Description of the data
        data_columns (list): List of column names and types

    Returns:
        list: List of suggested visualization types with rationale
    """
    try:
        columns_str = "\n".join([f"- {col['name']} ({col['type']})" for col in data_columns])

        prompt = f"""Based on this data structure:

Columns:
{columns_str}

Data description: {data_description}

Suggest 3-5 most appropriate chart/visualization types for this data. For each suggestion, explain:
1. Chart type
2. Which columns to use
3. Why it's appropriate
4. What insights it would reveal

Format as a numbered list."""

        response = query_llama(prompt, max_tokens=600)

        if response:
            # Parse suggestions from response
            suggestions = []
            lines = response.split('\n')

            for line in lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                    suggestions.append(line.strip())

            return suggestions if suggestions else ["Bar chart", "Line chart", "Scatter plot"]

        return ["Bar chart", "Line chart", "Scatter plot"]

    except Exception as e:
        logger.error(f"Error suggesting visualizations: {str(e)}")
        return ["Bar chart", "Line chart", "Scatter plot"]


def generate_dashboard_narrative(data_summary, insights, visualizations):
    """
    Generate a narrative explanation for a dashboard.

    Args:
        data_summary (str): Summary of the data
        insights (list): List of key insights
        visualizations (list): List of visualization descriptions

    Returns:
        str: Narrative explanation
    """
    try:
        insights_str = "\n".join([f"- {insight}" for insight in insights[:5]])
        viz_str = "\n".join([f"- {viz}" for viz in visualizations[:5]])

        prompt = f"""Create a professional narrative summary for this data dashboard:

Data Summary: {data_summary}

Key Insights:
{insights_str}

Visualizations:
{viz_str}

Write a concise, executive-level summary that explains what this dashboard shows and why it matters. Use business-appropriate language."""

        return query_llama(prompt, max_tokens=400)

    except Exception as e:
        logger.error(f"Error generating dashboard narrative: {str(e)}")
        return "Dashboard provides comprehensive insights into the data with key metrics and trends highlighted."


def generate_chart_configuration(data_description, chart_type, columns_info, query_context):
    """
    Generate chart configuration using AI model based on data characteristics and user query.

    Args:
        data_description (str): Description of the data
        chart_type (str): Type of chart to generate
        columns_info (dict): Information about columns in the dataset
        query_context (str): User's query context

    Returns:
        dict: Chart configuration in Plotly format or None if error
    """
    try:
        columns_str = "\n".join([f"- {name}: {info}" for name, info in columns_info.items()])

        prompt = f"""Based on this data and user request, generate a Plotly chart configuration:

User Query: {query_context}

Data Description: {data_description}

Chart Type Requested: {chart_type}

Available Columns:
{columns_str}

Generate a complete Plotly chart configuration that:
1. Uses appropriate data from the columns
2. Matches the requested chart type
3. Provides meaningful visualization for the user's query
4. Includes proper titles, labels, and styling
5. Returns valid JSON that can be directly used with Plotly

Respond ONLY with valid JSON in this exact format:
{{
    "data": [
        {{
            "type": "chart_type",
            "x": ["x_values"],
            "y": ["y_values"],
            "name": "series_name"
        }}
    ],
    "layout": {{
        "title": "Chart Title",
        "xaxis": {{"title": "X Axis Title"}},
        "yaxis": {{"title": "Y Axis Title"}}
    }}
}}

Make sure the JSON is valid and contains all necessary chart data. Use actual data from the columns provided, not example data."""

        response = query_llama(prompt, max_tokens=1000)

        if response:
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    chart_config = json.loads(json_str)
                    # Validate that we have the required structure
                    if 'data' in chart_config and 'layout' in chart_config:
                        return chart_config
                    else:
                        logger.warning(f"AI response missing required fields: {chart_config}")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing AI-generated chart JSON: {str(e)}")
                    logger.error(f"AI response was: {response}")
                    return None
            else:
                logger.error("No valid JSON found in AI response")
                logger.error(f"AI response was: {response}")
                return None

        return None

    except Exception as e:
        logger.error(f"Error generating chart configuration: {str(e)}")
        return None


def generate_intelligent_dashboard_content(data_description, query_context, insights_summary, columns_info):
    """
    Generate intelligent dashboard content including charts, KPIs, trends, and patterns
    by analyzing the user query and dataset through AI intelligence.

    Args:
        data_description (str): Description of the data
        query_context (str): User's query context
        insights_summary (str): Summary of extracted insights
        columns_info (dict): Information about columns in the dataset

    Returns:
        dict: Intelligent dashboard content including charts, KPIs, trends, and patterns
    """
    try:
        columns_str = "\n".join([f"- {name}: {info}" for name, info in columns_info.items()])

        prompt = f"""As an intelligent data analyst, analyze this dataset and user query to generate comprehensive dashboard content:

User Query: {query_context}

Data Description: {data_description}

Extracted Insights Summary: {insights_summary}

Available Columns:
{columns_str}

Generate intelligent dashboard content that includes:

1. Key Performance Indicators (KPIs) - 5-8 most relevant metrics with business context
2. Important Trends - 3-5 significant patterns in the data with business implications
3. Notable Patterns - 3-5 interesting relationships or distributions with business relevance
4. Critical Insights - 3-5 business-relevant observations with actionable recommendations
5. Anomalies - 2-3 outliers or unusual patterns with potential business impact
6. Chart Recommendations - 4-6 chart types that would best visualize the data with specific column recommendations

For each item, provide specific details based on the actual data characteristics, not generic examples. Focus on actionable insights that would help with decision making.

Respond in this JSON format:
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
    "patterns": [
        {{
            "type": "correlation|distribution|cluster|outlier|seasonal",
            "columns": ["col1", "col2"],
            "description": "Business relevance of this pattern",
            "significance": "High|Medium|Low"
        }}
    ],
    "insights": [
        {{
            "category": "business|technical|statistical",
            "title": "Insight Title",
            "description": "Detailed explanation with business implications and recommendations"
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
    "charts": [
        {{
            "type": "bar|line|scatter|pie|histogram|heatmap",
            "title": "Chart Title",
            "columns": ["x_column", "y_column"],
            "insight": "What this chart reveals for decision making"
        }}
    ]
}}

Make sure all values are based on actual data analysis, not placeholders. Focus on business implications and decision-making value."""

        response = query_llama(prompt, max_tokens=2000)

        if not response:
            logger.error("No response received from AI model")
            return None
            
        # Try to parse the response as JSON first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.info("Initial JSON parse failed, attempting to extract JSON from response")
            
        # If direct parse fails, try to extract JSON from the response
        try:
            # Clean the response by removing markdown code blocks and any surrounding text
            clean_response = response.strip()
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0].strip()
            elif '```' in clean_response:
                clean_response = clean_response.split('```')[1].split('```')[0].strip()
                
            # Try to parse the cleaned response
            return json.loads(clean_response)
            
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Error parsing AI response as JSON: {str(e)}")
            logger.debug(f"Response content: {response}")
            
            # As a last resort, try to find a JSON object in the response
            try:
                import re
                # Look for content between curly braces that might be JSON
                json_match = re.search(r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}', clean_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    return json.loads(json_str)
            except Exception as parse_error:
                logger.error(f"Failed to extract JSON from response: {str(parse_error)}")
                
        logger.error("Could not extract valid JSON from AI response")
        logger.debug(f"AI response was: {response}")
        return None

    except Exception as e:
        logger.error(f"Error generating intelligent dashboard content: {str(e)}")
        return None


def analyze_data_insights(data_description, query_context=None):
    """
    Generate insights and analysis from data description.

    Args:
        data_description (str): Description of the data/results
        query_context (str, optional): Context about the original query

    Returns:
        str: AI-generated insights
    """
    try:
        context = ""
        if query_context:
            context = f"Original query: {query_context}\n\n"

        prompt = f"""{context}Based on the following data analysis results:

{data_description}

Please provide:
1. Key insights and observations with business implications
2. Trends or patterns you notice with actionable context
3. Potential business implications and opportunities
4. Recommendations for further analysis or business actions
5. Any anomalies or outliers that stand out with potential impact

Provide a comprehensive but concise analysis focused on decision-making value:"""

        return query_llama(prompt, max_tokens=1000)

    except Exception as e:
        logger.error(f"Error analyzing data insights: {str(e)}")
        return "Unable to generate insights at this time."
