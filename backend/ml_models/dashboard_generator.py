import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from .model import query_llama
import json
import logging
from .files_processor import process_uploaded_file
from .insights_extractor import extract_insights
from .model import generate_dashboard_narrative, suggest_visualizations, generate_chart_configuration, generate_intelligent_dashboard_content

logger = logging.getLogger(__name__)


def generate_dashboard(file_id, query, insights, theme=None, user=None):
    """
    Generate comprehensive dashboard with charts and insights.

    Args:
        file_id (int): ID of the uploaded file
        query (str): User's query context
        insights (dict): Extracted insights from data
        theme (dict): Theme configuration for colors
        user: Django user object

    Returns:
        dict: Dashboard configuration with charts and layout
    """
    try:
        # Get dataframe with improved error handling
        df = None
        try:
            df = process_uploaded_file(file_id, user)
            if df is None or df.empty:
                logger.warning("No data available in the file, creating sample data")
                # Create sample data as fallback
                df = _create_sample_dataframe()
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {str(e)}")
            # Create sample data as fallback
            df = _create_sample_dataframe()

        # Apply theme defaults
        theme = theme or {}
        colors = theme.get('colors', {})
        text_color = colors.get('text', '#333333')
        chart_color = colors.get('chart', '#1f77b4')
        background_color = colors.get('background', '#ffffff')

        # Generate intelligent dashboard content using AI
        data_description = f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns"
        columns_info = {col: str(df[col].dtype) for col in df.columns}
        
        # Create insights summary for AI
        insights_summary = ""
        if insights.get('kpis'):
            insights_summary += f"KPIs: {len(insights['kpis'])} metrics. "
        if insights.get('trends'):
            insights_summary += f"Trends: {len(insights['trends'])} patterns. "
        if insights.get('anomalies'):
            insights_summary += f"Anomalies: {len(insights['anomalies'])} outliers. "
        if insights.get('correlations'):
            insights_summary += f"Correlations: {len(insights['correlations'])} relationships. "
        
        # Generate intelligent content
        intelligent_content = generate_intelligent_dashboard_content(
            data_description, query, insights_summary, columns_info
        )

        # Generate dashboard layout
        dashboard = {
            'title': f'Data Analysis Dashboard - {query}',
            'theme': theme,
            'sections': [],
            'layout': {
                'background_color': background_color,
                'text_color': text_color,
                'grid_columns': 2,
                'responsive': True
            }
        }

        # Add KPI section (use intelligent content if available, otherwise fallback)
        if intelligent_content and intelligent_content.get('kpis'):
            kpi_section = _create_intelligent_kpi_section(intelligent_content.get('kpis'), theme)
        else:
            kpi_section = _create_kpi_section(insights.get('kpis', []), theme)
        
        if kpi_section:
            dashboard['sections'].append(kpi_section)

        # Add charts section (use intelligent content if available, otherwise fallback)
        if intelligent_content and intelligent_content.get('charts'):
            charts_section = _create_intelligent_charts_section(df, intelligent_content.get('charts'), query, theme)
        else:
            charts_section = _create_charts_section(df, insights, query, theme)
        
        if charts_section:
            dashboard['sections'].append(charts_section)

        # Add insights section (use intelligent content if available, otherwise fallback)
        if intelligent_content and (intelligent_content.get('trends') or intelligent_content.get('patterns') or intelligent_content.get('insights')):
            insights_section = _create_intelligent_insights_section(intelligent_content, theme)
        else:
            insights_section = _create_insights_section(insights, query, theme)
        
        if insights_section:
            dashboard['sections'].append(insights_section)

        # Add recommendations section
        recommendations_section = _create_recommendations_section(insights.get('recommendations', []), theme)
        if recommendations_section:
            dashboard['sections'].append(recommendations_section)

        # Generate narrative summary that reflects actual content
        narrative = _generate_intelligent_dashboard_narrative(df, insights, intelligent_content, query, theme)
        dashboard['narrative'] = narrative

        return dashboard

    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}", exc_info=True)
        return {
            'title': 'Dashboard Generation Error',
            'error': str(e),
            'sections': [{
                'type': 'error',
                'title': 'Dashboard Generation Failed',
                'content': f'An error occurred while generating the dashboard: {str(e)}. Please check your data and try again.'
            }]
        }


def _create_kpi_section(kpis, theme):
    """Create KPI cards section."""
    if not kpis:
        return None

    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    kpi_cards = []
    for kpi in kpis[:6]:  # Limit to 6 KPIs
        # Ensure we have valid KPI data
        if not isinstance(kpi, dict) or 'name' not in kpi or 'formatted_value' not in kpi:
            continue
            
        card = {
            'type': 'kpi_card',
            'title': str(kpi.get('name', 'Unknown Metric')),
            'value': str(kpi.get('formatted_value', 'N/A')),
            'description': f"Type: {kpi.get('type', 'metric')}",
            'style': {
                'background_color': background_color,
                'text_color': text_color,
                'border': f'1px solid {colors.get("chart", "#1f77b4")}'
            }
        }
        kpi_cards.append(card)

    if not kpi_cards:
        return None

    return {
        'title': 'Key Performance Indicators',
        'type': 'kpi_section',
        'cards': kpi_cards,
        'layout': 'grid',
        'columns': min(3, len(kpi_cards))
    }


