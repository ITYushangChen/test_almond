from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from supabase_client import get_supabase
from datetime import datetime, timedelta
from collections import defaultdict
import os
import re
from openai import OpenAI
from config import Config
import requests
import json
import psycopg2
from psycopg2.extras import RealDictCursor

ai_analysis_bp = Blueprint('ai_analysis', __name__)

# Initialize OpenAI client
def get_openai_client():
    api_key = Config.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)

# Execute SQL using Supabase REST API via RPC
def execute_sql_via_supabase(sql_query):
    """
    Execute SQL query using Supabase REST API via RPC
    Uses Supabase's RPC (Remote Procedure Call) functionality
    """
    supabase = get_supabase()
    supabase_url = Config.SUPABASE_URL
    
    # Clean and validate SQL query
    cleaned_sql = clean_sql_query(sql_query)
    if not cleaned_sql:
        raise ValueError("Invalid SQL query: unbalanced quotes or empty query")
    sql_query = cleaned_sql
    
    # Try to use service_role key for executing SQL via RPC
    # If not available, try using existing SUPABASE_KEY
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    api_key = service_role_key if service_role_key else Config.SUPABASE_KEY
    
    # Use Supabase RPC to execute SQL via a database function
    # First, try to call the execute_sql function if it exists
    try:
        # Call RPC function to execute SQL
        # This requires a database function to be created in Supabase
        response = supabase.rpc('execute_sql', {'query_text': sql_query}).execute()
        # Handle different response formats
        if hasattr(response, 'data'):
            data = response.data
        else:
            data = response if isinstance(response, list) else []
        
        # If data is a JSON string, parse it
        if isinstance(data, str):
            import json
            data = json.loads(data)
        
        # If data is a single JSON object, wrap it in a list
        if isinstance(data, dict):
            data = [data]
        
        return data if data else []
    except Exception as e:
        # If RPC function doesn't exist, try using HTTP request directly
        # This uses PostgREST's RPC endpoint
        try:
            import requests
            headers = {
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            # Try to call execute_sql function via REST API
            rpc_url = f"{supabase_url}/rest/v1/rpc/execute_sql"
            response = requests.post(
                rpc_url,
                headers=headers,
                json={'query_text': sql_query},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json() if isinstance(response.json(), list) else []
            elif response.status_code == 404:
                # Function doesn't exist, provide instructions
                raise ValueError(
                    "Database function 'execute_sql' not found. "
                    "Please create it in Supabase SQL Editor:\n\n"
                    "CREATE OR REPLACE FUNCTION execute_sql(query_text TEXT)\n"
                    "RETURNS JSON\n"
                    "LANGUAGE plpgsql\n"
                    "SECURITY DEFINER\n"
                    "AS $$\n"
                    "DECLARE\n"
                    "  result JSON;\n"
                    "BEGIN\n"
                    "  -- Only allow SELECT statements\n"
                    "  IF upper(trim(query_text)) NOT LIKE 'SELECT%' THEN\n"
                    "    RAISE EXCEPTION 'Only SELECT statements are allowed';\n"
                    "  END IF;\n"
                    "  EXECUTE format('SELECT json_agg(row_to_json(t)) FROM (%s) t', query_text) INTO result;\n"
                    "  RETURN COALESCE(result, '[]'::JSON);\n"
                    "END;\n"
                    "$$;\n\n"
                    "GRANT EXECUTE ON FUNCTION execute_sql TO anon, authenticated;"
                )
            else:
                raise ValueError(f"RPC call failed: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to execute SQL via RPC: {str(e)}")


def clean_sql_query(sql):
    """Clean and normalize SQL query to prevent syntax errors"""
    if not sql:
        return None
    
    # Remove leading/trailing whitespace
    sql = sql.strip()
    
    # Remove trailing semicolon
    sql = sql.rstrip(';').strip()
    
    # Remove any trailing dots that might indicate truncation
    sql = sql.rstrip('...').strip()
    
    # Remove any backticks that might interfere
    sql = sql.replace('`', '')
    
    # Fix common quote issues - ensure single quotes are properly closed
    # Count single quotes to detect unclosed strings
    single_quote_count = sql.count("'")
    if single_quote_count % 2 != 0:
        # Odd number of quotes means unclosed string
        # Try to detect if it's just a trailing quote issue
        # Check if the last non-whitespace character is a quote
        sql_stripped = sql.rstrip()
        if sql_stripped and sql_stripped[-1] == "'":
            # Might be a closing quote, but let's be safe and return None
            return None
        # Otherwise, definitely unbalanced
        return None
    
    # Normalize whitespace but preserve newlines in a smarter way
    # Replace multiple spaces/tabs with single space, but keep single newlines
    sql = re.sub(r'[ \t]+', ' ', sql)  # Multiple spaces/tabs -> single space
    sql = re.sub(r'\n\s*\n', '\n', sql)  # Multiple newlines -> single newline
    # Keep single newlines as they help readability
    
    return sql.strip()


def validate_sql(sql):
    """Validate SQL is safe - only allow SELECT statements"""
    if not sql:
        return False, "Empty SQL query"
    
    sql_upper = sql.strip().upper()
    
    # Remove comments and whitespace
    sql_clean = re.sub(r'--.*?\n', '', sql_upper)
    sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
    sql_clean = ' '.join(sql_clean.split())
    
    # Check if it starts with SELECT
    if not sql_clean.startswith('SELECT'):
        return False, "Only SELECT statements are allowed"
    
    # Block dangerous keywords
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE',
        'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', 'MERGE', 'COPY'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_clean:
            return False, f"Keyword '{keyword}' is not allowed for security reasons"
    
    # Check for balanced quotes
    single_quotes = sql.count("'")
    if single_quotes % 2 != 0:
        return False, "Unbalanced single quotes in SQL query"
    
    return True, None


def extract_sql_from_response(response_text):
    """Extract SQL code from LLM response with improved parsing"""
    if not response_text:
        return None
    
    # Look for SQL code blocks (most reliable) - try multiple patterns
    # Use non-greedy matching but ensure we capture the full block
    sql_patterns = [
        r'```\s*sql\s*\n?(.*?)\n?\s*```',  # ```sql\n...\n``` or ```sql...``` (flexible)
        r'```sql\s*(.*?)\s*```',  # ```sql ... ``` (no newlines)
        r'```\s*sql\s*(.*?)\s*```',  # ``` sql ... ``` (with space)
        r'```\s*(SELECT.*?)\s*```',  # ``` SELECT ... ```
        r'```\s*(select.*?)\s*```',  # Case insensitive
    ]
    
    for pattern in sql_patterns:
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            # Remove leading/trailing quotes if any
            sql = sql.strip('"\'')
            # Remove any trailing dots that might be from truncated output
            sql = sql.rstrip('...').strip()
            # Clean the SQL
            cleaned_sql = clean_sql_query(sql)
            if cleaned_sql:
                return cleaned_sql
            # Even if clean_sql_query fails, return the original if it looks like valid SQL
            if sql.strip().upper().startswith('SELECT'):
                # Basic validation: check if it has balanced quotes
                quote_count = sql.count("'")
                if quote_count % 2 == 0:  # Balanced quotes
                    return sql.strip()
    
    # If no code block, try to find SELECT statement directly
    # Match from SELECT to end of statement (better handling of quotes)
    select_patterns = [
        r'(SELECT\s+.*?)(?=\n\n|\n```|$)',  # Until double newline or code block
        r'(SELECT\s+.*?)(?=\n[^\s]|$)',  # Until next non-indented line or end
        r'(SELECT\s+.*)',  # Everything after SELECT
    ]
    
    for pattern in select_patterns:
        select_match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if select_match:
            sql = select_match.group(1).strip()
            sql = sql.strip('"\'')
            sql = sql.rstrip('...').strip()
            # Only process if it looks like SQL
            if sql.upper().startswith('SELECT'):
                cleaned_sql = clean_sql_query(sql)
                if cleaned_sql:
                    return cleaned_sql
                # Even if clean fails, return if quotes are balanced
                quote_count = sql.count("'")
                if quote_count % 2 == 0:
                    return sql.strip()
    
    return None


def normalize_theme_name(name):
    """Normalize theme name to match database format (lowercase, underscores)"""
    if not name:
        return None
    # Convert to lowercase, replace spaces/hyphens with underscores
    normalized = name.lower().strip()
    normalized = re.sub(r'[\s\-]+', '_', normalized)
    return normalized


def get_available_themes():
    """Get all available base_theme and sub_theme values from database"""
    try:
        supabase = get_supabase()
        # Use a large limit to get all themes - we only need unique values so even with many rows, 
        # the unique set will be manageable. Using DISTINCT in query would be better but Supabase 
        # client doesn't support it directly, so we fetch rows and extract unique values in Python
        response = supabase.table('cb').select('base_theme,sub_theme').limit(100000).execute()
        data = response.data
        
        exclude_values = ['others', 'stock_market']
        
        base_themes = sorted(set(
            d.get('base_theme') for d in data 
            if d.get('base_theme') and d.get('base_theme') not in exclude_values
        ))
        
        sub_themes = sorted(set(
            d.get('sub_theme') for d in data 
            if d.get('sub_theme') and d.get('sub_theme') not in exclude_values
        ))
        
        return base_themes, sub_themes
    except Exception as e:
        print(f"Error fetching themes: {e}")
        return [], []


def create_theme_mapping_guide(base_themes, sub_themes):
    """Create a comprehensive guide for AI to understand theme name mappings"""
    guide = []
    
    # Base themes mapping - limit to first 20 to avoid token limits
    guide.append("\n=== Available Base Themes ===")
    for theme in base_themes[:20]:
        if not theme:
            continue
        # Common variations
        variations = [
            theme,
            theme.lower(),
            theme.replace('_', ' '),
            theme.replace('_', '-'),
        ]
        guide.append(f"  Database value: '{theme}'")
        guide.append(f"    Common variations: {', '.join(set(variations))}")
    
    if len(base_themes) > 20:
        guide.append(f"\n  ... and {len(base_themes) - 20} more base themes")
    
    # Sub themes mapping - limit to first 30 to avoid token limits
    guide.append("\n=== Available Sub Themes ===")
    for theme in sub_themes[:30]:
        if not theme:
            continue
        variations = [
            theme,
            theme.lower(),
            theme.replace('_', ' '),
            theme.replace('_', '-'),
        ]
        guide.append(f"  Database value: '{theme}'")
        guide.append(f"    Common variations: {', '.join(set(variations))}")
    
    if len(sub_themes) > 30:
        guide.append(f"\n  ... and {len(sub_themes) - 30} more sub themes")
    
    result = "\n".join(guide)
    # Limit total length to 4000 characters to avoid token overflow
    if len(result) > 4000:
        result = result[:4000] + "\n\n... (theme list truncated to avoid token limits)"
    
    return result


def generate_ai_analysis(user_message, query_results, sql_query, client):
    """
    Use AI to analyze query results and generate comprehensive analysis.
    Returns a dictionary with:
    - full_analysis: Complete natural language analysis with insights and recommendations
    - summary: Short summary (fallback)
    """
    if not query_results or len(query_results) == 0:
        return {
            'full_analysis': '📊 Query executed successfully, but no results were found.\n\nSuggestions:\n- Try adjusting your query parameters or date range\n- Check if your filter conditions are correct',
            'summary': 'Query executed successfully, but no results were found.'
        }
    
    # Prepare data for AI - use all data for better analysis
    total_rows = len(query_results)
    
    # For very large datasets, use more data but still need to be mindful of token limits
    # Send up to 1000 rows for analysis (increased from 30)
    if total_rows > 1000:
        # For very large datasets, sample more strategically: first 800 + last 200
        sample_data = query_results[:800] + query_results[-200:]
        data_summary = {
            'total_rows': total_rows,
            'columns': list(query_results[0].keys()) if query_results else [],
            'sample_data': sample_data,  # Include up to 1000 rows for analysis
            'is_sampled': True,
            'note': f'Showing sample of {len(sample_data)} rows out of {total_rows} total rows'
        }
    else:
        # For smaller datasets, use all data
        data_summary = {
            'total_rows': total_rows,
            'columns': list(query_results[0].keys()) if query_results else [],
            'sample_data': query_results,  # Include all rows
            'is_sampled': False
        }
    
    # Analyze user's request to determine if they want analysis or just data
    user_wants_analysis = any(keyword in user_message.lower() for keyword in [
        'analysis', 'analyze', 'insight', 'insights', 'findings', 'recommendation', 
        'trend', 'pattern', 'why', 'reason', 'deep', 'comprehensive', 'detailed analysis',
        'summarize', 'summary', 'summarise', 'what are', 'what do', 'tell me about',
        'describe', 'explain', 'overview', 'overall'
    ])
    
    # Create prompt for AI analysis (English only)
    if user_wants_analysis:
        # Determine the type of request
        is_summary_request = any(keyword in user_message.lower() for keyword in [
            'summarize', 'summary', 'summarise', 'what are', 'what do', 'tell me about'
        ])
        
        if is_summary_request:
            # User wants a summary/overview
            analysis_prompt = f"""You are a professional data analyst specializing in corporate sentiment data analysis.

User's Request: {user_message}

SQL Query Executed:
```sql
{sql_query}
```

Query Results:
- Total rows: {data_summary['total_rows']}
- Columns: {', '.join(data_summary['columns'])}
- Data: {f"{data_summary.get('note', '')} - " if data_summary.get('is_sampled') else ''}{len(data_summary['sample_data'])} rows shown below
{json.dumps(data_summary['sample_data'], default=str, ensure_ascii=False, indent=2)}

Your Task: Provide a clear, concise summary that directly answers the user's question.

CRITICAL Requirements:
1. **Directly answer the user's question** - If they ask "what are employees saying about X", summarize the key points employees are making about X
2. **Focus on content and sentiment** - Analyze the actual content/sentiment of comments, not just statistics
3. **Use specific examples** - Reference actual themes, sentiments, or patterns found in the data
4. **Be concise but informative** - Provide a comprehensive summary in 3-5 paragraphs
5. **Structure your response**:
   - Start with a brief overview of what the data shows
   - Highlight the main themes/topics employees are discussing
   - Summarize the overall sentiment (positive/negative/neutral patterns)
   - Mention any notable patterns or concerns if relevant

Format:
- Use clear paragraphs, not bullet points unless specifically requested
- Use emojis sparingly (only for emphasis)
- Reference specific numbers when relevant (e.g., "out of {data_summary['total_rows']} comments")
- If the dataset is large and sampled, acknowledge this but still provide insights based on the sample

Example structure for "Summarize what employees are saying about inclusion and safety":
- Overview: "Based on {data_summary['total_rows']} comments about inclusion and safety, employees are discussing..."
- Main themes: "The primary topics include..."
- Sentiment: "Overall sentiment is..."
- Key points: "Employees are expressing concerns/positive feedback about..."

Reply in English. Provide the summary directly, not in JSON format."""
        else:
            # User wants detailed analysis
            analysis_prompt = f"""You are a professional data analyst specializing in corporate sentiment data analysis.

User's Original Request: {user_message}

SQL Query Executed:
```sql
{sql_query}
```

Query Results:
- Total rows: {data_summary['total_rows']}
- Columns: {', '.join(data_summary['columns'])}
- Data: {f"{data_summary.get('note', '')} - " if data_summary.get('is_sampled') else ''}{len(data_summary['sample_data'])} rows shown below
{json.dumps(data_summary['sample_data'], default=str, ensure_ascii=False, indent=2)}

Please provide a comprehensive, in-depth analysis report based on the above data. The report should include:

1. **Data Overview**: Briefly summarize the query results, using specific numbers to explain what was found
2. **Key Findings**: Identify 3-5 most important insights (trends, anomalies, patterns, etc.), supported by data
3. **Deep Analysis**: Provide in-depth explanation of key findings and why they matter
4. **Actionable Recommendations**: Provide 2-3 specific, actionable recommendations

Requirements:
- Reply in English
- Be specific and data-driven - reference actual numbers, percentages, trends
- Focus on business value and actionability
- For sentiment data, highlight positive/negative trends and areas needing attention
- Use clear formatting with emojis and markdown for better readability
- If the dataset is large and sampled, note that your analysis is based on a sample but should consider the total row count

Please provide the complete analysis report directly, not in JSON format."""
    else:
        # User just wants data/listing, not analysis
        analysis_prompt = f"""You are a data assistant helping users understand query results.

User's Original Request: {user_message}

SQL Query Executed:
```sql
{sql_query}
```

Query Results:
- Total rows: {data_summary['total_rows']}
- Columns: {', '.join(data_summary['columns'])}
- Data: {f"{data_summary.get('note', '')} - " if data_summary.get('is_sampled') else ''}{len(data_summary['sample_data'])} rows shown below
{json.dumps(data_summary['sample_data'], default=str, ensure_ascii=False, indent=2)}

Important Requirements:
- **Only answer what the user explicitly asked for. Do NOT add extra analysis, insights, or recommendations.**
- If the user just wants to list or display data, only provide data overview and listing
- Only provide analysis if the user explicitly requests it
- Reply in English
- Use clear formatting with emojis and markdown for better readability
- If the dataset is large and sampled, note that your response is based on a sample but should consider the total row count

Please answer the user's question directly without adding content they didn't ask for."""
    
    try:
        # Call OpenAI for analysis - return as plain text, not JSON
        if user_wants_analysis:
            is_summary = any(keyword in user_message.lower() for keyword in [
                'summarize', 'summary', 'summarise', 'what are', 'what do', 'tell me about'
            ])
            if is_summary:
                system_prompt_english = "You are a professional data analyst specializing in corporate sentiment data analysis. When users ask for summaries, you provide clear, concise summaries that directly answer their questions by analyzing the actual content and sentiment of the data."
            else:
                system_prompt_english = "You are a professional data analyst specializing in corporate sentiment data analysis. When users request analysis, you always provide clear, in-depth, actionable analysis reports."
        else:
            system_prompt_english = "You are a data assistant helping users understand query results. You only answer what users explicitly ask for, without adding extra analysis or recommendations."
        
        analysis_response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt_english},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7,
            max_tokens=10000  # Increased for better summaries
        )
        
        full_analysis = analysis_response.choices[0].message.content.strip()
        
        # Don't add redundant summary prefix if the AI already provided a good response
        # Only add it if the response seems incomplete
        if not full_analysis or len(full_analysis) < 50:
            summary_prefix = f"✅ Query executed successfully, found {total_rows} results.\n\n"
            full_analysis = summary_prefix + full_analysis
        else:
            # Just add a brief success indicator at the start if not present
            if not full_analysis.startswith('✅') and not full_analysis.startswith('📊'):
                full_analysis = f"✅ Query executed successfully, found {total_rows} results.\n\n{full_analysis}"
        
        return {
            'full_analysis': full_analysis,
            'summary': f'Query executed successfully, found {total_rows} results.'
        }
        
    except Exception as e:
        # Fallback if AI analysis fails - provide basic statistics instead of error message
        import traceback
        print(f"AI analysis error: {traceback.format_exc()}")
        
        # Try to provide some basic insights from the data even without AI
        try:
            # Calculate basic statistics
            sentiment_counts = {}
            theme_counts = {}
            for row in query_results[:1000]:  # Sample for performance
                sentiment = row.get('sentiment', 'neutral')
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                
                base_theme = row.get('base_theme')
                if base_theme:
                    theme_counts[base_theme] = theme_counts.get(base_theme, 0) + 1
            
            # Build a basic summary
            sentiment_summary = ", ".join([f"{k}: {v}" for k, v in sorted(sentiment_counts.items(), key=lambda x: -x[1])])
            top_themes = sorted(theme_counts.items(), key=lambda x: -x[1])[:5]
            themes_summary = ", ".join([f"{theme}" for theme, count in top_themes])
            
            fallback_msg = f"""✅ Query executed successfully!

Found {total_rows} results.

**Basic Statistics:**
- Sentiment distribution: {sentiment_summary}
- Top themes: {themes_summary}

**Note:** Detailed AI analysis is currently unavailable. The above statistics are based on a sample of the data. For a comprehensive analysis, please try again later or review the raw data."""
        except:
            # If statistics calculation fails, use simple message
            fallback_msg = f"""✅ Query executed successfully!

Found {total_rows} results.

Columns: {', '.join(data_summary['columns'])}

**Note:** Detailed AI analysis is currently unavailable. Please try again later or review the raw data for insights."""
        
        return {
            'full_analysis': fallback_msg,
            'summary': f'Query executed successfully, found {total_rows} results.'
        }


