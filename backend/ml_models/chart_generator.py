import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
import logging
from .files_processor import process_uploaded_file
from .style_grid import ColorTheme
from .model import generate_chart_configuration

logger = logging.getLogger(__name__)


def generate_chart(chart_type, data, columns=None, theme=None, **kwargs):
    """
    Generate a Plotly chart based on type and data.

    Args:
        chart_type (str): Type of chart to generate
        data (pd.DataFrame or list): Data for the chart
        columns (list): Column names for the chart
        theme (dict): Theme configuration
        **kwargs: Additional chart parameters

    Returns:
        dict: Chart configuration with Plotly data
    """
    try:
        # Apply default theme if none provided
        if theme is None:
            theme = {'colors': {'chart': '#1f77b4', 'text': '#333333', 'background': '#ffffff'}}

        # Convert data to DataFrame if it's a list
        if isinstance(data, list):
            if not data:
                logger.warning("Empty data list provided to generate_chart")
                return None
            df = pd.DataFrame(data)
        else:
            df = data
            
        # Validate that we have a valid DataFrame
        if df is None or df.empty:
            logger.warning("Empty or None DataFrame provided to generate_chart")
            return None

        # Use AI to determine the best chart for the data and context
        intelligent_chart = _generate_intelligent_chart(df, chart_type, theme, **kwargs)
        if intelligent_chart:
            return intelligent_chart

        # Generate chart based on type
        if chart_type == 'bar':
            return _create_bar_chart(df, columns, theme, **kwargs)
        elif chart_type == 'line':
            return _create_line_chart(df, columns, theme, **kwargs)
        elif chart_type == 'scatter':
            return _create_scatter_chart(df, columns, theme, **kwargs)
        elif chart_type == 'pie':
            return _create_pie_chart(df, columns, theme, **kwargs)
        elif chart_type == 'histogram':
            return _create_histogram(df, columns, theme, **kwargs)
        elif chart_type == 'box':
            return _create_box_plot(df, columns, theme, **kwargs)
        elif chart_type == 'heatmap':
            return _create_heatmap(df, columns, theme, **kwargs)
        elif chart_type == 'area':
            return _create_area_chart(df, columns, theme, **kwargs)
        elif chart_type == 'treemap':
            return _create_treemap(df, columns, theme, **kwargs)
        elif chart_type == 'funnel':
            return _create_funnel_chart(df, columns, theme, **kwargs)
        else:
            logger.warning(f"Unknown chart type: {chart_type}")
            return _create_default_chart(df, theme)

    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return None


def _generate_intelligent_chart(df, chart_type, theme, **kwargs):
    """
    Generate an intelligent chart using AI model based on data characteristics.

    Args:
        df (pd.DataFrame): Input dataframe
        chart_type (str): Type of chart to generate
        theme (dict): Theme configuration
        **kwargs: Additional chart parameters

    Returns:
        dict: Chart configuration or None if creation fails
    """
    try:
        # Prepare data description for AI
        data_description = f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns"
        columns_info = {col: str(df[col].dtype) for col in df.columns}
        query_context = kwargs.get('query_context', 'Analyze this data and create meaningful visualizations')

        # Generate chart configuration using AI
        chart_config = generate_chart_configuration(data_description, chart_type, columns_info, query_context)
        
        if chart_config and 'data' in chart_config and 'layout' in chart_config:
            # Apply theme colors to the AI-generated chart
            colors = theme.get('colors', {})
            chart_color = colors.get('chart', '#1f77b4')
            text_color = colors.get('text', '#333333')
            background_color = colors.get('background', '#ffffff')

            # Update layout with theme colors
            chart_config['layout'].update({
                'plot_bgcolor': background_color,
                'paper_bgcolor': background_color,
                'font': {'color': text_color}
            })

            # Ensure we have valid data in the chart
            if not chart_config.get('data'):
                logger.warning("AI-generated chart has no data")
                return None

            # If AI returned nested {'data': [...], 'layout': {...}}, unwrap it
            data_payload = chart_config.get('data')
            layout_payload = chart_config.get('layout', {})
            if isinstance(data_payload, dict) and 'data' in data_payload:
                nested = data_payload
                traces = nested.get('data')
                # Prefer layout from nested if available
                layout_payload = nested.get('layout', layout_payload)
            else:
                # If data_payload is already a list of traces
                traces = data_payload

            # Build normalized chart
            normalized_chart = {
                'type': 'plotly_chart',
                'title': layout_payload.get('title', f'{chart_type.replace("_", " ").title()}'),
                'chart_type': chart_type,
                'data': traces,
                'layout': layout_payload,
                'config': {'responsive': True}
            }

            return normalized_chart

        return None

    except Exception as e:
        logger.error(f"Error generating intelligent chart: {str(e)}", exc_info=True)
        return None