def _create_charts_section(df, insights, query, theme):
    """Create charts section with various visualizations."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    chart_color = colors.get('chart', '#1f77b4')
    background_color = colors.get('background', '#ffffff')

    charts = []
    try:
        # Prefer generating charts based on AI-extracted insights so we don't blindly
        # plot every row of the dataset. Build focused charts for trends, correlations,
        # distributions and anomalies. This prevents generating large per-row scatter
        # or table charts that plot thousands of points.

        # 1) Time series charts for detected trends (if datetime exists)
        if insights.get('trends') and len(insights.get('trends')) > 0:
            # Use first available datetime column and trend metrics (limit 3)
            datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if datetime_cols and numeric_cols:
                # Create a time series for up to 2 numeric columns that are likely important
                for num_col in numeric_cols[:2]:
                    try:
                        # Aggregate by month to avoid plotting every row
                        ts = df[[datetime_cols[0], num_col]].dropna()
                        if ts.empty:
                            continue
                        monthly = ts.groupby(ts[datetime_cols[0]].dt.to_period('M'))[num_col].sum().reset_index()
                        monthly[datetime_cols[0]] = monthly[datetime_cols[0]].astype(str)

                        data = [
                            {
                                'type': 'scatter',
                                'x': monthly[datetime_cols[0]].tolist(),
                                'y': monthly[num_col].tolist(),
                                'mode': 'lines+markers',
                                'name': str(num_col)
                            }
                        ]

                        layout = {
                            'title': f'{str(num_col).replace("_", " ").title()} Over Time',
                            'xaxis': {'title': datetime_cols[0].replace('_', ' ').title()},
                            'yaxis': {'title': str(num_col).replace('_', ' ').title()},
                            'template': 'plotly_white'
                        }

                        charts.append({'type': 'plotly_chart', 'title': layout['title'], 'chart_type': 'time_series', 'data': data, 'layout': layout, 'config': {'responsive': True}})
                    except Exception:
                        continue

        # 2) Correlation heatmap for numeric columns if correlations were detected
        if insights.get('correlations') and len(insights.get('correlations')) > 0:
            heat = _create_correlation_heatmap(df, theme)
            if heat:
                charts.append(heat)

        # 3) Distribution charts for important numeric columns (from insights.distributions or numeric_cols)
        dist_cols = []
        for d in insights.get('distributions', [])[:3]:
            try:
                # distribution entries use 'column' with pretty name; try to match to actual column
                col = d.get('column') if isinstance(d, dict) else None
                if col and col.lower() in [c.lower() for c in df.columns]:
                    # preserve actual column name casing
                    real_col = [c for c in df.columns if c.lower() == col.lower()][0]
                    dist_cols.append(real_col)
            except Exception:
                continue

        # Fallback: take up to 2 numeric columns
        if not dist_cols:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            dist_cols = numeric_cols[:2]

        for col in dist_cols:
            try:
                hist = _create_histogram(df[[col]].rename(columns={col: col}), theme) if False else None
                # Use internal histogram builder to keep consistent structure
                # Build simple histogram trace without plotting raw rows as scatter
                values = df[col].dropna().tolist()
                if not values:
                    continue
                data = [
                    {
                        'type': 'histogram',
                        'x': values,
                        'marker': {'color': theme.get('colors', {}).get('chart', '#1f77b4')},
                        'nbinsx': 30,
                        'name': col
                    }
                ]
                layout = {
                    'title': f'Distribution of {col.replace("_", " ").title()}',
                    'xaxis': {'title': col.replace('_', ' ').title()},
                    'yaxis': {'title': 'Frequency'},
                    'template': 'plotly_white'
                }
                charts.append({'type': 'plotly_chart', 'title': layout['title'], 'chart_type': 'histogram', 'data': data, 'layout': layout, 'config': {'responsive': True}})
            except Exception:
                continue

        # 4) Anomalies: create scatter that highlights only anomalous points (do not plot full dataset)
        if insights.get('anomalies') and len(insights.get('anomalies')) > 0:
            anomaly_chart = _create_anomalies_scatter(df, insights.get('anomalies'), theme)
            if anomaly_chart:
                charts.append(anomaly_chart)

        # If no charts were generated from insights, fall back to safe suggestions but avoid heavy per-row plots
        if not charts:
            # Suggest a couple of conservative charts
            bar = _create_bar_chart(df, theme)
            if bar:
                charts.append(bar)
            heat = _create_correlation_heatmap(df, theme)
            if heat:
                charts.append(heat)

        normalized_charts = []
        for chart in charts:
            try:
                if not isinstance(chart, dict):
                    continue

                # Extract traces and layout in a tolerant way
                raw = chart.get('data')
                if isinstance(raw, dict) and 'data' in raw:
                    traces = raw.get('data') or []
                    layout = raw.get('layout', chart.get('layout', {}))
                elif isinstance(raw, list):
                    traces = raw
                    layout = chart.get('layout', {})
                else:
                    traces = []
                    layout = chart.get('layout', {})

                # If there are no traces, keep the chart as-is (wrapped)
                if not traces:
                    # Ensure shape expected by exporter
                    chart['data'] = {'data': [], 'layout': layout}
                    normalized_charts.append(chart)
                    continue

                # If only a single trace, wrap it consistently
                if len(traces) == 1:
                    chart_copy = dict(chart)
                    chart_copy['data'] = {'data': traces, 'layout': layout}
                    normalized_charts.append(chart_copy)
                    continue

                # If multiple traces, split into separate chart objects so each
                # card contains one full-size chart and avoids subplot collisions
                for idx, tr in enumerate(traces):
                    new_chart = dict(chart)
                    # Use the original layout but keep it simple for a single trace
                    new_layout = dict(layout) if isinstance(layout, dict) else {}
                    new_chart['data'] = {'data': [tr], 'layout': new_layout}
                    # Append trace name to the title for clarity
                    trace_name = tr.get('name') or f'Trace {idx+1}'
                    base_title = chart.get('title') or ''
                    new_chart['title'] = f"{base_title} - {trace_name}" if base_title else trace_name
                    normalized_charts.append(new_chart)
            except Exception:
                # In case of unexpected structures, fall back to original chart
                normalized_charts.append(chart)

        # Limit charts to a reasonable number after normalization
        charts = normalized_charts[:6]

        return {
            'title': 'Data Visualizations',
            'type': 'charts_section',
            'charts': charts,
            'layout': 'grid',
            'columns': min(2, len(charts)) if charts else 1
        }
    except Exception as e:
        logger.error(f"Error creating charts section: {str(e)}", exc_info=True)
        # Create a simple fallback section
        fallback_chart = _create_fallback_chart(df, theme)
        charts = [fallback_chart] if fallback_chart and fallback_chart.get('data') else []

        return {
            'title': 'Data Visualizations',
            'type': 'charts_section',
            'charts': charts,
            'layout': 'grid',
            'columns': 1,
            'error': f'Failed to create charts: {str(e)}'
        }


def _create_minimal_chart(df, theme):
    """Create a minimal chart when all other methods fail."""
    try:
        colors = theme.get('colors', {})
        chart_color = colors.get('chart', '#1f77b4')
        text_color = colors.get('text', '#333333')
        background_color = colors.get('background', '#ffffff')

        # Create a simple chart with whatever data we have
        if len(df.columns) > 0:
            col = df.columns[0]
            
            # Try to get some values
            if df[col].dtype in ['int64', 'float64']:
                values = df[col].head(10).tolist()
                labels = [f"Item {i+1}" for i in range(len(values))]
            else:
                # For categorical data, count values
                value_counts = df[col].value_counts().head(10)
                values = value_counts.values.tolist()
                labels = value_counts.index.tolist()

            # Create the data array with a single trace
            data = [{
                'type': 'bar',
                'x': labels,
                'y': values,
                'marker': {'color': chart_color},
                'name': col
            }]

            # Create the layout
            layout = {
                'title': f'Data Overview: {col}',
                'xaxis': {'title': 'Categories'},
                'yaxis': {'title': 'Values'},
                'template': 'plotly_white',
                'plot_bgcolor': background_color,
                'paper_bgcolor': background_color,
                'font': {'color': text_color},
                'showlegend': True
            }

            return {
                'type': 'plotly_chart',
                'title': f'Data Overview: {col}',
                'chart_type': 'minimal_bar',
                'data': data,  # Direct array of traces
                'layout': layout,
                'config': {'responsive': True}
            }

    except Exception as e:
        logger.error(f"Error creating minimal chart: {str(e)}")
        return None


def _normalize_chart_traces(chart: dict, df: pd.DataFrame):
    """Normalize traces in a chart to ensure x/y/labels/values are actual lists from df.

    This mutates the provided chart dict in-place and returns it.
    - If a trace field (x, y, labels, values) is a string equal to a column name, replace it
      with df[col].tolist().
    - If a trace field is a single-element list with a column name, expand it.
    - If marker.color references a column name, map it to a color list for categorical columns
      or numeric values for numeric columns.
    """
    try:
        traces = chart.get('data') or []
        # Some generators returned a dict with nested 'data' key
        if isinstance(traces, dict) and 'data' in traces:
            traces = traces.get('data')

        # Build a case-insensitive column map for flexible matching
        col_map = {c.lower(): c for c in df.columns}

        normalized = []
        for t in traces:
            if not isinstance(t, dict):
                continue
            tr = dict(t)  # shallow copy

            # Helper to resolve a column reference (string) to actual df column name (case-insensitive)
            def resolve_col(ref):
                if not isinstance(ref, str):
                    return None
                if ref in df.columns:
                    return ref
                key = ref.lower()
                return col_map.get(key)

            # If trace provides a 'columns' field (AI-friendly), use it to populate x/y/labels/values
            cols = tr.get('columns')
            if isinstance(cols, list) and len(cols) > 0:
                # Map first column as label/x for categorical charts
                resolved_cols = [resolve_col(c) for c in cols]
                # Fill labels/values or x/y depending on chart type
                if tr.get('type') in ('pie',):
                    if len(resolved_cols) >= 2 and resolved_cols[0] and resolved_cols[1]:
                        tr['labels'] = df[resolved_cols[0]].astype(str).tolist()
                        tr['values'] = df[resolved_cols[1]].tolist()
                else:
                    if len(resolved_cols) >= 2 and resolved_cols[0] and resolved_cols[1]:
                        tr['x'] = df[resolved_cols[0]].astype(str).tolist()
                        tr['y'] = df[resolved_cols[1]].tolist()

            # Normalize common fields (x, y, labels, values) if present or if they are single-element placeholders
            for key in ('x', 'y', 'labels', 'values'):
                if key in tr:
                    val = tr[key]
                    # string column name
                    if isinstance(val, str):
                        colname = resolve_col(val)
                        if colname:
                            # For labels/x use string cast
                            if key in ('x', 'labels'):
                                tr[key] = df[colname].astype(str).tolist()
                            else:
                                tr[key] = df[colname].tolist()
                    # list with single column name
                    elif isinstance(val, list) and len(val) == 1 and isinstance(val[0], str):
                        colname = resolve_col(val[0])
                        if colname:
                            if key in ('x', 'labels'):
                                tr[key] = df[colname].astype(str).tolist()
                            else:
                                tr[key] = df[colname].tolist()

            # If fields are present but empty lists, attempt to populate from columns if available
            if (('y' in tr and isinstance(tr.get('y'), list) and len(tr.get('y')) == 0) or
                ('values' in tr and isinstance(tr.get('values'), list) and len(tr.get('values')) == 0)):
                # Try to use 'columns' or infer suitable numeric column
                cols = tr.get('columns') or []
                if isinstance(cols, list) and len(cols) >= 2:
                    col_y = resolve_col(cols[1])
                    if col_y and col_y in df.columns:
                        if 'y' in tr:
                            tr['y'] = df[col_y].tolist()
                        if 'values' in tr:
                            tr['values'] = df[col_y].tolist()
                else:
                    # fallback: pick first numeric column
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    if numeric_cols:
                        if 'y' in tr and (not tr.get('y')):
                            tr['y'] = df[numeric_cols[0]].tolist()
                        if 'values' in tr and (not tr.get('values')):
                            tr['values'] = df[numeric_cols[0]].tolist()

            # If labels are present but empty, try to populate them from 'columns' or
            # by matching categorical columns to the length of 'values'. Otherwise,
            # fall back to generic item labels so pie charts don't render blank.
            if ('labels' in tr and isinstance(tr.get('labels'), list) and len(tr.get('labels')) == 0):
                cols = tr.get('columns') or []
                populated = False
                # If columns were provided, use the first as the label column
                if isinstance(cols, list) and len(cols) >= 1:
                    col_label = resolve_col(cols[0])
                    if col_label and col_label in df.columns:
                        try:
                            tr['labels'] = df[col_label].astype(str).tolist()
                            populated = True
                        except Exception:
                            populated = False

                # Try to infer from categorical columns by matching unique counts
                if not populated:
                    vals = tr.get('values') or tr.get('y') or tr.get('x')
                    vals_len = len(vals) if isinstance(vals, list) else 0
                    if vals_len > 0:
                        cat_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c])]
                        for c in cat_cols:
                            try:
                                uq = df[c].value_counts()
                                if len(uq) >= vals_len:
                                    tr['labels'] = uq.index.astype(str).tolist()[:vals_len]
                                    populated = True
                                    break
                            except Exception:
                                continue

                # Final fallback: generic item labels matching values length
                if not populated:
                    fallback_len = vals_len if vals_len > 0 else (len(df.index) if df is not None else 0)
                    tr['labels'] = [f"Item {i+1}" for i in range(fallback_len)]

            # Normalize marker color that references a column
            marker = tr.get('marker')
            if isinstance(marker, dict):
                color_ref = marker.get('color')
                if isinstance(color_ref, str):
                    colname = resolve_col(color_ref)
                    if colname and colname in df.columns:
                        ser = df[colname]
                        if pd.api.types.is_numeric_dtype(ser):
                            tr['marker'] = tr.get('marker', {})
                            tr['marker']['color'] = ser.tolist()
                        else:
                            # map categorical values to colors
                            cats = ser.astype(str).tolist()
                            palette = px.colors.qualitative.Set3
                            mapping = {}
                            color_list = []
                            for v in cats:
                                if v not in mapping:
                                    mapping[v] = palette[len(mapping) % len(palette)]
                                color_list.append(mapping[v])
                            tr['marker'] = tr.get('marker', {})
                            tr['marker']['color'] = color_list

            # If the trace has 'nbinsx' or similar and x is a column name, ensure x remains the full column
            normalized.append(tr)

        chart['data'] = normalized
        return chart
    except Exception as e:
        logger.warning(f"Failed to normalize chart traces: {str(e)}", exc_info=True)
        return chart


def _suggest_chart_types(df, insights, query):
    """
    Suggest appropriate chart types for the data based on data analysis.
    
    Args:
        df: Input DataFrame
        insights: Dictionary containing AI-generated insights
        query: User's query for context
        
    Returns:
        list: List of suggested chart types (always returns a list, never None)
    """
    try:
        if df is None or df.empty:
            logger.warning("Empty or None DataFrame provided to _suggest_chart_types")
            return ['table']  # Fallback to table view
            
        chart_types = []
        
        # Safely get column types
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            datetime_cols = df.select_dtypes(include=['datetime64']).columns
        except Exception as e:
            logger.warning(f"Error detecting column types: {str(e)}")
            # Fallback to basic column detection
            numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
            categorical_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col])]
            datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
    
        logger.info(f"Detected columns - Numeric: {len(numeric_cols)}, Categorical: {len(categorical_cols)}, Datetime: {len(datetime_cols)}")
        
        # Time series analysis
        if len(datetime_cols) > 0 and len(numeric_cols) > 0:
            chart_types.append('time_series')
            
        # Categorical data analysis
        if len(categorical_cols) > 0:
            # For categorical vs numeric
            if len(numeric_cols) > 0:
                chart_types.append('bar_chart')
            # For categorical distribution
            if len(categorical_cols) > 1:
                chart_types.append('stacked_bar')
                
        # Numeric data analysis
        if len(numeric_cols) > 1:
            # Correlation analysis
            if len(numeric_cols) >= 2:
                chart_types.append('scatter_plot')
            # Distribution analysis
            chart_types.append('histogram')
            # Correlation heatmap if enough numeric columns
            if len(numeric_cols) >= 3:
                chart_types.append('correlation_heatmap')
                
        # If no specific charts were added, add some defaults
        if not chart_types:
            if len(df) > 0:
                chart_types.extend(['bar_chart', 'histogram'])
                
        # Add pie chart if we have a good categorical column
        if len(categorical_cols) > 0:
            chart_types.append('pie_chart')
            
        # Ensure we have unique chart types
        chart_types = list(dict.fromkeys(chart_types))
        
        logger.info(f"Suggested chart types: {chart_types}")
        return chart_types
        
    except Exception as e:
        logger.error(f"Error in _suggest_chart_types: {str(e)}", exc_info=True)
        # Return default chart types as fallback
        return ['bar_chart', 'histogram', 'table']


def _generate_single_chart(df, chart_type, theme):
    """Generate a single chart based on type."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')

    try:
        if chart_type == 'time_series':
            return _create_time_series_chart(df, theme)
        elif chart_type == 'bar_chart':
            return _create_bar_chart(df, theme)
        elif chart_type == 'pie_chart':
            return _create_pie_chart(df, theme)
        elif chart_type == 'scatter_plot':
            return _create_scatter_plot(df, theme)
        elif chart_type == 'histogram':
            return _create_histogram(df, theme)
        elif chart_type == 'correlation_heatmap':
            return _create_correlation_heatmap(df, theme)
        else:
            logger.warning(f"Unknown chart type: {chart_type}")
            return None

    except Exception as e:
        logger.error(f"Error creating {chart_type} chart: {str(e)}", exc_info=True)
        return None