@ai_analysis_bp.route('/hot-topics-sentiment', methods=['GET'])
def get_hot_topics_sentiment():
    """Get recent hot topics and their sentiment trends"""
    supabase = get_supabase()
    
    # Get data from the last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Query data, excluding others and stock_market
    query = supabase.table('cb').select('date,base_theme,sub_theme,sentiment,likes,content')
    query = query.gte('date', start_date)
    query = query.lte('date', end_date)
    query = query.neq('base_theme', 'others')
    query = query.neq('base_theme', 'stock_market')
    query = query.neq('sub_theme', 'others')
    query = query.limit(10000)
    
    response = query.execute()
    data = response.data
    
    # Count hot topics
    topic_stats = defaultdict(lambda: {
        'count': 0,
        'likes_total': 0,
        'daily_sentiment': defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0}),
        'sample_contents': []
    })
    
    for item in data:
        theme = item.get('base_theme')
        if not theme:
            continue
            
        date = item.get('date')[:10] if item.get('date') else None
        sentiment = item.get('sentiment', 'neutral')
        likes = item.get('likes', 0)
        content = item.get('content', '')
        
        topic_stats[theme]['count'] += 1
        topic_stats[theme]['likes_total'] += likes
        
        # Record daily sentiment
        if date and sentiment:
            topic_stats[theme]['daily_sentiment'][date][sentiment] += 1
        
        # Save first 5 content samples
        if len(topic_stats[theme]['sample_contents']) < 5 and content:
            topic_stats[theme]['sample_contents'].append(content[:200])
    
    # Calculate hotness score and sort
    hot_topics = []
    for theme, stats in topic_stats.items():
        # Hotness score = comment count * 0.3 + likes * 0.7
        hotness_score = stats['count'] * 0.3 + stats['likes_total'] * 0.7
        
        # Process daily sentiment trends
        daily_trends = []
        for date in sorted(stats['daily_sentiment'].keys()):
            sentiment_data = stats['daily_sentiment'][date]
            total = sum(sentiment_data.values())
            if total > 0:
                daily_trends.append({
                    'date': date,
                    'positive': sentiment_data['positive'],
                    'negative': sentiment_data['negative'],
                    'neutral': sentiment_data['neutral'],
                    'positive_rate': round(sentiment_data['positive'] / total * 100, 2),
                    'negative_rate': round(sentiment_data['negative'] / total * 100, 2),
                    'total': total
                })
        
        # Calculate overall sentiment distribution
        total_positive = sum(d['positive'] for d in stats['daily_sentiment'].values())
        total_negative = sum(d['negative'] for d in stats['daily_sentiment'].values())
        total_neutral = sum(d['neutral'] for d in stats['daily_sentiment'].values())
        total_comments = total_positive + total_negative + total_neutral
        
        sentiment_distribution = {
            'positive': total_positive,
            'negative': total_negative,
            'neutral': total_neutral,
            'positive_rate': round(total_positive / total_comments * 100, 2) if total_comments > 0 else 0,
            'negative_rate': round(total_negative / total_comments * 100, 2) if total_comments > 0 else 0,
            'neutral_rate': round(total_neutral / total_comments * 100, 2) if total_comments > 0 else 0
        }
        
        hot_topics.append({
            'theme': theme,
            'hotness_score': round(hotness_score, 2),
            'total_comments': stats['count'],
            'total_likes': stats['likes_total'],
            'sentiment_distribution': sentiment_distribution,
            'daily_trends': daily_trends,
            'sample_contents': stats['sample_contents']
        })
    
    # Sort by hotness, take top 10
    hot_topics.sort(key=lambda x: x['hotness_score'], reverse=True)
    top_topics = hot_topics[:10]
    
    return jsonify({
        'period': {
            'start': start_date,
            'end': end_date
        },
        'topics': top_topics
    }), 200


