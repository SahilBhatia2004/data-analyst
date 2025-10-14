import logging
from django.conf import settings
from .model import query_llama
from .sql_generator import generate_sql
from .db_adapter import execute_query, validate_query
import re
from .insights_extractor import extract_insights
from .dashboard_generator import generate_dashboard

logger = logging.getLogger(__name__)


class ChatbotSession:
    """
    Manages a chatbot conversation session.
    """

    def __init__(self, user, file_id=None):
        self.user = user
        self.file_id = file_id
        self.conversation_history = []
        self.current_context = {}

    def add_message(self, message, is_user=True):
        """
        Add a message to the conversation history.

        Args:
            message (str): Message content
            is_user (bool): Whether the message is from user
        """
        self.conversation_history.append({
            'message': message,
            'is_user': is_user,
            'timestamp': None  # Could add timestamp if needed
        })

    def get_conversation_context(self):
        """
        Get recent conversation context for AI model.

        Returns:
            str: Formatted conversation context
        """
        if not self.conversation_history:
            return ""

        # Get last 5 exchanges (10 messages)
        recent_messages = self.conversation_history[-10:]

        context_parts = []
        for msg in recent_messages:
            role = "User" if msg['is_user'] else "Assistant"
            context_parts.append(f"{role}: {msg['message']}")

        return "\n".join(context_parts)

    def process_query(self, user_query):
        """
        Process a user query and return response.

        Args:
            user_query (str): User's natural language query

        Returns:
            dict: Response containing answer, SQL query, and data
        """
        try:
            # Add user message to history
            self.add_message(user_query, is_user=True)

            # Validate query if file_id is provided
            if self.file_id:
                validation = validate_query(user_query, self.file_id, self.user)
                if not validation['valid']:
                    error_response = f"I couldn't understand your query. The following issues were found:\n" + "\n".join(validation['errors'])
                    self.add_message(error_response, is_user=False)
                    return {
                        'response': error_response,
                        'sql_query': None,
                        'data': None,
                        'success': False
                    }

            # Generate SQL query from natural language
            sql_query = None
            if self.file_id:
                sql_query = generate_sql(user_query, self.file_id, self.user)

            # Execute query if we have a file
            query_data = None
            if sql_query and self.file_id:
                query_data = execute_query(sql_query, self.file_id, self.user)

            # If we got query results from a file, run insights extraction and
            # generate an intelligent dashboard. The dashboard generator uses
            # the AI model to decide which charts/KPIs/trends to include
            # based on the dataset and the user's query. This allows the
            # system to create more charts than the user explicitly asked
            # for when the data warrants it.
            dashboard = None
            insights = None
            try:
                if query_data is not None:
                    # Extract insights from the full file (not just query slice)
                    insights = extract_insights(self.file_id, user_query, self.user)

                    # Generate a dashboard using insights and the user query.
                    # This will call into the AI to produce KPIs, charts, and
                    # narratives. The returned dashboard contains 'sections'
                    # with a charts section that can include AI-chosen extra
                    # visualizations.
                    dashboard = generate_dashboard(self.file_id, user_query, insights, theme=None, user=self.user)

                    # Post-process dashboard:
                    # - remove empty/placeholder charts
                    # - deduplicate charts with same type/name/data-size
                    # - ensure a consistent default layout (fix alignment)
                    try:
                        if isinstance(dashboard, dict):
                            sections = dashboard.get('sections', [])
                            new_sections = []
                            seen_signatures = set()

                            def list_nonempty(v):
                                return isinstance(v, (list, tuple)) and any(x is not None for x in v)

                            for sec in sections:
                                if not isinstance(sec, dict):
                                    new_sections.append(sec)
                                    continue

                                charts = sec.get('charts') if isinstance(sec.get('charts'), list) else []
                                filtered = []

                                for ch in charts:
                                    # remove totally empty entries
                                    if not ch or not isinstance(ch, dict):
                                        logger.debug("Removed empty/invalid chart entry from dashboard: %r", ch)
                                        continue

                                    # determine if chart contains actual data
                                    has_data = False
                                    if ch.get('figure') or ch.get('data') or ch.get('traces'):
                                        has_data = True
                                    elif list_nonempty(ch.get('x')) or list_nonempty(ch.get('y')) or list_nonempty(ch.get('values')) or list_nonempty(ch.get('labels')):
                                        has_data = True

                                    if not has_data:
                                        logger.debug("Filtered empty chart (no data) from dashboard: %r", ch)
                                        continue

                                    # build a lightweight signature to dedupe similar charts
                                    def safe_len(k):
                                        v = ch.get(k)
                                        return len(v) if isinstance(v, (list, tuple)) else 0

                                    sig = (
                                        ch.get('type'),
                                        (ch.get('name') or ch.get('title')),
                                        safe_len('x'),
                                        safe_len('y'),
                                        safe_len('values'),
                                        safe_len('labels')
                                    )

                                    if sig in seen_signatures:
                                        logger.debug("Dropped duplicate chart by signature: %s", sig)
                                        continue
                                    seen_signatures.add(sig)

                                    # ensure a consistent layout to avoid misaligned heights
                                    if 'figure' not in ch:
                                        layout = ch.get('layout', {}) or {}
                                        if not layout.get('height'):
                                            layout['height'] = 360
                                        if 'margin' not in layout:
                                            layout['margin'] = {'l': 40, 'r': 40, 't': 40, 'b': 40}
                                        # keep autosize / responsive hint
                                        layout.setdefault('autosize', True)
                                        ch['layout'] = layout

                                    filtered.append(ch)

                                # Further transform charts:
                                # - split multi-trace chart into separate single-trace charts
                                # - validate traces (matching x/y lengths or labels/values for pie)
                                # - set clear titles per-trace
                                transformed = []

                                def is_valid_trace(t):
                                    if not isinstance(t, dict):
                                        return False
                                    ttype = (t.get('type') or '').lower()
                                    if ttype == 'pie':
                                        labels = t.get('labels')
                                        values = t.get('values')
                                        return isinstance(labels, (list, tuple)) and isinstance(values, (list, tuple)) and len(labels) == len(values) and len(labels) > 0
                                    # For other traces require x and y lists of same length
                                    x = t.get('x')
                                    y = t.get('y')
                                    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
                                        return len(x) == len(y) and len(x) > 0
                                    return False

                                for ch in filtered:
                                    data_traces = ch.get('data') if isinstance(ch.get('data'), list) else []
                                    # If generator returned traces nested under 'data' as a single trace-like dict
                                    if not data_traces and isinstance(ch.get('data'), dict):
                                        data_traces = [ch.get('data')]

                                    # If there's more than one trace and they are different types, split them
                                    if len(data_traces) > 1:
                                        for t in data_traces:
                                            try:
                                                if not is_valid_trace(t):
                                                    logger.debug("Dropping invalid trace during split: %r", t)
                                                    continue

                                                new_ch = {
                                                    'type': 'plotly_chart',
                                                    'title': (t.get('name') or ch.get('title') or ch.get('name') or 'Chart').strip(),
                                                    'chart_type': t.get('type') or ch.get('chart_type'),
                                                    'data': [t],
                                                    'layout': ch.get('layout', {}) or {},
                                                    'config': ch.get('config', {'responsive': True})
                                                }
                                                transformed.append(new_ch)
                                            except Exception:
                                                logger.debug("Error splitting trace, skipping", exc_info=True)
                                                continue
                                    else:
                                        # Single-trace chart, validate and normalize
                                        t = data_traces[0] if data_traces else None
                                        if t and is_valid_trace(t):
                                            # normalize title
                                            title = (ch.get('title') or (t.get('name') if isinstance(t, dict) else None) or ch.get('name') or 'Chart')
                                            new_ch = {
                                                'type': 'plotly_chart',
                                                'title': title.strip(),
                                                'chart_type': (t.get('type') or ch.get('chart_type')),
                                                'data': [t],
                                                'layout': ch.get('layout', {}) or {},
                                                'config': ch.get('config', {'responsive': True})
                                            }
                                            transformed.append(new_ch)
                                        else:
                                            logger.debug("Dropped single invalid chart: %r", ch)

                                # If too many charts, prefer those related to user query or insights
                                max_charts = 8
                                final_charts = transformed
                                if len(transformed) > max_charts:
                                    # Build keywords from user query and insight titles
                                    keywords = set()
                                    try:
                                        q_words = re.findall(r"\w+", user_query.lower()) if user_query else []
                                        keywords.update(q_words)
                                        # include insight metric names
                                        if insights and isinstance(insights, dict):
                                            for k in ('kpis', 'trends', 'patterns', 'insights'):
                                                items = insights.get(k) or []
                                                for it in items:
                                                    if isinstance(it, dict):
                                                        for v in it.values():
                                                            if isinstance(v, str):
                                                                for w in re.findall(r"\w+", v.lower()):
                                                                    keywords.add(w)
                                    except Exception:
                                        keywords = set()

                                    def score_chart(c):
                                        s = 0
                                        txt = ' '.join([str(c.get('title') or ''), str(c.get('chart_type') or '')]).lower()
                                        for kw in keywords:
                                            if kw and kw in txt:
                                                s += 1
                                        return s

                                    scored = sorted([(score_chart(c), c) for c in transformed], key=lambda x: x[0], reverse=True)
                                    best = [c for sc, c in scored if sc > 0]
                                    if best:
                                        final_charts = best[:max_charts]
                                    else:
                                        final_charts = [c for _, c in scored][:max_charts]

                                sec['charts'] = final_charts
                                new_sections.append(sec)

                            dashboard['sections'] = new_sections
                    except Exception as e:
                        logger.warning(f"Failed to post-process dashboard charts: {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"Failed to generate insights/dashboard: {str(e)}", exc_info=True)

            # Generate AI response
            context = self.get_conversation_context()
            if query_data:
                data_context = f"Query results: {str(query_data[:3])}"  # First 3 rows for context
                ai_prompt = f"{context}\n\n{data_context}\n\nUser query: {user_query}\n\nProvide a helpful response explaining these results:"
            else:
                ai_prompt = f"{context}\n\nUser query: {user_query}\n\nProvide a helpful response:"

            ai_response = query_llama(ai_prompt)

            if not ai_response:
                ai_response = "I'm having trouble generating a response right now. Please try again."

            # Add AI response to history
            self.add_message(ai_response, is_user=False)

            return {
                'response': ai_response,
                'sql_query': sql_query,
                'data': query_data,
                'insights': insights,
                'dashboard': dashboard,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error processing chatbot query: {str(e)}")
            error_response = "I encountered an error while processing your request. Please try again."
            self.add_message(error_response, is_user=False)

            return {
                'response': error_response,
                'sql_query': None,
                'data': None,
                'success': False
            }


def handle_chat_message(message, session_id, file_id, user):
    """
    Handle a chat message and return response.

    Args:
        message (str): User's message
        session_id (str): Chat session ID
        file_id (int): File ID for context
        user: Django user object

    Returns:
        dict: Chat response
    """
    try:
        # Get or create session
        if session_id:
            # In a real implementation, you'd retrieve the session from database
            # For this example, we'll create a new session each time
            session = ChatbotSession(user, file_id)
        else:
            session = ChatbotSession(user, file_id)

        # Process the message
        response = session.process_query(message)

        return response

    except Exception as e:
        logger.error(f"Error handling chat message: {str(e)}")
        return {
            'response': 'An error occurred while processing your message.',
            'sql_query': None,
            'data': None,
            'success': False
        }


def generate_follow_up_questions(current_query, data_summary, user):
    """
    Generate follow-up questions based on current analysis.

    Args:
        current_query (str): Current user query
        data_summary (str): Summary of the data/results
        user: Django user object

    Returns:
        list: List of suggested follow-up questions
    """
    try:
        prompt = f"""Based on this data analysis:

Current query: {current_query}
Data summary: {data_summary}

Generate 3-4 relevant follow-up questions that a user might want to ask next.
Make them specific and actionable. Format as a simple list."""

        response = query_llama(prompt, max_tokens=300)

        if response:
            # Parse questions from response
            questions = []
            lines = response.split('\n')

            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                    # Clean up the question
                    question = re.sub(r'^[-•]\s*', '', line)
                    question = re.sub(r'^\d+\.\s*', '', question)
                    if question:
                        questions.append(question)

            return questions[:4]  # Return max 4 questions

        return []

    except Exception as e:
        logger.error(f"Error generating follow-up questions: {str(e)}")
        return []


def explain_data_patterns(data_summary, user):
    """
    Explain patterns and insights in the data.

    Args:
        data_summary (str): Summary of the data
        user: Django user object

    Returns:
        str: Explanation of data patterns
    """
    try:
        prompt = f"""Analyze this data and explain any patterns, trends, or insights you can identify:

{data_summary}

Provide a clear, professional explanation focusing on:
1. Key patterns or trends
2. Notable outliers or anomalies
3. Business implications
4. Recommendations"""

        return query_llama(prompt, max_tokens=500)

    except Exception as e:
        logger.error(f"Error explaining data patterns: {str(e)}")
        return "Unable to analyze data patterns at this time."


def suggest_dashboard_elements(data_summary, columns, user):
    """
    Suggest dashboard elements based on data.

    Args:
        data_summary (str): Summary of the data
        columns (list): List of column information
        user: Django user object

    Returns:
        list: Suggested dashboard elements
    """
    try:
        columns_str = "\n".join([f"- {col['name']} ({col['type']})" for col in columns])

        prompt = f"""Based on this data:

Columns:
{columns_str}

Data summary: {data_summary}

Suggest 4-6 key dashboard elements (charts, KPIs, tables) that would be most valuable for this data.
For each element, specify:
1. Type (KPI card, bar chart, line chart, table, etc.)
2. What it should show
3. Why it's useful

Format as a numbered list."""

        response = query_llama(prompt, max_tokens=400)

        if response:
            # Parse suggestions from response
            suggestions = []
            lines = response.split('\n')

            for line in lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                    suggestions.append(line.strip())

            return suggestions[:6]

        return []

    except Exception as e:
        logger.error(f"Error suggesting dashboard elements: {str(e)}")
        return []