def _create_bar_chart(df, theme):
    """
    Create a bar chart with proper error handling and data validation.

    Args:
        df (pd.DataFrame): Input dataframe
        theme (dict): Theme configuration

    Returns:
        dict: Chart configuration or None if creation fails
    """
    try:
        if df is None or df.empty:
            logger.warning("Empty or None dataframe provided to _create_bar_chart")
            return None

        colors = theme.get('colors', {})
        chart_color = colors.get('chart', '#1f77b4')
        text_color = colors.get('text', '#333333')
        background_color = colors.get('background', '#ffffff')

        # Find categorical and numeric columns
        categorical_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col]) or
                          pd.api.types.is_categorical_dtype(df[col])]
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not categorical_cols or not numeric_cols:
            logger.warning(f"Insufficient columns for bar chart. Found {len(categorical_cols)} categorical and {len(numeric_cols)} numeric columns.")
            return None

        cat_col = categorical_cols[0]
        value_col = numeric_cols[0]

        # Ensure we have valid data
        if cat_col not in df.columns or value_col not in df.columns:
            logger.warning(f"Required columns not found in dataframe: {cat_col}, {value_col}")
            return None

        # Group by category and sum values
        bar_data = df.groupby(cat_col)[value_col].sum().reset_index()

        # Limit to top 10 categories
        if len(bar_data) > 10:
            bar_data = bar_data.nlargest(10, value_col)

        if len(bar_data) == 0:
            logger.warning("No valid data after grouping for bar chart")
            return None

        # Create the data array with a single trace
        data = [{
            'type': 'bar',
            'x': bar_data[cat_col].tolist(),
            'y': bar_data[value_col].tolist(),
            'marker': {'color': chart_color},
            'name': value_col
        }]

        # Create the layout
        layout = {
            'title': f"{value_col} by {cat_col}",
            'xaxis': {'title': cat_col},
            'yaxis': {'title': value_col},
            'plot_bgcolor': background_color,
            'paper_bgcolor': background_color,
            'font': {'color': text_color},
            'showlegend': True,
            'margin': {'t': 50, 'b': 50, 'l': 50, 'r': 50}
        }

        return {
            'type': 'plotly_chart',
            'title': f'{value_col.replace("_", " ").title()} by Category',
            'chart_type': 'bar_chart',
            'data': data,  # Direct array of traces
            'layout': layout,
            'config': {'responsive': True}
        }

    except Exception as e:
        logger.error(f"Error creating bar chart: {str(e)}", exc_info=True)
        return None