@ai_analysis_bp.route('/generate-insights', methods=['POST'])
def generate_insights():
    """Generate insights using AI (currently returns mock data)"""
    data = request.get_json() or {}
    topics = data.get('topics', [])
    
    # TODO: Integrate OpenAI API
    # For now return mock insights
    mock_insights = []
    
    for topic in topics[:3]:  # Only analyze top 3 hottest topics
        theme = topic['theme']
        sentiment = topic['sentiment_distribution']
        
        insight = {
            'theme': theme,
            'key_findings': [],
            'recommendations': []
        }
        
        # Generate mock insights based on sentiment
        if sentiment['negative_rate'] > 40:
            insight['key_findings'].append(f"{theme} shows significant negative sentiment ({sentiment['negative_rate']}%)")
            insight['recommendations'].append(f"Immediate attention needed for {theme} issues")
            insight['risk_level'] = 'high'
        elif sentiment['positive_rate'] > 60:
            insight['key_findings'].append(f"{theme} has strong positive engagement ({sentiment['positive_rate']}%)")
            insight['recommendations'].append(f"Continue current approach for {theme}")
            insight['risk_level'] = 'low'
        else:
            insight['key_findings'].append(f"{theme} shows mixed sentiment")
            insight['recommendations'].append(f"Monitor {theme} closely for changes")
            insight['risk_level'] = 'medium'
        
        # Analyze trends
        if len(topic['daily_trends']) > 7:
            recent = topic['daily_trends'][-7:]
            early = topic['daily_trends'][:7]
            recent_positive = sum(d['positive_rate'] for d in recent) / len(recent)
            early_positive = sum(d['positive_rate'] for d in early) / len(early)
            
            if recent_positive > early_positive + 10:
                insight['key_findings'].append("Sentiment improving over time")
            elif recent_positive < early_positive - 10:
                insight['key_findings'].append("Sentiment declining - requires attention")
            
        mock_insights.append(insight)
    
    return jsonify({
        'insights': mock_insights,
        'generated_at': datetime.now().isoformat(),
        'ai_model': 'gpt-4 (simulated)'
    }), 200


