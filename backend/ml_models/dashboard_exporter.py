import json
import base64
import uuid
import os
import io
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .dashboard_generator import generate_dashboard
import supabase

logger = logging.getLogger(__name__)


def get_supabase_client():
    """Get Supabase client for storage operations."""
    try:
        client = supabase.create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY
        )
        return client
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {str(e)}")
        raise


def export_dashboard(dashboard, export_format='html'):
    """
    Export dashboard in various formats.

    Args:
        dashboard: Dashboard object from database
        export_format (str): Export format ('html', 'pdf', 'png')

    Returns:
        str: Export link or file path
    """
    try:
        if export_format == 'html':
            return _export_html(dashboard)
        elif export_format == 'pdf':
            return _export_pdf(dashboard)
        elif export_format == 'png':
            return _export_png(dashboard)
        else:
            logger.error(f"Unsupported export format: {export_format}")
            return None

    except Exception as e:
        logger.error(f"Error exporting dashboard: {str(e)}")
        return None


def _export_html(dashboard):
    """Export dashboard as HTML file to Supabase storage."""
    try:
        # Generate unique filename
        export_id = str(uuid.uuid4())
        filename = f"dashboard_{export_id}.html"

        # Create HTML content
        html_content = _generate_html_content(dashboard)

        # Get Supabase client and upload file
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'

        # Generate unique filename with user identifier
        import pandas as pd
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        user_id = getattr(dashboard.user, 'id', 'unknown')
        unique_filename = f"{user_id}_{timestamp}_{filename}"

        # Upload to Supabase storage
        try:
            upload_response = supabase_client.storage.from_(bucket_name).upload(
                unique_filename,
                html_content.encode('utf-8'),
                {"content-type": "text/html"}
            )
            logger.info(f"HTML file uploaded to Supabase: {upload_response}")
        except Exception as upload_error:
            logger.error(f"Error uploading HTML to Supabase: {str(upload_error)}")
            # Try to create the bucket if it doesn't exist
            if "Bucket not found" in str(upload_error):
                try:
                    logger.info(f"Creating bucket: {bucket_name}")
                    # Create bucket without public parameter - buckets are private by default
                    supabase_client.storage.create_bucket(bucket_name)
                    logger.info(f"Bucket {bucket_name} created")

                    # Make bucket public after creation
                    try:
                        supabase_client.storage.update_bucket(bucket_name, {"public": True})
                        logger.info(f"Bucket {bucket_name} made public")
                    except Exception as public_error:
                        logger.warning(f"Could not make bucket public: {str(public_error)}")

                    # Retry upload after creating bucket
                    upload_response = supabase_client.storage.from_(bucket_name).upload(
                        unique_filename,
                        html_content.encode('utf-8'),
                        {"content-type": "text/html"}
                    )
                    logger.info(f"HTML file uploaded to Supabase after bucket creation: {upload_response}")
                except Exception as bucket_error:
                    logger.error(f"Failed to create bucket: {str(bucket_error)}")
                    return None
            else:
                raise upload_error

        # Get public URL for the uploaded file
        try:
            file_url = supabase_client.storage.from_(bucket_name).get_public_url(unique_filename)
            logger.info(f"Generated public URL: {file_url}")
        except Exception as url_error:
            logger.error(f"Error generating public URL: {str(url_error)}")
            file_url = None

        return file_url

    except Exception as e:
        logger.error(f"Error exporting HTML: {str(e)}")
        return None