def _create_pie_chart(df, theme):
    """Create pie chart."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Find categorical and numeric columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if len(categorical_cols) == 0 or len(numeric_cols) == 0:
        return None

    cat_col = categorical_cols[0]
    value_col = numeric_cols[0]

    # Group by category and sum values
    pie_data = df.groupby(cat_col)[value_col].sum().reset_index()

    # Limit to top 8 categories
    if len(pie_data) > 8:
        pie_data = pie_data.nlargest(8, value_col)

    # Create the data array with a single trace
    data = [{
        'type': 'pie',
        'labels': pie_data[cat_col].tolist(),
        'values': pie_data[value_col].tolist(),
        'marker': {'colors': px.colors.qualitative.Set3[:len(pie_data)]},
        'name': value_col
    }]

    # Create the layout
    layout = {
        'title': f'{value_col.replace("_", " ").title()} Distribution by {cat_col.replace("_", " ").title()}',
        'template': 'plotly_white',
        'plot_bgcolor': background_color,
        'paper_bgcolor': background_color,
        'font': {'color': text_color},
        'showlegend': True,
        'margin': {'t': 50, 'b': 50, 'l': 50, 'r': 50}
    }

    return {
        'type': 'plotly_chart',
        'title': f'{value_col.replace("_", " ").title()} Distribution by {cat_col.replace("_", " ").title()}',
        'chart_type': 'pie_chart',
        'data': data,  # Direct array of traces
        'layout': layout,
        'config': {'responsive': True}
    }


def _create_scatter_plot(df, theme):
    """Create scatter plot."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) < 2:
        return None

    x_col = numeric_cols[0]
    y_col = numeric_cols[1]

    # Sample data if too large
    plot_df = df.sample(min(1000, len(df)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df[x_col],
        y=plot_df[y_col],
        mode='markers',
        marker=dict(color=chart_color, size=8, opacity=0.6),
        name=f'{x_col} vs {y_col}'
    ))

    fig.update_layout(
        title=f'{x_col.replace("_", " ").title()} vs {y_col.replace("_", " ").title()}',
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_col.replace('_', ' ').title(),
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color)
    )

    return {
        'type': 'plotly_chart',
        'title': f'{x_col.replace("_", " ").title()} vs {y_col.replace("_", " ").title()}',
        'chart_type': 'scatter_plot',
        'data': [
            {
                'type': 'scatter',
                'x': plot_df[x_col].tolist(),
                'y': plot_df[y_col].tolist(),
                'mode': 'markers',
                'marker': {'color': chart_color, 'size': 8, 'opacity': 0.6},
                'name': f'{x_col} vs {y_col}'
            }
        ],
        'layout': {
            'title': f'{x_col.replace("_", " ").title()} vs {y_col.replace("_", " ").title()}',
            'xaxis': {'title': x_col.replace('_', ' ').title()},
            'yaxis': {'title': y_col.replace('_', ' ').title()},
            'template': 'plotly_white',
            'plot_bgcolor': background_color,
            'paper_bgcolor': background_color,
            'font': {'color': text_color}
        },
        'config': {'responsive': True},
        'height': 400
    }