@ai_analysis_bp.route('/chat', methods=['POST'])
def chat():
    """AI chat interface - uses OpenAI to understand user intent, generate SQL and execute"""
    data = request.get_json() or {}
    message = data.get('message', '')
    conversation_history = data.get('conversation_history', [])  # Get conversation history
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Check OpenAI API key
    if not Config.OPENAI_API_KEY:
        return jsonify({
            'error': 'OpenAI API key not configured',
            'response': 'Please configure OPENAI_API_KEY in your .env file'
        }), 500
    
    try:
        client = get_openai_client()
        
        # Get available themes from database
        try:
            base_themes, sub_themes = get_available_themes()
            theme_mapping_guide = create_theme_mapping_guide(base_themes, sub_themes)
        except Exception as e:
            print(f"Error getting themes: {e}")
            import traceback
            print(traceback.format_exc())
            # Fallback: use empty guide if theme fetching fails
            base_themes, sub_themes = [], []
            theme_mapping_guide = "\n=== Available Base Themes ===\n(Unable to fetch themes from database)\n\n=== Available Sub Themes ===\n(Unable to fetch themes from database)"
        
        # Get database schema information
        schema_info = """
        Table: cb
        Columns:
        - id (BIGINT, PRIMARY KEY)
        - date (DATE/TIMESTAMP)
        - likes (INTEGER)
        - base_theme (TEXT)
        - sub_theme (TEXT)
        - sentiment (TEXT: 'positive', 'negative', 'neutral')
        - language (TEXT)
        - content (TEXT)
        
        Important filters:
        - Always exclude rows where base_theme = 'others' or base_theme = 'stock_market'
        - Always exclude rows where sub_theme = 'others'
        - You can query all data without LIMIT - the system will handle large result sets intelligently
        """
        
        # Create prompt for OpenAI
        system_prompt = f"""You are a SQL query generator for analyzing corporate culture sentiment data.

Database Schema:
{schema_info}

{theme_mapping_guide}

CRITICAL: Theme Name Matching Rules:
1. When users mention themes in natural language (e.g., "Workplace harassment", "workplace harassment", "Workplace_Harassment"), you MUST map them to the EXACT database values shown above.
2. Theme names in the database may use underscores, lowercase, or mixed case. Use the EXACT values from the "Database value" lists above.
3. If a user mentions "workplace harassment" or "Workplace harassment", search in BOTH base_theme and sub_theme columns using pattern matching.
4. ALWAYS use case-insensitive pattern matching for theme names. Use one of these patterns:
   - ILIKE: WHERE base_theme ILIKE '%workplace%harassment%' OR sub_theme ILIKE '%workplace%harassment%'
   - Pattern matching: WHERE LOWER(REPLACE(base_theme, '_', ' ')) LIKE '%workplace harassment%' OR LOWER(REPLACE(sub_theme, '_', ' ')) LIKE '%workplace harassment%'
   - OR: WHERE LOWER(base_theme) LIKE '%workplace%harassment%' OR LOWER(sub_theme) LIKE '%workplace%harassment%'
5. For queries about specific themes, check BOTH base_theme and sub_theme columns, as "Workplace harassment" might be in either column.
6. Example: If user asks about "Workplace harassment", generate:
   SELECT * FROM cb 
   WHERE (LOWER(REPLACE(base_theme, '_', ' ')) LIKE '%workplace harassment%' 
          OR LOWER(REPLACE(sub_theme, '_', ' ')) LIKE '%workplace harassment%')
     AND base_theme NOT IN ('others', 'stock_market')
     AND sub_theme != 'others'

CRITICAL: Counting and Statistics Queries:
When users ask about "how many", "count", "number of", "total number", etc., you MUST:
1. Use COUNT(DISTINCT column) to count UNIQUE values, NOT COUNT(*) which counts all rows
2. For counting unique themes, ALWAYS use COUNT(DISTINCT base_theme) or COUNT(DISTINCT sub_theme)
3. Examples:
   - "How many base themes?" → SELECT COUNT(DISTINCT base_theme) AS base_theme_count FROM cb WHERE base_theme NOT IN ('others', 'stock_market')
   - "How many sub themes?" → SELECT COUNT(DISTINCT sub_theme) AS sub_theme_count FROM cb WHERE base_theme NOT IN ('others', 'stock_market') AND sub_theme != 'others'
   - "How many base themes and sub themes?" → SELECT COUNT(DISTINCT base_theme) AS base_theme_count, COUNT(DISTINCT sub_theme) AS sub_theme_count FROM cb WHERE base_theme NOT IN ('others', 'stock_market') AND sub_theme != 'others'
   - "List all base themes" → SELECT DISTINCT base_theme FROM cb WHERE base_theme NOT IN ('others', 'stock_market') ORDER BY base_theme
   - "List all sub themes" → SELECT DISTINCT sub_theme FROM cb WHERE base_theme NOT IN ('others', 'stock_market') AND sub_theme != 'others' ORDER BY sub_theme
4. Remember: COUNT(*) counts all rows, COUNT(DISTINCT column) counts unique values in that column
5. When counting, always apply the exclusion filters: base_theme NOT IN ('others', 'stock_market') AND sub_theme != 'others'

Your task:
1. Understand the user's request in natural language
2. **Use conversation history to understand context**: If the user refers to "previous results", "last query", "above", "those themes", "that data", etc., look at the conversation history to understand what they're referring to
3. Map natural language theme names to database values using the mapping guide above
4. Generate a valid PostgreSQL SELECT query that answers their question
5. Always exclude 'others' and 'stock_market' from base_theme
6. Always exclude 'others' from sub_theme
7. Use appropriate date filtering when needed
8. If the user asks follow-up questions about previous queries, incorporate relevant filters or conditions from previous queries
9. Return ONLY the SQL query, no explanations unless asked

Format your response as:
```sql
SELECT ... FROM cb WHERE ...
```

CRITICAL SQL Syntax Rules:
1. **Always use single quotes (') for string literals, NEVER double quotes (")**
2. **Ensure all single quotes are properly closed** - every opening quote must have a closing quote
3. **For string values, use single quotes**: WHERE base_theme = 'inclusion_safety' (correct)
4. **For string values, NEVER use**: WHERE base_theme = "inclusion_safety" (wrong)
5. **When using IN clause with strings, use single quotes**: WHERE base_theme IN ('others', 'stock_market')
6. **When using NOT IN, ensure proper quote closure**: WHERE base_theme NOT IN ('others', 'stock_market')
7. **For pattern matching with ILIKE/LIKE, use single quotes**: WHERE sub_theme ILIKE '%inclusion%'
8. **Always wrap your SQL in ```sql code blocks** for proper extraction
9. **Do NOT include trailing semicolons** - they will be removed automatically
10. **Test your SQL mentally**: count opening and closing single quotes - they must match

Important: 
- Only generate SELECT queries (read-only)
- Use proper WHERE clauses to filter data
- Use ILIKE or pattern matching for theme names when exact match is uncertain
- Include appropriate aggregations (COUNT, SUM, AVG, etc.) when needed
- **For counting unique values, ALWAYS use COUNT(DISTINCT column), NOT COUNT(*)**
- Group by relevant columns when aggregating
- Order results meaningfully
- **Double-check quote balance before returning SQL**
"""
        
        user_prompt = f"""User request: {message}

Generate a SQL query to answer this request. 

CRITICAL: SQL Syntax Requirements:
- **Use SINGLE quotes (') for ALL string literals** - Example: WHERE base_theme = 'inclusion_safety'
- **NEVER use double quotes (") for string values** - they are for identifiers, not values
- **Ensure ALL single quotes are properly closed** - count them to verify balance
- **For IN clauses**: base_theme NOT IN ('others', 'stock_market') - note the single quotes
- **For equality checks**: sub_theme = 'others' - note the single quotes
- **Wrap your SQL in ```sql code blocks** for proper formatting

Query Requirements:
- Map any theme names mentioned by the user to the exact database values from the mapping guide
- Use case-insensitive pattern matching (ILIKE or LOWER/REPLACE) if the exact format is unclear
- Remember to exclude base_theme IN ('others', 'stock_market') and sub_theme = 'others'
- **IMPORTANT**: If the user asks about "how many", "count", "number of", or similar counting questions:
  * Use COUNT(DISTINCT column) to count UNIQUE values, NOT COUNT(*) which counts all rows
  * For themes: COUNT(DISTINCT base_theme) or COUNT(DISTINCT sub_theme)
  * Always apply exclusion filters when counting
- If the user refers to previous queries or mentions "previous results", "last query", "above", etc., use context from the conversation history below to understand what they're referring to.

Before returning, verify:
1. All string literals use single quotes (')
2. All single quotes are properly closed (even number of quotes)
3. SQL is wrapped in ```sql code blocks"""
        
        # Build messages array with conversation history for context
        messages_array = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 5 messages) for context
        # Filter and format conversation history to OpenAI format
        try:
            if conversation_history and isinstance(conversation_history, list):
                for hist_msg in conversation_history[-5:]:  # Keep last 5 messages
                    if not isinstance(hist_msg, dict):
                        continue
                    role = hist_msg.get('role', 'user')
                    content = hist_msg.get('content', '')
                    # Skip empty messages and error messages
                    if content and role in ['user', 'assistant'] and not hist_msg.get('error'):
                        # For assistant messages, limit length to avoid token overflow
                        # Keep key information like SQL queries and summaries
                        if role == 'assistant':
                            # Extract important parts: SQL queries and brief summaries
                            # Limit to 800 chars to keep context manageable
                            if len(content) > 800:
                                # Try to keep SQL queries if present
                                sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL)
                                if sql_match:
                                    content = f"[Previous query result summary] {content[:300]}... [SQL: {sql_match.group(1)[:200]}]"
                                else:
                                    content = content[:800] + "..."
                        
                        messages_array.append({
                            "role": role,
                            "content": str(content)  # Ensure content is a string
                        })
        except Exception as e:
            print(f"Error processing conversation history: {e}")
            import traceback
            print(traceback.format_exc())
            # Continue without history if there's an error
        
        # Add current user message
        messages_array.append({"role": "user", "content": user_prompt})
        
        # Call OpenAI with conversation history
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages_array,
            temperature=0.3,
            max_tokens=1000
        )
        
        ai_response_text = response.choices[0].message.content
        
        # Extract SQL from response
        sql_query = extract_sql_from_response(ai_response_text)
        
        if not sql_query:
            # Try to provide helpful debugging info
            debug_info = ""
            if '```sql' in ai_response_text or '```' in ai_response_text:
                debug_info = "\n\n💡 Debug: Found code blocks in response, but SQL extraction failed. This might be due to:\n- Incomplete code block formatting\n- Unbalanced quotes in the SQL\n- Special characters interfering with parsing"
            elif 'SELECT' in ai_response_text.upper():
                debug_info = "\n\n💡 Debug: Found SELECT statement but not in proper code blocks. Please wrap SQL in ```sql code blocks."
            
            return jsonify({
                'response': ai_response_text + '\n\n⚠️ Could not extract SQL query from response.' + debug_info + '\n\nPlease ensure the SQL is properly formatted in ```sql code blocks.',
                'error': 'No SQL query found in AI response',
                'debug': {
                    'has_code_blocks': '```' in ai_response_text,
                    'has_select': 'SELECT' in ai_response_text.upper(),
                    'response_length': len(ai_response_text)
                }
            }), 200
        
        # Clean SQL query again to ensure it's properly formatted
        sql_query = clean_sql_query(sql_query)
        if not sql_query:
            return jsonify({
                'response': f"❌ SQL syntax error: Unbalanced quotes or invalid query format.\n\nAI generated:\n```sql\n{extract_sql_from_response(ai_response_text) or 'Unable to extract'}\n```\n\nPlease try rephrasing your question.",
                'error': 'SQL syntax error: unbalanced quotes'
            }), 400
        
        # Validate SQL
        is_valid, error_msg = validate_sql(sql_query)
        if not is_valid:
            return jsonify({
                'response': f"❌ SQL validation failed: {error_msg}\n\nAI generated:\n```sql\n{sql_query}\n```\n\nPlease try rephrasing your question.",
                'error': error_msg
            }), 400
        
        # Execute SQL via Supabase
        try:
            query_results = execute_sql_via_supabase(sql_query)
            
            # Use AI to analyze the results and generate comprehensive analysis
            ai_analysis_result = generate_ai_analysis(message, query_results, sql_query, client)
            
            # Return the complete AI analysis as the response
            # The AI will provide a comprehensive analysis including insights, recommendations, etc.
            formatted_response = ai_analysis_result.get('full_analysis', ai_analysis_result.get('summary', ''))
            
            # Simple visualization config for backward compatibility
            visualization_config = {
                'view_type': 'custom_query',
                'query_type': 'custom',
                'auto_select_first': False
            }
            
            # Minimal analysis data for backward compatibility
            # Include more results for reference (up to 100 rows instead of 10)
            analysis_data = {
                'period': {'start': None, 'end': None},
                'topics': [],
                'raw_results': query_results[:100] if len(query_results) > 100 else query_results,  # Include up to 100 rows for reference
                'total_results': len(query_results),  # Include total count
                'sql_query': sql_query
            }
            
            return jsonify({
                'response': formatted_response,
                'analysis_data': analysis_data,
                'visualization_config': visualization_config,
                'sql_query': sql_query
            }), 200
            
        except (psycopg2.Error, ValueError, Exception) as e:
            # If SQL execution fails (e.g., missing function), still return the SQL query
            error_msg = str(e)
            formatted_response = f"{ai_response_text}\n\n⚠️ SQL execution not available: {error_msg}\n\nGenerated SQL:\n```sql\n{sql_query}\n```\n\n💡 To execute SQL queries, please:\n1. Run the SQL in CREATE_SQL_FUNCTION.sql in Supabase SQL Editor\n2. Or configure SUPABASE_SERVICE_ROLE_KEY for enhanced permissions"
            
            return jsonify({
                'response': formatted_response,
                'error': error_msg,
                'sql_query': sql_query,
                'analysis_data': {
                    'period': {'start': None, 'end': None},
                    'topics': [],
                    'raw_results': [],
                    'sql_query': sql_query
                },
                'visualization_config': {
                    'view_type': 'custom_query',
                    'query_type': 'custom',
                    'auto_select_first': False
                }
            }), 200  # Return 200 but with error info
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in chat endpoint: {error_trace}")  # Print to console for debugging
        return jsonify({
            'response': f"❌ Error processing request: {str(e)}\n\nPlease check the backend logs for more details.",
            'error': str(e),
            'traceback': error_trace if hasattr(Config, 'FLASK_ENV') and Config.FLASK_ENV == 'development' else None
        }), 500