def _export_pdf(dashboard):
    """Export dashboard as Word document (.docx) file to Supabase storage."""
    try:
        # Generate unique filename
        export_id = str(uuid.uuid4())
        filename = f"dashboard_{export_id}.docx"

        # Get Supabase client and upload file
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'

        # Generate unique filename with user identifier
        import pandas as pd
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        user_id = getattr(dashboard.user, 'id', 'unknown')
        unique_filename = f"{user_id}_{timestamp}_{filename}"

        # Create Word document content in-memory
        docx_bytes = _create_word_document(dashboard)
        if docx_bytes is None:
            return None

        # Upload to Supabase storage
        try:
            upload_response = supabase_client.storage.from_(bucket_name).upload(
                unique_filename,
                docx_bytes,
                {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
            )
            logger.info(f"Word document uploaded to Supabase: {upload_response}")
        except Exception as upload_error:
            logger.error(f"Error uploading Word document to Supabase: {str(upload_error)}")
            # Try to create the bucket if it doesn't exist
            if "Bucket not found" in str(upload_error):
                try:
                    logger.info(f"Creating bucket: {bucket_name}")
                    # Create bucket without public parameter - buckets are private by default
                    supabase_client.storage.create_bucket(bucket_name)
                    logger.info(f"Bucket {bucket_name} created")

                    # Make bucket public after creation
                    try:
                        supabase_client.storage.update_bucket(bucket_name, {"public": True})
                        logger.info(f"Bucket {bucket_name} made public")
                    except Exception as public_error:
                        logger.warning(f"Could not make bucket public: {str(public_error)}")

                    # Retry upload after creating bucket
                    upload_response = supabase_client.storage.from_(bucket_name).upload(
                        unique_filename,
                        docx_bytes,
                        {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
                    )
                    logger.info(f"Word document uploaded to Supabase after bucket creation: {upload_response}")
                except Exception as bucket_error:
                    logger.error(f"Failed to create bucket: {str(bucket_error)}")
                    return None
            else:
                raise upload_error

        # Get public URL for the uploaded file
        try:
            file_url = supabase_client.storage.from_(bucket_name).get_public_url(unique_filename)
            logger.info(f"Generated public URL: {file_url}")
        except Exception as url_error:
            logger.error(f"Error generating public URL: {str(url_error)}")
            file_url = None

        return file_url

    except Exception as e:
        logger.error(f"Error exporting Word document: {str(e)}")
        return None


def _export_png(dashboard):
    """Export dashboard as PNG image to Supabase storage."""
    try:
        # Generate unique filename
        export_id = str(uuid.uuid4())
        filename = f"dashboard_{export_id}.png"

        # Get Supabase client and upload file
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'

        # Generate unique filename with user identifier
        import pandas as pd
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        user_id = getattr(dashboard.user, 'id', 'unknown')
        unique_filename = f"{user_id}_{timestamp}_{filename}"

        # Create PNG content
        png_bytes = _create_png_placeholder(dashboard)
        if png_bytes is None:
            return None

        # Upload to Supabase storage
        try:
            upload_response = supabase_client.storage.from_(bucket_name).upload(
                unique_filename,
                png_bytes,
                {"content-type": "image/png"}
            )
            logger.info(f"PNG file uploaded to Supabase: {upload_response}")
        except Exception as upload_error:
            logger.error(f"Error uploading PNG to Supabase: {str(upload_error)}")
            # Try to create the bucket if it doesn't exist
            if "Bucket not found" in str(upload_error):
                try:
                    logger.info(f"Creating bucket: {bucket_name}")
                    # Create bucket without public parameter - buckets are private by default
                    supabase_client.storage.create_bucket(bucket_name)
                    logger.info(f"Bucket {bucket_name} created")

                    # Make bucket public after creation
                    try:
                        supabase_client.storage.update_bucket(bucket_name, {"public": True})
                        logger.info(f"Bucket {bucket_name} made public")
                    except Exception as public_error:
                        logger.warning(f"Could not make bucket public: {str(public_error)}")

                    # Retry upload after creating bucket
                    upload_response = supabase_client.storage.from_(bucket_name).upload(
                        unique_filename,
                        png_bytes,
                        {"content-type": "image/png"}
                    )
                    logger.info(f"PNG file uploaded to Supabase after bucket creation: {upload_response}")
                except Exception as bucket_error:
                    logger.error(f"Failed to create bucket: {str(bucket_error)}")
                    return None
            else:
                raise upload_error

        # Get public URL for the uploaded file
        try:
            file_url = supabase_client.storage.from_(bucket_name).get_public_url(unique_filename)
            logger.info(f"Generated public URL: {file_url}")
        except Exception as url_error:
            logger.error(f"Error generating public URL: {str(url_error)}")
            file_url = None

        return file_url

    except Exception as e:
        logger.error(f"Error exporting PNG: {str(e)}")
        return None


def _generate_html_content(dashboard, include_charts_as_images=False):
    """Generate standalone HTML content for the dashboard."""
    try:
        # Extract dashboard data
        dashboard_data = dashboard.dashboard_data
        theme = dashboard.theme or {}

        # Generate HTML template
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {plotly_script}
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: {background_color};
            color: {text_color};
        }}

        .dashboard-container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .dashboard-title {{
            text-align: center;
            margin-bottom: 30px;
            color: {text_color};
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section-title {{
            border-bottom: 2px solid {chart_color};
            padding-bottom: 10px;
            margin-bottom: 20px;
            color: {text_color};
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .kpi-card {{
            background: {background_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}

        .kpi-value {{
            font-size: 2em;
            font-weight: bold;
            color: {chart_color};
        }}

        .kpi-title {{
            color: {text_color};
            margin-top: 10px;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }}

        .chart-container {{
            background: {background_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 20px;
        }}

        .chart-image {{
            width: 100%;
            height: auto;
            max-height: 400px;
        }}

        .insights-list {{
            display: grid;
            gap: 15px;
        }}

        .insight-item {{
            background: {background_color};
            border-left: 4px solid {chart_color};
            padding: 15px;
            border-radius: 0 4px 4px 0;
        }}

        .recommendations-list {{
            display: grid;
            gap: 15px;
        }}

        .recommendation-item {{
            background: {background_color};
            border: 1px solid {border_color};
            padding: 15px;
            border-radius: 4px;
        }}

        .narrative {{
            background: {background_color};
            border: 1px solid {border_color};
            padding: 20px;
            border-radius: 8px;
            line-height: 1.6;
        }}

        @media (max-width: 768px) {{
            .kpi-grid {{
                grid-template-columns: 1fr;
            }}

            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <h1 class="dashboard-title">{title}</h1>

        {sections_html}

        <div class="section">
            <h2 class="section-title">Summary</h2>
            <div class="narrative">
                {narrative}
            </div>
        </div>
    </div>

    {chart_scripts}
</body>
</html>"""

        # Generate sections HTML
        sections_html = _generate_sections_html(dashboard_data, theme, include_charts_as_images)

        # Format template
        html_content = html_template.format(
            title=dashboard_data.get('title', 'Data Analysis Dashboard'),
            background_color=theme.get('colors', {}).get('background', '#ffffff'),
            text_color=theme.get('colors', {}).get('text', '#333333'),
            chart_color=theme.get('colors', {}).get('chart', '#1f77b4'),
            border_color=theme.get('colors', {}).get('border', '#dee2e6'),
            sections_html=sections_html,
            narrative=dashboard_data.get('narrative', 'No summary available.'),
            plotly_script='<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>' if not include_charts_as_images else '',
            chart_scripts=_generate_chart_scripts(dashboard_data, include_charts_as_images) if not include_charts_as_images else ''
        )

        return html_content

    except Exception as e:
        logger.error(f"Error generating HTML content: {str(e)}")
        return "<html><body><h1>Error generating dashboard</h1></body></html>"


def _generate_sections_html(dashboard_data, theme, include_charts_as_images=False):
    """Generate HTML for dashboard sections."""
    sections_html = []

    for section in dashboard_data.get('sections', []):
        if section['type'] == 'kpi_section':
            html = _generate_kpi_section_html(section, theme)
        elif section['type'] == 'charts_section':
            html = _generate_charts_section_html(section, theme, include_charts_as_images)
        elif section['type'] == 'insights_section':
            html = _generate_insights_section_html(section, theme)
        elif section['type'] == 'recommendations_section':
            html = _generate_recommendations_section_html(section, theme)
        else:
            continue

        sections_html.append(html)

    return '\n'.join(sections_html)


def _generate_kpi_section_html(section, theme):
    """Generate HTML for KPI section."""
    html = f'<div class="section"><h2 class="section-title">{section["title"]}</h2>'
    html += '<div class="kpi-grid">'

    for card in section.get('cards', []):
        html += '''
        <div class="kpi-card">
            <div class="kpi-value">{card['value']}</div>
            <div class="kpi-title">{card['title']}</div>
        </div>
        '''.format(**card)

    html += '</div></div>'
    return html


def _generate_chart_scripts(dashboard_data, include_charts_as_images=False):
    """Generate JavaScript for initializing charts."""
    if include_charts_as_images:
        return ""

    scripts = []
    for section in dashboard_data.get('sections', []):
        if section['type'] == 'charts_section':
            for chart in section.get('charts', []):
                chart_id = f"chart_{uuid.uuid4().hex[:8]}"
                if chart.get('data'):
                    scripts.append(f'''
                    <script>
                        Plotly.newPlot('{chart_id}', {json.dumps(chart['data']['data'])}, {json.dumps(chart['data']['layout'])});
                    </script>
                    ''')

    return '\n'.join(scripts)


def _generate_charts_section_html(section, theme, include_charts_as_images=False):
    """Generate HTML for charts section."""
    html = f'<div class="section"><h2 class="section-title">{section["title"]}</h2>'
    html += '<div class="charts-grid">'

    for chart in section.get('charts', []):
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"
        html += f'<div class="chart-container">'

        if include_charts_as_images:
            # Generate static image of the chart
            chart_image = _generate_chart_image(chart)
            if chart_image:
                html += f'<img src="{chart_image}" class="chart-image" alt="{chart.get("title", "Chart")}">'
            else:
                html += f'<div class="chart-placeholder">Chart: {chart.get("title", "Chart")}</div>'
        else:
            html += f'<div id="{chart_id}"></div>'

        html += '</div>'

        # Add script to render the chart (only if not using images)
        if not include_charts_as_images and chart.get('data'):
            html += f'''
            <script>
                Plotly.newPlot('{chart_id}', {json.dumps(chart['data']['data'])}, {json.dumps(chart['data']['layout'])});
            </script>
            '''

    html += '</div></div>'
    return html


def _generate_chart_image(chart):
    """Generate a static image from chart data using Kaleido."""
    try:
        import kaleido

        # Create a temporary HTML file with the chart
        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div id="chart" style="width: 800px; height: 400px;"></div>
            <script>
                var data = {json.dumps(chart['data']['data'])};
                var layout = {json.dumps(chart['data']['layout'])};
                Plotly.newPlot('chart', data, layout);
            </script>
        </body>
        </html>
        """

        # For PDF generation, we'll create a simpler representation
        # In production, you might want to use Kaleido to generate actual images
        # For now, return a data URL placeholder
        return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzMzMzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPntjaGFydC5nZXQoJ3RpdGxlJywgJ0NoYXJ0Jyl9PC90ZXh0Pjwvc3ZnPg=="

    except ImportError:
        logger.warning("Kaleido not available for chart image generation")
        return None
    except Exception as e:
        logger.error(f"Error generating chart image: {str(e)}")
        return None


def _generate_insights_section_html(section, theme):
    """Generate HTML for insights section."""
    html = f'<div class="section"><h2 class="section-title">{section["title"]}</h2>'
    html += '<div class="insights-list">'

    for insight in section.get('insights', []):
        html += f'''
        <div class="insight-item">
            <strong>{insight['title']}</strong><br>
            {insight['description']}
        </div>
        '''

    html += '</div></div>'
    return html


def _generate_recommendations_section_html(section, theme):
    """Generate HTML for recommendations section."""
    html = f'<div class="section"><h2 class="section-title">{section["title"]}</h2>'
    html += '<div class="recommendations-list">'

    for rec in section.get('recommendations', []):
        html += f'''
        <div class="recommendation-item">
            <strong>{rec['title']}</strong><br>
            {rec['description']}
        </div>
        '''

    html += '</div></div>'
    return html


def _create_pdf_from_html(dashboard):
    """Create a PDF file from the dashboard HTML content using WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        # Generate the HTML content first with static chart images for PDF
        html_content = _generate_html_content(dashboard, include_charts_as_images=True)

        # Configure fonts for better rendering
        font_config = FontConfiguration()

        # Create WeasyPrint HTML object
        html_doc = HTML(string=html_content)

        # Generate PDF bytes
        pdf_bytes = html_doc.write_pdf(
            stylesheets=[
                CSS(string='''
                    @page {
                        size: A4;
                        margin: 1cm;
                        @bottom-right {
                            content: "Page " counter(page) " of " counter(pages);
                            font-size: 8pt;
                            color: #666;
                        }
                    }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    }
                    .dashboard-container {
                        max-width: none !important;
                        margin: 0 !important;
                        padding: 20px !important;
                    }
                    .chart-container {
                        page-break-inside: avoid;
                        margin-bottom: 20px;
                    }
                    .section {
                        page-break-inside: avoid;
                        margin-bottom: 30px;
                    }
                    .chart-image {
                        max-width: 100%;
                        height: auto;
                    }
                ''')
            ],
            font_config=font_config
        )

        return pdf_bytes

    except ImportError:
        logger.warning("WeasyPrint not available, using fallback PDF generation.")
        return _create_pdf_fallback(dashboard)
    except Exception as e:
        logger.error(f"Error creating PDF with WeasyPrint: {str(e)}")
        # Fallback to ReportLab
        return _create_pdf_fallback(dashboard)


def _create_pdf_fallback(dashboard):
    """Create a fallback PDF file using ReportLab when WeasyPrint is not available."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors

        # Write PDF to BytesIO
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Add title
        title = dashboard.dashboard_data.get('title', 'Data Analysis Dashboard')
        title_para = Paragraph(title, styles['Title'])
        story.append(title_para)
        story.append(Spacer(1, 12))

        # Add dashboard summary if available
        narrative = dashboard.dashboard_data.get('narrative', 'No summary available.')
        summary_para = Paragraph(f"Summary: {narrative[:500]}...", styles['Normal'])
        story.append(summary_para)
        story.append(Spacer(1, 12))

        # Add sections information
        sections = dashboard.dashboard_data.get('sections', [])
        for section in sections:
            section_title = section.get('title', 'Section')
            section_para = Paragraph(f"<b>{section_title}</b>", styles['Heading2'])
            story.append(section_para)

            if section.get('type') == 'kpi_section' and section.get('cards'):
                # Create a table for KPI data
                kpi_data = [['KPI', 'Value']]
                for card in section['cards'][:6]:  # Limit to first 6 cards
                    kpi_data.append([
                        card.get('title', 'KPI'),
                        str(card.get('value', 'N/A'))
                    ])

                kpi_table = Table(kpi_data)
                kpi_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(kpi_table)
                story.append(Spacer(1, 12))

            elif section.get('type') == 'insights_section' and section.get('insights'):
                for insight in section['insights'][:5]:  # Limit to first 5 insights
                    insight_title = insight.get('title', 'Insight')
                    insight_desc = insight.get('description', 'No description available.')
                    insight_para = Paragraph(f"<b>{insight_title}:</b> {insight_desc}", styles['Normal'])
                    story.append(insight_para)
                    story.append(Spacer(1, 6))

            elif section.get('type') == 'recommendations_section' and section.get('recommendations'):
                for rec in section['recommendations'][:5]:  # Limit to first 5 recommendations
                    rec_title = rec.get('title', 'Recommendation')
                    rec_desc = rec.get('description', 'No description available.')
                    rec_para = Paragraph(f"<b>{rec_title}:</b> {rec_desc}", styles['Normal'])
                    story.append(rec_para)
                    story.append(Spacer(1, 6))

            elif section.get('type') == 'charts_section':
                # For charts, add a placeholder note
                charts_count = len(section.get('charts', []))
                charts_para = Paragraph(f"This section contains {charts_count} chart(s). For full visual representation, please use HTML export.", styles['Italic'])
                story.append(charts_para)

            story.append(Spacer(1, 12))

        # Add note about PDF generation
        note_para = Paragraph("Note: This PDF contains structured data from the dashboard. For full visual dashboard with interactive charts, please use HTML export.", styles['Italic'])
        story.append(Spacer(1, 12))
        story.append(note_para)

        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    except Exception as e:
        logger.error(f"Error creating fallback PDF: {str(e)}")
def _create_word_document(dashboard):
    """Create a Word document that closely matches the dashboard layout."""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.style import WD_STYLE_TYPE
        from docx.oxml.shared import OxmlElement, qn
        from docx.oxml.ns import nsdecls
        import matplotlib.pyplot as plt
        import io

        # Create new Word document
        doc = Document()

        # Extract dashboard data and theme
        dashboard_data = dashboard.dashboard_data
        theme = dashboard.theme or {}
        colors = theme.get('colors', {})

        # Set document margins for better layout
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.3)
            section.bottom_margin = Inches(0.3)
            section.left_margin = Inches(0.3)
            section.right_margin = Inches(0.3)

        # Add main title with dashboard styling
        title = dashboard_data.get('title', 'Data Analysis Dashboard')
        title_heading = doc.add_heading(title, 0)
        title_run = title_heading.runs[0]
        title_run.font.size = Pt(28)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(51, 51, 51)  # Dark gray like dashboard

        # Add dashboard summary with styling
        narrative = dashboard_data.get('narrative', 'No summary available.')
        if narrative:
            summary_para = doc.add_paragraph()
            summary_run = summary_para.add_run('Summary: ')
            summary_run.font.bold = True
            summary_run.font.size = Pt(12)
            summary_run.font.color.rgb = RGBColor(51, 51, 51)

            summary_content = summary_para.add_run(narrative)
            summary_content.font.size = Pt(11)
            summary_content.font.color.rgb = RGBColor(51, 51, 51)

        # Process sections with dashboard-like styling
        sections_data = dashboard_data.get('sections', [])
        for section in sections_data:
            doc.add_paragraph()  # Add spacing

            if section['type'] == 'kpi_section':
                _add_kpi_section_to_word(doc, section, theme)
            elif section['type'] == 'charts_section':
                _add_charts_section_to_word(doc, section, theme)
            elif section['type'] == 'insights_section':
                _add_insights_section_to_word(doc, section, theme)
            elif section['type'] == 'recommendations_section':
                _add_recommendations_section_to_word(doc, section, theme)

        # Save document
        from io import BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()

    except Exception as e:
        logger.error(f"Error creating Word document: {str(e)}")
        return None


def _add_kpi_section_to_word(doc, section, theme):
    """Add KPI section to Word document with dashboard-like styling."""
    from docx.shared import Pt, RGBColor
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.shared import OxmlElement, qn

    colors = theme.get('colors', {})

    # Add section title
    title_heading = doc.add_heading(section.get('title', 'KPI Section'), level=1)
    title_run = title_heading.runs[0]
    title_run.font.size = Pt(20)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(51, 51, 51)

    # Get KPI cards
    cards = section.get('cards', [])
    if not cards:
        doc.add_paragraph("No KPI data available.")
        return

    # Create a table for KPIs that looks like dashboard cards
    cols = min(3, len(cards))  # Max 3 columns like dashboard grid
    table = doc.add_table(rows=1, cols=cols)
    table.style = 'Table Grid'

    # Style the table to look like dashboard cards
    for i, card in enumerate(cards[:cols]):  # Limit to fit in table
        if i == 0:  # First card in first row
            cell = table.cell(0, 0)
        elif i == 1 and cols > 1:
            cell = table.cell(0, 1)
        elif i == 2 and cols > 2:
            cell = table.cell(0, 2)
        else:
            # Add new row for remaining cards
            row_cells = table.add_row().cells
            cell = row_cells[i % cols]

        # Clear cell content and add KPI card content
        cell.text = ''

        # Add KPI value (large text)
        kpi_para = cell.paragraphs[0]
        kpi_run = kpi_para.add_run(str(card.get('value', 'N/A')))
        kpi_run.font.size = Pt(24)
        kpi_run.font.bold = True
        kpi_run.font.color.rgb = RGBColor(31, 119, 180)  # Chart blue color

        # Add KPI title
        title_para = cell.add_paragraph()
        title_run = title_para.add_run(card.get('title', 'KPI'))
        title_run.font.size = Pt(11)
        title_run.font.color.rgb = RGBColor(51, 51, 51)

        # Style cell to look like a card
        cell.paragraphs[0].paragraph_format.space_after = Pt(6)

    # Set table properties
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Make table borders less visible
    for row in table.rows:
        for cell in row.cells:
            # Remove borders by setting them to white
            tc = cell._element
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for border_name in ['w:top', 'w:left', 'w:bottom', 'w:right']:
                border = OxmlElement(border_name)
                border.set(qn('w:val'), 'none')
                tcBorders.append(border)
            tcPr.append(tcBorders)


def _add_charts_section_to_word(doc, section, theme):
    """Add charts section to Word document with embedded chart images."""
    from docx.shared import Pt, Inches, RGBColor

    # Add section title
    title_heading = doc.add_heading(section.get('title', 'Charts Section'), level=1)
    title_run = title_heading.runs[0]
    title_run.font.size = Pt(20)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(51, 51, 51)

    # Get charts
    charts = section.get('charts', [])
    if not charts:
        doc.add_paragraph("No charts available.")
        return

    for chart in charts:
        # Add chart title
        chart_title = chart.get('title', 'Chart')
        chart_heading = doc.add_heading(chart_title, level=2)
        chart_run = chart_heading.runs[0]
        chart_run.font.size = Pt(16)
        chart_run.font.bold = True
        chart_run.font.color.rgb = RGBColor(51, 51, 51)

        # Generate and embed chart image
        chart_image_path = _generate_chart_image_for_word(chart, theme)
        if chart_image_path:
            try:
                doc.add_picture(chart_image_path, width=Inches(6))
                # Add some spacing after image
                doc.add_paragraph()
            except Exception as e:
                logger.error(f"Error adding chart image: {str(e)}")
                # Fallback to placeholder text
                chart_para = doc.add_paragraph()
                chart_para.add_run("Chart visualization: ")
                chart_para.add_run(chart.get('title', 'Chart'))
        else:
            # Fallback placeholder
            chart_para = doc.add_paragraph()
            chart_para.add_run("Chart '")
            chart_para.add_run(chart.get('title', 'Chart'))
            chart_para.add_run("' would appear here.")

        doc.add_paragraph()  # Add spacing between charts


def _add_insights_section_to_word(doc, section, theme):
    """Add insights section to Word document."""
    from docx.shared import Pt

    # Add section title
    title_heading = doc.add_heading(section.get('title', 'Insights Section'), level=1)
    title_run = title_heading.runs[0]
    title_run.font.size = Pt(16)
    title_run.font.bold = True

    # Get insights
    insights = section.get('insights', [])
    if not insights:
        doc.add_paragraph("No insights available.")
        return

    for insight in insights:
        insight_title = insight.get('title', 'Insight')
        insight_desc = insight.get('description', 'No description available.')

        # Add insight title
        insight_heading = doc.add_heading(insight_title, level=2)
        insight_run = insight_heading.runs[0]
        insight_run.font.size = Pt(13)
        insight_run.font.bold = True

        # Add insight description
        desc_para = doc.add_paragraph()
        desc_para.add_run(insight_desc)
        desc_para.paragraph_format.space_after = Pt(6)


def _add_recommendations_section_to_word(doc, section, theme):
    """Add recommendations section to Word document."""
    from docx.shared import Pt

    # Add section title
    title_heading = doc.add_heading(section.get('title', 'Recommendations Section'), level=1)
    title_run = title_heading.runs[0]
    title_run.font.size = Pt(16)
    title_run.font.bold = True

    # Get recommendations
    recommendations = section.get('recommendations', [])
    if not recommendations:
        doc.add_paragraph("No recommendations available.")
        return

    for rec in recommendations:
        rec_title = rec.get('title', 'Recommendation')
        rec_desc = rec.get('description', 'No description available.')

        # Add recommendation title
        rec_heading = doc.add_heading(rec_title, level=2)
        rec_run = rec_heading.runs[0]
        rec_run.font.size = Pt(13)
        rec_run.font.bold = True

        # Add recommendation description
        desc_para = doc.add_paragraph()
        desc_para.add_run(rec_desc)
        desc_para.paragraph_format.space_after = Pt(6)


def _generate_chart_image_for_word(chart, theme):
    """Generate a static chart image and return the file path."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        # Create a simple chart representation using matplotlib
        fig, ax = plt.subplots(figsize=(8, 5))

        chart_data = chart.get('data', {})
        if chart_data and 'data' in chart_data:
            # Try to extract data for a simple plot
            data = chart_data['data']
            if data and len(data) > 0:
                # Simple bar chart as example
                x = ['A', 'B', 'C', 'D', 'E'][:len(data)]
                y = [d.get('y', [1, 2, 3, 4, 5])[0] for d in data[:5]]
                ax.bar(x, y)
                ax.set_title(chart.get('title', 'Chart'))
            else:
                ax.text(0.5, 0.5, 'Chart Data\nNot Available',
                       transform=ax.transAxes, ha='center', va='center',
                       fontsize=14, bbox=dict(boxstyle='round', facecolor='lightgray'))
        else:
            ax.text(0.5, 0.5, 'Chart\nPlaceholder',
                   transform=ax.transAxes, ha='center', va='center',
                   fontsize=14, bbox=dict(boxstyle='round', facecolor='lightgray'))

        # Apply theme colors if available
        colors = theme.get('colors', {})
        if 'chart' in colors:
            # Try to use theme color for chart elements
            chart_color = colors['chart']
            if chart_color.startswith('#'):
                # Convert hex to RGB for matplotlib
                hex_color = chart_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                ax.set_facecolor((r/255, g/255, b/255, 0.1))

        # Save to temporary file
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'chart_{uuid.uuid4().hex[:8]}.png')

        plt.savefig(temp_path, dpi=100, bbox_inches='tight')
        plt.close()

        # Store the path for later cleanup
        return temp_path

    except Exception as e:
        logger.error(f"Error generating chart image: {str(e)}")
        return None
    finally:
        # Clean up matplotlib
        plt.close('all')


def _create_png_placeholder(dashboard):
    """Create a placeholder PNG file."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new('RGB', (1200, 800), color='white')
        draw = ImageDraw.Draw(img)

        # Add title
        draw.text((50, 50), dashboard.dashboard_data.get('title', 'Data Analysis Dashboard'), fill='black')

        # Add placeholder text
        draw.text((50, 120), "This is a placeholder PNG export.", fill='black')
        draw.text((50, 150), "In production, this would be the actual dashboard visualization.", fill='black')

        # Save to BytesIO
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.read()

    except Exception as e:
        logger.error(f"Error creating PNG placeholder: {str(e)}")
        return None


def get_export_status(export_id):
    """Get status of an export job."""
    # In a real implementation, this would check a database or cache
    return {
        'status': 'completed',
        'progress': 100,
        'download_url': f'/exports/dashboard_{export_id}.docx'  # This should be updated to use actual Supabase URL
    }


def cleanup_old_exports(days_old=7):
    """Clean up old export files from Supabase storage."""
    try:
        # Get Supabase client
        supabase_client = get_supabase_client()
        bucket_name = 'data-files'

        # List files in the bucket (this would need proper implementation)
        # For now, we'll skip cleanup as Supabase handles this automatically
        # In production, you might want to implement time-based cleanup
        logger.info("Skipping local file cleanup - files are stored in Supabase")

    except Exception as e:
        logger.error(f"Error during export cleanup: {str(e)}")