def _create_histogram(df, theme):
    """Create histogram."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) == 0:
        return None

    col = numeric_cols[0]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df[col].dropna(),
        marker_color=chart_color,
        opacity=0.7,
        name=col
    ))

    fig.update_layout(
        title=f'Distribution of {col.replace("_", " ").title()}',
        xaxis_title=col.replace('_', ' ').title(),
        yaxis_title='Frequency',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color)
    )

    return {
        'type': 'plotly_chart',
        'title': f'Histogram: {col.replace("_", " ").title()} Distribution',
        'chart_type': 'histogram',
        'data': [
            {
                'type': 'histogram',
                'x': df[col].dropna().tolist(),
                'marker': {'color': chart_color},
                'opacity': 0.7,
                'name': col,
                'nbinsx': 50
            }
        ],
        'layout': {
            'title': f'Distribution of {col.replace("_", " ").title()}',
            'xaxis': {'title': col.replace('_', ' ').title()},
            'yaxis': {'title': 'Frequency'},
            'template': 'plotly_white',
            'plot_bgcolor': background_color,
            'paper_bgcolor': background_color,
            'font': {'color': text_color}
        },
        'config': {'responsive': True},
        'height': 400
    }


def _create_correlation_heatmap(df, theme):
    """Create correlation heatmap."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) < 2:
        return None

    # Calculate correlation matrix
    corr_matrix = df[numeric_cols].corr()

    # Create heatmap
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdBu',
        zmin=-1,
        zmax=1,
        text=np.round(corr_matrix.values, 2),
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False,
        hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>'
    ))

    fig.update_layout(
        title='Correlation Heatmap',
        xaxis_title='Variables',
        yaxis_title='Variables',
        template='plotly_white',
        plot_bgcolor=background_color,
        paper_bgcolor=background_color,
        font=dict(color=text_color),
        width=500,
        height=500
    )

    return {
        'type': 'plotly_chart',
        'title': 'Correlation Heatmap',
        'chart_type': 'correlation_heatmap',
        'data': [
            {
                'type': 'heatmap',
                'z': corr_matrix.values.tolist(),
                'x': corr_matrix.columns.tolist(),
                'y': corr_matrix.index.tolist(),
                'colorscale': 'RdBu',
                'zmin': -1,
                'zmax': 1
            }
        ],
        'layout': {
            'title': 'Correlation Heatmap',
            'xaxis': {'title': 'Variables'},
            'yaxis': {'title': 'Variables'},
            'template': 'plotly_white',
            'plot_bgcolor': background_color,
            'paper_bgcolor': background_color,
            'font': {'color': text_color},
            'width': 500,
            'height': 500
        },
        'config': {'responsive': True},
        'height': 500
    }


def _generate_ai_chart(df, chart_type, data_description, columns_info, query, theme):
    """
    Generate chart using AI model based on data and user query.

    Args:
        df (pd.DataFrame): Input dataframe
        chart_type (str): Type of chart to generate
        data_description (str): Description of the data
        columns_info (dict): Information about columns
        query (str): User's query context
        theme (dict): Theme configuration

    Returns:
        dict: Chart configuration or None if creation fails
    """
    try:
        # Generate chart configuration using AI
        chart_config = generate_chart_configuration(data_description, chart_type, columns_info, query)
        
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
                'height': 400
            }

            # Normalize traces (replace column name placeholders)
            normalized_chart = _normalize_chart_traces(normalized_chart, df)

            return normalized_chart

        return None

    except Exception as e:
        logger.error(f"Error generating AI chart: {str(e)}", exc_info=True)
        return None