def _create_bar_chart(df, columns, theme, **kwargs):
    """Create bar chart."""
    try:
        colors = theme.get('colors', {})
        chart_color = colors.get('chart', '#1f77b4')
        text_color = colors.get('text', '#333333')
        background_color = colors.get('background', '#ffffff')

        # Validate input DataFrame
        if df is None or df.empty:
            logger.warning("Empty or None DataFrame provided to _create_bar_chart")
            return None

        # Determine columns to use
        if not columns or len(columns) < 2:
            # Auto-select: first categorical, first numeric
            cat_cols = df.select_dtypes(include=['object']).columns
            num_cols = df.select_dtypes(include=[np.number]).columns

            if len(cat_cols) > 0 and len(num_cols) > 0:
                x_col = cat_cols[0]
                y_col = num_cols[0]
            else:
                # Try to convert string columns to numeric if possible
                for col in df.columns:
                    if df[col].dtype == 'object':
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        except:
                            pass
                
                # Try again after conversion
                cat_cols = df.select_dtypes(include=['object']).columns
                num_cols = df.select_dtypes(include=[np.number]).columns
                
                if len(cat_cols) > 0 and len(num_cols) > 0:
                    x_col = cat_cols[0]
                    y_col = num_cols[0]
                else:
                    logger.warning("Insufficient columns for bar chart")
                    return None
        else:
            x_col, y_col = columns[0], columns[1]

        # Validate that columns exist
        if x_col not in df.columns or y_col not in df.columns:
            logger.warning(f"Required columns not found: {x_col}, {y_col}")
            return None

        # Group data if needed
        if df.groupby(x_col).size().count() > 20:
            # Too many categories, aggregate
            chart_data = df.groupby(x_col)[y_col].sum().reset_index().nlargest(10, y_col)
        else:
            chart_data = df.groupby(x_col)[y_col].sum().reset_index()

        # Validate chart data
        if chart_data.empty:
            logger.warning("No data after grouping for bar chart")
            return None

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=chart_data[x_col],
            y=chart_data[y_col],
            marker_color=chart_color,
            name=f'{y_col} by {x_col}'
        ))

        fig.update_layout(
            title=f'{y_col.replace("_", " ").title()} by {x_col.replace("_", " ").title()}',
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title(),
            template='plotly_white',
            plot_bgcolor=background_color,
            paper_bgcolor=background_color,
            font=dict(color=text_color),
            showlegend=False
        )

        chart_json = json.loads(fig.to_json())
        
        # Validate that we have data
        if not chart_json or 'data' not in chart_json or not chart_json['data']:
            logger.warning("Generated chart has no data")
            return None

        return {
            'data': chart_json,
            'layout': fig.to_dict()['layout'],
            'config': {'responsive': True}
        }

    except Exception as e:
        logger.error(f"Error creating bar chart: {str(e)}")
        return None