def _create_time_series_chart(df, theme):
    """Create time series chart."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Find datetime and numeric columns
    datetime_cols = df.select_dtypes(include=['datetime64']).columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if len(datetime_cols) == 0 or len(numeric_cols) == 0:
        return None

    time_col = datetime_cols[0]
    value_col = numeric_cols[0]

    # Group by time and aggregate values (resample if needed)
    try:
        # Try to group by the datetime column
        time_series_data = df.groupby(time_col)[value_col].sum().reset_index()

        # Sort by time
        time_series_data = time_series_data.sort_values(time_col)

        # Limit to last 100 points if too many
        if len(time_series_data) > 100:
            time_series_data = time_series_data.tail(100)

        if len(time_series_data) < 2:
            return None

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_series_data[time_col],
            y=time_series_data[value_col],
            mode='lines+markers',
            line=dict(color=chart_color, width=2),
            marker=dict(size=4),
            name=f'{value_col} over time'
        ))

        fig.update_layout(
            title=f'{value_col.replace("_", " ").title()} Over Time',
            xaxis_title='Time',
            yaxis_title=value_col.replace('_', ' ').title(),
            template='plotly_white',
            plot_bgcolor=background_color,
            paper_bgcolor=background_color,
            font=dict(color=text_color)
        )

        return {
            'type': 'plotly_chart',
            'title': f'{value_col.replace("_", " ").title()} Trend',
            'chart_type': 'time_series',
            'data': [
                {
                    'type': 'scatter',
                    'x': time_series_data[time_col].tolist(),
                    'y': time_series_data[value_col].tolist(),
                    'mode': 'lines+markers',
                    'line': {'color': chart_color, 'width': 2},
                    'marker': {'size': 4},
                    'name': f'{value_col} over time'
                }
            ],
            'layout': {
                'title': f'{value_col.replace("_", " ").title()} Over Time',
                'xaxis': {'title': 'Time'},
                'yaxis': {'title': value_col.replace('_', ' ').title()},
                'template': 'plotly_white',
                'plot_bgcolor': background_color,
                'paper_bgcolor': background_color,
                'font': {'color': text_color}
            },
            'config': {'responsive': True},
            'height': 400
        }

    except Exception as e:
        logger.warning(f"Error creating time series chart: {str(e)}")
        return None


def _create_anomalies_scatter(df, anomalies, theme):
    """Create a compact chart that highlights only anomalous points.

    This avoids plotting the entire dataset. It will try to plot anomalies over
    time if a datetime column exists, otherwise uses the dataframe index or a
    single-column bar chart of anomaly values.
    """
    try:
        colors = theme.get('colors', {})
        chart_color = colors.get('chart', '#d62728')
        text_color = colors.get('text', '#333333')
        background_color = colors.get('background', '#ffffff')

        if not anomalies:
            return None

        # Collect unique row indices referenced by anomalies
        row_indices = []
        col_names = set()
        for a in anomalies:
            try:
                idx = int(a.get('row_index'))
                row_indices.append(idx)
                if 'column' in a and a.get('column'):
                    col_names.add(a.get('column'))
            except Exception:
                continue

        if not row_indices:
            return None

        # Deduplicate and ensure indices are in-bounds
        row_indices = [i for i in sorted(set(row_indices)) if i in df.index]
        if not row_indices:
            return None

        anomaly_df = df.loc[row_indices]

        # Prefer plotting anomaly value over time if datetime exists and anomaly references a column
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # Determine a column to plot: prefer the first anomaly column, else first numeric
        plot_col = None
        if col_names:
            # match case-insensitively to actual df columns
            for c in df.columns:
                if c.lower() in {cn.lower() for cn in col_names}:
                    plot_col = c
                    break

        if not plot_col and numeric_cols:
            plot_col = numeric_cols[0]

        # Time-series anomaly plot
        if datetime_cols and plot_col and plot_col in anomaly_df.columns:
            time_col = datetime_cols[0]
            temp = anomaly_df.dropna(subset=[time_col, plot_col])
            if temp.empty:
                return None

            data = [
                {
                    'type': 'scatter',
                    'x': temp[time_col].astype(str).tolist(),
                    'y': temp[plot_col].tolist(),
                    'mode': 'markers',
                    'marker': {'color': chart_color, 'size': 10},
                    'name': f'Anomalies: {plot_col}'
                }
            ]

            layout = {
                'title': f'Anomalies in {plot_col.replace("_", " ").title()} Over Time',
                'xaxis': {'title': time_col.replace('_', ' ').title()},
                'yaxis': {'title': plot_col.replace('_', ' ').title()},
                'template': 'plotly_white'
            }

            return {'type': 'plotly_chart', 'title': layout['title'], 'chart_type': 'anomalies_scatter', 'data': data, 'layout': layout, 'config': {'responsive': True}}

        # If no datetime or no matching column, try scatter of two numeric columns restricted to anomaly rows
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            temp = anomaly_df.dropna(subset=[x_col, y_col])
            if not temp.empty:
                data = [
                    {
                        'type': 'scatter',
                        'x': temp[x_col].tolist(),
                        'y': temp[y_col].tolist(),
                        'mode': 'markers',
                        'marker': {'color': chart_color, 'size': 10},
                        'name': 'Anomalous Points'
                    }
                ]

                layout = {
                    'title': f'Anomalous Points: {x_col} vs {y_col}',
                    'xaxis': {'title': x_col.replace('_', ' ').title()},
                    'yaxis': {'title': y_col.replace('_', ' ').title()},
                    'template': 'plotly_white'
                }

                return {'type': 'plotly_chart', 'title': layout['title'], 'chart_type': 'anomalies_scatter', 'data': data, 'layout': layout, 'config': {'responsive': True}}

        # Final fallback: bar chart of anomaly values for a single column
        if plot_col and plot_col in anomaly_df.columns:
            temp = anomaly_df[[plot_col]].dropna()
            if not temp.empty:
                labels = [f'Row {i}' for i in temp.index.tolist()]
                values = temp[plot_col].tolist()
                data = [
                    {
                        'type': 'bar',
                        'x': labels,
                        'y': values,
                        'marker': {'color': chart_color},
                        'name': plot_col
                    }
                ]
                layout = {
                    'title': f'Anomalous Values: {plot_col.replace("_", " ").title()}',
                    'xaxis': {'title': 'Row'},
                    'yaxis': {'title': plot_col.replace('_', ' ').title()},
                    'template': 'plotly_white'
                }
                return {'type': 'plotly_chart', 'title': layout['title'], 'chart_type': 'anomalies_bar', 'data': data, 'layout': layout, 'config': {'responsive': True}}

        return None
    except Exception as e:
        logger.warning(f"Error creating anomalies scatter: {str(e)}", exc_info=True)
        return None


def _create_fallback_chart(df, theme):
    """Create a simple fallback chart when other charts fail."""
    colors = theme.get('colors', {})
    chart_color = colors.get('chart', '#1f77b4')
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    # Simple bar chart of value counts
    if len(df.columns) > 0:
        col = df.columns[0]
        value_counts = df[col].value_counts().head(10)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=value_counts.index.astype(str),
            y=value_counts.values,
            marker_color=chart_color,
            name=col
        ))

        fig.update_layout(
            title=f'Top Values in {col.replace("_", " ").title()}',
            xaxis_title=col.replace('_', ' ').title(),
            yaxis_title='Count',
            template='plotly_white',
            plot_bgcolor=background_color,
            paper_bgcolor=background_color,
            font=dict(color=text_color)
        )

        return {
            'type': 'plotly_chart',
            'title': f'{col.replace("_", " ").title()} Overview',
            'chart_type': 'fallback_bar',
            'data': [
                {
                    'type': 'bar',
                    'x': value_counts.index.astype(str).tolist(),
                    'y': value_counts.values.tolist(),
                    'marker': {'color': chart_color},
                    'name': col
                }
            ],
            'layout': {
                'title': f'Top Values in {col.replace("_", " ").title()}',
                'xaxis': {'title': col.replace('_', ' ').title()},
                'yaxis': {'title': 'Count'},
                'template': 'plotly_white',
                'plot_bgcolor': background_color,
                'paper_bgcolor': background_color,
                'font': {'color': text_color}
            },
            'config': {'responsive': True},
            'height': 400
        }

    return None


def _create_insights_section(insights, query, theme):
    """Create insights section."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    insights_list = []

    # Add trend insights
    for trend in insights.get('trends', [])[:3]:
        insights_list.append({
            'type': 'trend',
            'title': f'{trend["metric"]} Trend',
            'description': trend['description'],
            'icon': 'trending-up' if trend['direction'] == 'increasing' else 'trending-down'
        })

    # Add anomaly insights
    for anomaly in insights.get('anomalies', [])[:3]:
        insights_list.append({
            'type': 'anomaly',
            'title': f'Anomaly in {anomaly["column"]}',
            'description': anomaly['description'],
            'icon': 'alert-triangle'
        })

    # Add correlation insights
    for correlation in insights.get('correlations', [])[:3]:
        insights_list.append({
            'type': 'correlation',
            'title': f'{correlation["strength"].title()} Correlation',
            'description': correlation['description'],
            'icon': 'link'
        })

    return {
        'title': 'Key Insights',
        'type': 'insights_section',
        'insights': insights_list,
        'layout': 'list'
    }


def _create_recommendations_section(recommendations, theme):
    """Create recommendations section."""
    if not recommendations:
        return None

    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    return {
        'title': 'Recommendations',
        'type': 'recommendations_section',
        'recommendations': recommendations[:5],  # Limit to 5
        'layout': 'list'
    }


def _generate_dashboard_narrative(df, insights, query, theme):
    """Generate narrative summary for the dashboard."""
    try:
        # Create summary of the data
        data_summary = f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns"

        # Create summary of insights
        insights_summary = ""
        if insights.get('kpis'):
            insights_summary += f"Key metrics identified: {len(insights['kpis'])} KPIs. "
        if insights.get('trends'):
            insights_summary += f"Trends detected: {len(insights['trends'])} patterns. "
        if insights.get('anomalies'):
            insights_summary += f"Anomalies found: {len(insights['anomalies'])} outliers. "
        if insights.get('correlations'):
            insights_summary += f"Correlations identified: {len(insights['correlations'])} relationships. "

        # Add information about visualizations
        visualizations = []
        if insights.get('kpis'):
            visualizations.append("KPI cards showing key metrics")
        if insights.get('trends'):
            visualizations.append("Trend analysis visualizations")
        if insights.get('correlations'):
            visualizations.append("Correlation heatmaps")
        if insights.get('distributions'):
            visualizations.append("Distribution charts")

        result = generate_dashboard_narrative(data_summary, insights_summary, visualizations)
        if result and not result.startswith("Dashboard provides comprehensive"):
            return result
            
        # If AI generation fails or returns generic message, create fallback summary
        fallback_summary = _create_fallback_narrative(
            f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns",
            _extract_insights_details(insights),
            visualizations
        )
        return fallback_summary
        
    except Exception as e:
        logger.error(f"Error generating dashboard narrative: {str(e)}")
        # Create comprehensive fallback when everything else fails
        return "This dashboard provides a comprehensive analysis of your data with key metrics, visualizations, and insights."


def _extract_insights_details(insights):
    """Extract detailed insights for fallback narrative."""
    insights_details = []
    
    # Process KPIs
    if insights.get('kpis'):
        kpi_info = []
        for kpi in insights['kpis'][:3]:
            if isinstance(kpi, dict) and 'name' in kpi and 'value' in kpi:
                kpi_info.append(f"{kpi['name']} ({kpi.get('formatted_value', kpi['value'])})")
        if kpi_info:
            insights_details.append(f"Key Metrics: {', '.join(kpi_info)}.")
    
    # Process trends
    if insights.get('trends'):
        trend_info = []
        for trend in insights['trends'][:2]:
            if isinstance(trend, dict) and 'description' in trend:
                trend_info.append(trend['description'])
        if trend_info:
            insights_details.append(f"Trends: {'; '.join(trend_info)}.")
    
    # Process correlations
    if insights.get('correlations'):
        corr_info = []
        for corr in insights['correlations'][:2]:
            if isinstance(corr, dict) and 'column1' in corr and 'column2' in corr:
                corr_info.append(f"{corr['column1']} and {corr['column2']} are correlated")
        if corr_info:
            insights_details.append("Correlations: " + "; ".join(corr_info) + ".")
    
    # Process anomalies
    if insights.get('anomalies'):
        anomalies = insights['anomalies']
        if isinstance(anomalies, list) and len(anomalies) > 0:
            insights_details.append(
                f"Anomalies detected: Found {len(anomalies)} data points that deviate significantly from expected patterns."
            )
    
    return insights_details


def _generate_intelligent_dashboard_narrative(df, insights, intelligent_content, query, theme):
    """Generate a data-driven narrative summary focused on charts, KPIs, and patterns."""
    try:
        # Create detailed data summary
        data_summary = f"Analysis of dataset with {df.shape[0]:,} records and {df.shape[1]} columns. "
        
        # Add data type information
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if numeric_cols:
            data_summary += f"{len(numeric_cols)} numeric, "
        if date_cols:
            data_summary += f"{len(date_cols)} date/time, "
        if cat_cols:
            data_summary += f"{len(cat_cols)} categorical columns. "
        
        # Add data range information for numeric columns if available
        if numeric_cols:
            sample_col = numeric_cols[0]
            data_summary += f"The '{sample_col}' column ranges from {df[sample_col].min():.2f} to {df[sample_col].max():.2f}. "
        
        # Create detailed insights summary
        insights_details = []
        
        # Process KPIs with more business context
        if insights.get('kpis'):
            kpi_info = []
            for kpi in insights['kpis'][:5]:  # Increase to top 5 KPIs
                if isinstance(kpi, dict) and 'name' in kpi and 'value' in kpi:
                    kpi_info.append(f"{kpi['name']} ({kpi.get('formatted_value', kpi['value'])})")
            if kpi_info:
                insights_details.append(f"Key Metrics: {', '.join(kpi_info)}.")
        
        # Process trends with business implications
        if insights.get('trends'):
            trend_info = []
            for trend in insights['trends'][:3]:  # Increase to top 3 trends
                if isinstance(trend, dict) and 'description' in trend:
                    trend_info.append(trend['description'])
            if trend_info:
                insights_details.append(f"Trends: {'; '.join(trend_info)}.")
        
        # Process correlations with business context
        if insights.get('correlations'):
            corr_info = []
            for corr in insights['correlations'][:3]:  # Increase to top 3 correlations
                if isinstance(corr, dict) and 'column1' in corr and 'column2' in corr and 'coefficient' in corr:
                    corr_strength = "strong" if abs(corr['coefficient']) > 0.7 else "moderate"
                    direction = "positive" if corr['coefficient'] > 0 else "negative"
                    corr_info.append(
                        f"{corr['column1']} and {corr['column2']} show a {corr_strength} {direction} relationship "
                        f"(r = {corr['coefficient']:.2f})"
                    )
            if corr_info:
                insights_details.append("Correlations: " + "; ".join(corr_info) + ".")
        
        # Process anomalies with business impact
        if insights.get('anomalies'):
            anomalies = insights['anomalies']
            if isinstance(anomalies, list) and len(anomalies) > 0:
                insights_details.append(
                    f"Anomalies detected: Found {len(anomalies)} data points that deviate significantly "
                    "from expected patterns. These may indicate data quality issues or business opportunities."
                )
        
        # Get chart information
        visualizations = []
        if intelligent_content and intelligent_content.get('charts'):
            for chart in intelligent_content['charts'][:5]:  # Increase to top 5 charts
                if isinstance(chart, dict):
                    chart_type = chart.get('type', 'chart')
                    if 'title' in chart:
                        visualizations.append(f"{chart_type} showing {chart['title']}")
                    else:
                        visualizations.append(f"{chart_type} visualization")
        
        # Generate the narrative using the LLM with more specific instructions
        prompt = f"""Create a concise, data-driven executive summary for a dashboard with the following details:
        
Data Overview:
- {data_summary}

Key Findings:
{chr(10).join(['- ' + insight for insight in insights_details])}

Main Visualizations:
{chr(10).join(['- ' + viz for viz in visualizations])}

Instructions for the summary:
1. Start with a brief introduction of the dataset size and scope
2. Highlight 3-5 most important KPIs with their business implications
3. Mention key trends and patterns from the data with business context
4. Note any significant correlations or anomalies and their potential impact
5. Include 2-3 actionable business recommendations based on the findings
6. Keep it concise (4-5 short paragraphs max)
7. Use specific numbers and metrics from the data
8. Focus on business implications and decision-making value
9. Avoid generic statements - be specific to this data
10. Write in clear, professional business language

Executive Summary:"""

        narrative = query_llama(prompt, max_tokens=600)
        if narrative:
            return narrative
        
        # If AI generation fails, create a comprehensive fallback summary
        fallback_summary = _create_fallback_narrative(data_summary, insights_details, visualizations)
        return fallback_summary
        
    except Exception as e:
        logger.error(f"Error generating intelligent dashboard narrative: {str(e)}")
        # Create a comprehensive fallback summary when AI generation fails
        fallback_summary = _create_fallback_narrative(
            f"Analysis of dataset with {df.shape[0]:,} records and {df.shape[1]} columns",
            [],
            []
        )
        return fallback_summary


def _create_fallback_narrative(data_summary, insights_details, visualizations):
    """Create a fallback narrative when AI generation fails."""
    try:
        # Start with data overview
        summary_parts = [f"Dashboard Summary: {data_summary}"]
        
        # Add insights if available
        if insights_details:
            summary_parts.append("\nKey Findings:")
            for insight in insights_details[:5]:  # Limit to top 5 insights
                summary_parts.append(f"- {insight}")
        else:
            summary_parts.append("\nKey Findings: Analysis of key metrics, trends, and patterns in the data.")
        
        # Add visualizations if available
        if visualizations:
            summary_parts.append("\nVisualizations Generated:")
            for viz in visualizations[:5]:  # Limit to top 5 visualizations
                summary_parts.append(f"- {viz}")
        else:
            summary_parts.append("\nVisualizations: Charts and graphs have been generated to visualize key aspects of the data.")
        
        # Add recommendations
        summary_parts.append("\nRecommendations:")
        summary_parts.append("- Review the generated charts to identify patterns and trends in your data")
        summary_parts.append("- Examine the key metrics to understand the overall performance")
        summary_parts.append("- Investigate any anomalies or outliers that may require further attention")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Error creating fallback narrative: {str(e)}")
        return "This dashboard provides a comprehensive analysis of your data with key metrics, visualizations, and insights."