def _create_line_chart(df, columns, theme, **kwargs):
    """Create line chart."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine columns to use
    if not columns or len(columns) < 2:
        # Auto-select: first datetime, first numeric
        date_cols = df.select_dtypes(include=['datetime64']).columns
        num_cols = df.select_dtypes(include=[np.number]).columns

        if len(date_cols) > 0 and len(num_cols) > 0:
            x_col = date_cols[0]
            y_col = num_cols[0]
        else:
            return None
    else:
        x_col, y_col = columns[0], columns[1]

    # Group by date if needed
    if df[x_col].dtype == 'datetime64[ns]':
        line_data = df.groupby(df[x_col].dt.to_period('M'))[y_col].sum().reset_index()
        line_data[x_col] = line_data[x_col].astype(str)
    else:
        line_data = df.groupby(x_col)[y_col].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=line_data[x_col],
        y=line_data[y_col],
        mode='lines+markers',
        line=dict(color=chart_color, width=2),
        marker=dict(color=chart_color, size=6),
        name=f'{y_col} over {x_col}'
    ))

    fig.update_layout(
        title=f'{y_col.replace("_", " ").title()} Trend',
        xaxis_title=x_col.replace('_", " "').title(),
        yaxis_title=y_col.replace('_", " "').title(),
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=False
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_scatter_chart(df, columns, theme, **kwargs):
    """Create scatter plot."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine columns to use
    if not columns or len(columns) < 2:
        # Auto-select: first two numeric columns
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) >= 2:
            x_col, y_col = num_cols[0], num_cols[1]
        else:
            return None
    else:
        x_col, y_col = columns[0], columns[1]

    # Sample data if too large
    plot_df = df.sample(min(1000, len(df)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df[x_col],
        y=plot_df[y_col],
        mode='markers',
        marker=dict(
            color=chart_color,
            size=8,
            opacity=0.6,
            showscale=False
        ),
        name=f'{x_col} vs {y_col}'
    ))

    fig.update_layout(
        title=f'{x_col.replace("_", " ").title()} vs {y_col.replace("_", " ").title()}',
        xaxis_title=x_col.replace('_", " "').title(),
        yaxis_title=y_col.replace('_", " "').title(),
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=False
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_pie_chart(df, columns, theme, **kwargs):
    """Create pie chart."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine columns to use
    if not columns or len(columns) < 2:
        # Auto-select: first categorical, first numeric
        cat_cols = df.select_dtypes(include=['object']).columns
        num_cols = df.select_dtypes(include=[np.number]).columns

        if len(cat_cols) > 0 and len(num_cols) > 0:
            label_col = cat_cols[0]
            value_col = num_cols[0]
        else:
            return None
    else:
        label_col, value_col = columns[0], columns[1]

    # Group data and limit to top categories
    pie_data = df.groupby(label_col)[value_col].sum().reset_index()
    if len(pie_data) > 8:
        pie_data = pie_data.nlargest(8, value_col)

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=pie_data[label_col],
        values=pie_data[value_col],
        marker_colors=px.colors.qualitative.Set3[:len(pie_data)],
        name=f'{value_col} by {label_col}'
    ))

    fig.update_layout(
        title=f'{value_col.replace("_", " ").title()} Distribution',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=True
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_histogram(df, columns, theme, **kwargs):
    """Create histogram."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine column to use
    if not columns or len(columns) < 1:
        # Auto-select: first numeric column
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) > 0:
            col = num_cols[0]
        else:
            return None
    else:
        col = columns[0]

    # Drop NaN values
    data = df[col].dropna()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=data,
        marker_color=chart_color,
        opacity=0.7,
        name=col
    ))

    fig.update_layout(
        title=f'Distribution of {col.replace("_", " ").title()}',
        xaxis_title=col.replace('_", " "').title(),
        yaxis_title='Frequency',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=False
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_box_plot(df, columns, theme, **kwargs):
    """Create box plot."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine columns to use
    if not columns or len(columns) < 2:
        # Auto-select: first categorical, first numeric
        cat_cols = df.select_dtypes(include=['object']).columns
        num_cols = df.select_dtypes(include=[np.number]).columns

        if len(cat_cols) > 0 and len(num_cols) > 0:
            x_col = cat_cols[0]
            y_col = num_cols[0]
        else:
            return None
    else:
        x_col, y_col = columns[0], columns[1]

    fig = go.Figure()
    fig.add_trace(go.Box(
        x=df[x_col],
        y=df[y_col],
        marker_color=chart_color,
        name=f'{y_col} by {x_col}'
    ))

    fig.update_layout(
        title=f'{y_col.replace("_", " ").title()} Distribution by {x_col.replace("_", " ").title()}',
        xaxis_title=x_col.replace('_", " "').title(),
        yaxis_title=y_col.replace('_", " "').title(),
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=False
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_heatmap(df, columns, theme, **kwargs):
    """Create correlation heatmap."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Get numeric columns
    num_cols = df.select_dtypes(include=[np.number]).columns

    if len(num_cols) < 2:
        return None

    # Calculate correlation matrix
    corr_matrix = df[num_cols].corr()

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmin=-1,
        zmax=1,
        text=np.round(corr_matrix.values, 2),
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False,
        name='Correlation Heatmap'
    ))

    fig.update_layout(
        title='Feature Correlation Matrix',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color)
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_area_chart(df, columns, theme, **kwargs):
    """Create area chart."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Similar to line chart but filled
    if not columns or len(columns) < 2:
        # Auto-select: first datetime, first numeric
        date_cols = df.select_dtypes(include=['datetime64']).columns
        num_cols = df.select_dtypes(include=[np.number]).columns

        if len(date_cols) > 0 and len(num_cols) > 0:
            x_col = date_cols[0]
            y_col = num_cols[0]
        else:
            return None
    else:
        x_col, y_col = columns[0], columns[1]

    # Group by date if needed
    if df[x_col].dtype == 'datetime64[ns]':
        area_data = df.groupby(df[x_col].dt.to_period('M'))[y_col].sum().reset_index()
        area_data[x_col] = area_data[x_col].astype(str)
    else:
        area_data = df.groupby(x_col)[y_col].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=area_data[x_col],
        y=area_data[y_col],
        fill='tozeroy',
        mode='lines',
        line=dict(color=chart_color, width=2),
        name=f'{y_col} over {x_col}'
    ))

    fig.update_layout(
        title=f'{y_col.replace("_", " ").title()} Area Chart',
        xaxis_title=x_col.replace('_", " "').title(),
        yaxis_title=y_col.replace('_", " "').title(),
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=False
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_treemap(df, columns, theme, **kwargs):
    """Create treemap chart."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine columns to use
    if not columns or len(columns) < 2:
        # Auto-select: first categorical, first numeric
        cat_cols = df.select_dtypes(include=['object']).columns
        num_cols = df.select_dtypes(include=[np.number]).columns

        if len(cat_cols) > 0 and len(num_cols) > 0:
            path_col = cat_cols[0]
            value_col = num_cols[0]
        else:
            return None
    else:
        path_col, value_col = columns[0], columns[1]

    # Prepare data for treemap
    tree_data = df.groupby(path_col)[value_col].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Treemap(
        labels=tree_data[path_col],
        values=tree_data[value_col],
        marker_colorscale='Blues',
        textinfo="label+value",
        path=[tree_data[path_col]],
        name='Treemap'
    ))

    fig.update_layout(
        title=f'{value_col.replace("_", " ").title()} Treemap',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color)
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_funnel_chart(df, columns, theme, **kwargs):
    """Create funnel chart."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Determine column to use
    if not columns or len(columns) < 1:
        # Auto-select: first categorical column
        cat_cols = df.select_dtypes(include=['object']).columns
        if len(cat_cols) > 0:
            col = cat_cols[0]
        else:
            return None
    else:
        col = columns[0]

    # Create funnel data (stages with decreasing values)
    funnel_data = df[col].value_counts().reset_index()
    funnel_data.columns = [col, 'count']
    funnel_data = funnel_data.sort_values('count', ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Funnel(
        y=funnel_data[col],
        x=funnel_data['count'],
        marker={"color": chart_color},
        name='Funnel Chart'
    ))

    fig.update_layout(
        title=f'{col.replace("_", " ").title()} Funnel',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        showlegend=False
    )

    return {
        'data': json.loads(fig.to_json()),
        'layout': fig.to_dict()['layout'],
        'config': {'responsive': True}
    }


def _create_default_chart(df, theme):
    """Create a default chart when type is unknown."""
    # Create a simple bar chart as fallback
    return _create_bar_chart(df, None, theme)


def get_chart_types():
    """Get available chart types."""
    return [
        {'type': 'bar', 'name': 'Bar Chart', 'description': 'Compare values across categories'},
        {'type': 'line', 'name': 'Line Chart', 'description': 'Show trends over time'},
        {'type': 'scatter', 'name': 'Scatter Plot', 'description': 'Show relationship between variables'},
        {'type': 'pie', 'name': 'Pie Chart', 'description': 'Show parts of a whole'},
        {'type': 'histogram', 'name': 'Histogram', 'description': 'Show distribution of values'},
        {'type': 'box', 'name': 'Box Plot', 'description': 'Show statistical distribution'},
        {'type': 'heatmap', 'name': 'Heatmap', 'description': 'Show correlation matrix'},
        {'type': 'area', 'name': 'Area Chart', 'description': 'Show cumulative data'},
        {'type': 'treemap', 'name': 'Treemap', 'description': 'Show hierarchical data'},
        {'type': 'funnel', 'name': 'Funnel Chart', 'description': 'Show conversion stages'}
    ]


def validate_chart_request(chart_type, data, columns=None):
    """
    Validate chart generation request.

    Args:
        chart_type (str): Type of chart requested
        data: Data for the chart
        columns (list): Column specifications

    Returns:
        dict: Validation result
    """
    validation = {
        'valid': True,
        'errors': [],
        'warnings': []
    }

    # Check chart type
    available_types = [chart['type'] for chart in get_chart_types()]
    if chart_type not in available_types:
        validation['errors'].append(f"Invalid chart type: {chart_type}")
        validation['valid'] = False

    # Check data
    if data is None:
        validation['errors'].append("No data provided")
        validation['valid'] = False
    elif isinstance(data, list) and len(data) == 0:
        validation['errors'].append("Empty data provided")
        validation['valid'] = False

    # Check columns
    if columns:
        if isinstance(data, pd.DataFrame):
            available_columns = data.columns.tolist()
            for col in columns:
                if col not in available_columns:
                    validation['errors'].append(f"Column not found: {col}")
                    validation['valid'] = False

    return validation