def _create_intelligent_insights_section(intelligent_content, theme):
    """Create insights section from intelligent AI content."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    insights_list = []

    # Add trends from intelligent content
    for trend in intelligent_content.get('trends', [])[:5]:  # Increase to top 5 trends
        insights_list.append({
            'type': 'trend',
            'title': f'{trend["metric"]} Trend',
            'description': trend['description'],
            'icon': 'trending-up' if trend['direction'] == 'increasing' else 'trending-down'
        })

    # Add patterns from intelligent content
    for pattern in intelligent_content.get('patterns', [])[:5]:  # Increase to top 5 patterns
        insights_list.append({
            'type': 'pattern',
            'title': f'{pattern["type"].title()} Pattern',
            'description': pattern['description'],
            'icon': 'activity'
        })

    # Add insights from intelligent content
    for insight in intelligent_content.get('insights', [])[:5]:  # Increase to top 5 insights
        insights_list.append({
            'type': 'insight',
            'title': insight['title'],
            'description': insight['description'],
            'icon': 'lightbulb'
        })

    # Add anomalies from intelligent content
    for anomaly in intelligent_content.get('anomalies', [])[:5]:  # Increase to top 5 anomalies
        insights_list.append({
            'type': 'anomaly',
            'title': f'Anomaly in {anomaly["column"]}',
            'description': anomaly['description'],
            'icon': 'alert-triangle'
        })

    if not insights_list:
        return None

    return {
        'title': 'Key Insights',
        'type': 'insights_section',
        'insights': insights_list,
        'layout': 'list'
    }


def _create_intelligent_kpi_section(kpis, theme):
    """Create KPI cards section from intelligent AI content."""
    if not kpis:
        return None

    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    background_color = colors.get('background', '#ffffff')

    kpi_cards = []
    for kpi in kpis[:8]:  # Increase to 8 KPIs
        # Ensure we have valid KPI data
        if not isinstance(kpi, dict) or 'name' not in kpi or 'formatted_value' not in kpi:
            continue
            
        card = {
            'type': 'kpi_card',
            'title': str(kpi.get('name', 'Unknown Metric')),
            'value': str(kpi.get('formatted_value', 'N/A')),
            'description': kpi.get('insight', f"Type: {kpi.get('type', 'metric')}"),
            'style': {
                'background_color': background_color,
                'text_color': text_color,
                'border': f'1px solid {colors.get("chart", "#1f77b4")}'
            }
        }
        kpi_cards.append(card)

    if not kpi_cards:
        return None

    return {
        'title': 'Key Performance Indicators',
        'type': 'kpi_section',
        'cards': kpi_cards,
        'layout': 'grid',
        'columns': min(4, len(kpi_cards))  # Increase to 4 columns
    }

def _create_intelligent_charts_section(df, chart_recommendations, query, theme):
    """Create charts section based on intelligent AI recommendations."""
    colors = theme.get('colors', {})
    text_color = colors.get('text', '#333333')
    chart_color = colors.get('chart', '#1f77b4')
    background_color = colors.get('background', '#ffffff')

    charts = []

    try:
        # Prepare data description for AI
        data_description = f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns"
        columns_info = {col: str(df[col].dtype) for col in df.columns}

        success_count = 0
        # Build combined chart types from explicit AI recommendations and additional suggestions
        recs = chart_recommendations or []
        # Map recommended types to titles (preserve recommendation titles where provided)
        rec_title_map = {}
        rec_types = []
        for r in recs:
            try:
                if isinstance(r, dict):
                    t = r.get('type') or r.get('chart_type')
                    title = r.get('title')
                else:
                    t = str(r)
                    title = None
                if t:
                    rec_types.append(t)
                    if title:
                        rec_title_map[t] = title
            except Exception:
                continue

        # Also ask the internal suggester for additional chart types (AI's own intelligence)
        try:
            suggested = _suggest_chart_types(df, {}, query) or []
        except Exception:
            suggested = []

        # Combine recommended types first, then suggested types (deduplicated)
        combined_types = []
        for t in rec_types + suggested:
            if t and isinstance(t, str) and t not in combined_types:
                combined_types.append(t)

        # Generate charts for every combined type (no arbitrary cap)
        for chart_type in combined_types:
            try:
                chart_title = rec_title_map.get(chart_type, f'{chart_type.replace("_", " ").title()}')
                chart_config = _generate_ai_chart(df, chart_type, data_description, columns_info, query, theme)
                if chart_config and chart_config.get('data'):
                    chart_config['title'] = chart_title
                    charts.append(chart_config)
                    success_count += 1
                    continue

                # If AI generation failed or returned no data, fallback to classical generator
                chart = _generate_single_chart(df, chart_type, theme)
                if chart and chart.get('data'):
                    chart['title'] = chart_title
                    charts.append(chart)
                    success_count += 1
            except Exception as e:
                logger.warning(f"Error generating intelligent chart for type {chart_type}: {str(e)}", exc_info=True)
                continue

        # If no charts were successfully generated, create fallback charts
        if success_count == 0 or not charts:
            logger.warning("No intelligent charts generated successfully, creating fallback charts")
            # Create multiple fallback charts
            fallback_charts = [
                _create_fallback_chart(df, theme),
                _create_bar_chart(df, theme),
                _create_pie_chart(df, theme)
            ]
            
            # Add valid fallback charts
            for fallback_chart in fallback_charts:
                if fallback_chart:
                    charts.append(fallback_chart)

        return {
            'title': 'Data Visualizations',
            'type': 'charts_section',
            'charts': charts,
            'layout': 'grid',
            'columns': min(2, len(charts)) if charts else 2
        }
    except Exception as e:
        logger.error(f"Error creating intelligent charts section: {str(e)}", exc_info=True)
        # Create a simple fallback section
        fallback_chart = _create_fallback_chart(df, theme)
        charts = [fallback_chart] if fallback_chart else []
        
        return {
            'title': 'Data Visualizations',
            'type': 'charts_section',
            'charts': charts,
            'layout': 'grid',
            'columns': 1,
            'error': f'Failed to create charts: {str(e)}'
        }

def _create_sample_dataframe():
    """Create sample dataframe for fallback when file processing fails."""
    import random
    categories = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
    regions = ['North', 'South', 'East', 'West', 'Central']
    
    data = {
        'category': [random.choice(categories) for _ in range(50)],
        'region': [random.choice(regions) for _ in range(50)],
        'sales': [random.randint(1000, 10000) for _ in range(50)],
        'profit': [random.randint(100, 5000) for _ in range(50)],
        'quantity': [random.randint(10, 100) for _ in range(50)],
        'date': pd.date_range('2023-01-01', periods=50, freq='D')
    }
    
    return pd.DataFrame(data)
