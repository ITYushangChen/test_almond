from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from supabase_client import get_supabase
from datetime import datetime
from routes.ai_analysis import get_openai_client
from config import Config
import json

dashboard_bp = Blueprint('dashboard', __name__)

def apply_filters(query, filters):
    """Apply common filters to Supabase query"""
    # Default filter: exclude base_theme and sub_theme that are 'others' and 'stock_market'
    query = query.not_.in_('base_theme', ['others', 'stock_market'])
    query = query.not_.in_('sub_theme', ['others', 'stock_market'])
    
    if filters.get('base_themes'):
        query = query.in_('base_theme', filters['base_themes'])
    
    if filters.get('sub_themes'):
        query = query.in_('sub_theme', filters['sub_themes'])
    
    if filters.get('languages'):
        query = query.in_('language', filters['languages'])
    
    if filters.get('sources'):
        query = query.in_('source', filters['sources'])
    
    if filters.get('start_date'):
        query = query.gte('date', filters['start_date'])
    
    if filters.get('end_date'):
        query = query.lte('date', filters['end_date'])
    
    return query

@dashboard_bp.route('/kpis', methods=['POST'])
def get_kpis():
    filters = request.get_json() or {}
    supabase = get_supabase()
    
    # Base query - get all data from cb table
    query = supabase.table('cb').select('sentiment,base_theme,likes')
    query = apply_filters(query, filters)
    
    response = query.execute()
    data = response.data
    
    # Calculate KPIs
    total_comments = len(data)
    
    # Use sentiment if available for each item, otherwise use likes as proxy
    positive_comments = 0
    negative_comments = 0
    
    for d in data:
        sentiment = d.get('sentiment')
        if sentiment == 'positive':
            positive_comments += 1
        elif sentiment == 'negative':
            negative_comments += 1
        else:
            # Fallback to likes-based calculation when sentiment is null
            likes = d.get('likes', 0)
            if likes > 5:
                positive_comments += 1
            elif likes < -5:
                negative_comments += 1
    
    # Theme distribution
    theme_counts = {}
    for d in data:
        theme = d.get('base_theme', 'unknown')
        theme_counts[theme] = theme_counts.get(theme, 0) + 1
    
    # eNPS calculation: positive comments / total comments * 100
    enps = (positive_comments / total_comments * 100) if total_comments > 0 else 0
    
    return jsonify({
        'total_comments': total_comments,
        'positive_comments': positive_comments,
        'negative_comments': negative_comments,
        'enps': round(enps, 2),
        'theme_distribution': theme_counts
    }), 200

@dashboard_bp.route('/filters/options', methods=['GET'])
def get_filter_options():
    """Get available filter options"""
    supabase = get_supabase()
    
    # Get unique values from cb table, excluding 'others' and 'stock_market'
    response = supabase.table('cb').select('base_theme,sub_theme,language,source,date').execute()
    data = response.data
    
    # Get actual date range from database
    dates = [d.get('date') for d in data if d.get('date')]
    min_date = None
    max_date = None
    if dates:
        dates_only = [d for d in dates if d]  # Filter out None values
        if dates_only:
            min_date = min(dates_only)
            max_date = max(dates_only)
    
    # Exclusion list
    exclude_values = ['others', 'stock_market']
    
    # Extract unique values and filter out excluded ones
    base_themes = list(set(
        d.get('base_theme') for d in data 
        if d.get('base_theme') and d.get('base_theme') not in exclude_values
    ))
    
    # Build mapping of base_theme to sub_themes
    theme_mapping = {}
    for d in data:
        base_theme = d.get('base_theme')
        sub_theme = d.get('sub_theme')
        if base_theme and base_theme not in exclude_values and sub_theme and sub_theme not in exclude_values:
            if base_theme not in theme_mapping:
                theme_mapping[base_theme] = set()
            theme_mapping[base_theme].add(sub_theme)
    
    # Convert sets to sorted lists
    theme_mapping_sorted = {
        theme: sorted(list(sub_themes)) 
        for theme, sub_themes in theme_mapping.items()
    }
    
    # All sub_themes (for backward compatibility)
    all_sub_themes = list(set(
        d.get('sub_theme') for d in data 
        if d.get('sub_theme') and d.get('sub_theme') not in exclude_values
    ))
    
    # Count language frequencies and sort by frequency (descending)
    language_counts = {}
    for d in data:
        lang = d.get('language')
        if lang:
            language_counts[lang] = language_counts.get(lang, 0) + 1
    
    # Sort languages by frequency (descending), then alphabetically for ties
    languages = sorted(
        language_counts.keys(),
        key=lambda x: (-language_counts[x], x)
    )
    
    # Extract unique source values
    sources = sorted(set(
        d.get('source') for d in data 
        if d.get('source')
    ))
    
    # Prepare date range info
    date_range = None
    if min_date and max_date:
        # Parse dates to extract year-month
        try:
            from datetime import datetime
            
            # Helper function to parse date
            def parse_date(date_val):
                if isinstance(date_val, datetime):
                    return date_val
                elif isinstance(date_val, str):
                    # Try different date formats
                    date_str = date_val.replace('Z', '+00:00').split('T')[0]  # Get date part only
                    try:
                        return datetime.strptime(date_str, '%Y-%m-%d')
                    except:
                        try:
                            return datetime.fromisoformat(date_str)
                        except:
                            # Fallback: try to extract year-month from string
                            parts = date_str.split('-')
                            if len(parts) >= 2:
                                return datetime(int(parts[0]), int(parts[1]), 1)
                return None
            
            min_dt = parse_date(min_date)
            max_dt = parse_date(max_date)
            
            if min_dt and max_dt:
                date_range = {
                    'min_date': min_dt.strftime('%Y-%m-%d'),
                    'max_date': max_dt.strftime('%Y-%m-%d'),
                    'min_year': min_dt.year,
                    'min_month': min_dt.month,
                    'max_year': max_dt.year,
                    'max_month': max_dt.month
                }
        except Exception as e:
            import traceback
            print(f"Error parsing date range: {e}")
            print(traceback.format_exc())
            date_range = None
    
    return jsonify({
        'base_themes': sorted(base_themes),
        'sub_themes': sorted(all_sub_themes),
        'theme_mapping': theme_mapping_sorted,  # New: mapping of base_theme to sub_themes
        'languages': languages,
        'sources': sources,
        'date_range': date_range  # New: actual date range from database
    }), 200

@dashboard_bp.route('/ai-insights', methods=['POST'])
def generate_dashboard_insights():
    """Generate AI insights based on filtered dashboard data"""
    filters = request.get_json() or {}
    
    # Check OpenAI API key
    if not Config.OPENAI_API_KEY:
        return jsonify({
            'insights': [],
            'error': 'OpenAI API key not configured'
        }), 200  # Return empty insights instead of error
    
    try:
        supabase = get_supabase()
        
        # Get filtered data for analysis
        query = supabase.table('cb').select('base_theme,sub_theme,sentiment,likes,date,language,content')
        query = apply_filters(query, filters)
        query = query.limit(3000)  # Limit to 3000 rows for analysis
        response = query.execute()
        data = response.data
        
        if not data or len(data) == 0:
            return jsonify({
                'insights': [],
                'message': 'No data available for the selected filters'
            }), 200
        
        # Prepare data summary for AI
        total_comments = len(data)
        
        # Calculate sentiment distribution
        positive_count = sum(1 for d in data if d.get('sentiment') == 'positive' or (not d.get('sentiment') and d.get('likes', 0) > 0))
        negative_count = sum(1 for d in data if d.get('sentiment') == 'negative' or (not d.get('sentiment') and d.get('likes', 0) < 0))
        neutral_count = total_comments - positive_count - negative_count
        
        # Calculate theme distribution
        theme_counts = {}
        theme_sentiment = {}
        for d in data:
            theme = d.get('base_theme', 'unknown')
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
            if theme not in theme_sentiment:
                theme_sentiment[theme] = {'positive': 0, 'negative': 0, 'neutral': 0}
            sentiment = d.get('sentiment')
            if sentiment == 'positive' or (not sentiment and d.get('likes', 0) > 0):
                theme_sentiment[theme]['positive'] += 1
            elif sentiment == 'negative' or (not sentiment and d.get('likes', 0) < 0):
                theme_sentiment[theme]['negative'] += 1
            else:
                theme_sentiment[theme]['neutral'] += 1
        
        # Get top themes by count
        top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Prepare data summary
        data_summary = {
            'total_comments': total_comments,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_rate': round((positive_count / total_comments * 100) if total_comments > 0 else 0, 2),
            'negative_rate': round((negative_count / total_comments * 100) if total_comments > 0 else 0, 2),
            'top_themes': [
                {
                    'theme': theme,
                    'count': count,
                    'positive': theme_sentiment[theme]['positive'],
                    'negative': theme_sentiment[theme]['negative'],
                    'positive_rate': round((theme_sentiment[theme]['positive'] / count * 100) if count > 0 else 0, 2),
                    'negative_rate': round((theme_sentiment[theme]['negative'] / count * 100) if count > 0 else 0, 2)
                }
                for theme, count in top_themes
            ],
            'date_range': {
                'start': filters.get('start_date', 'N/A'),
                'end': filters.get('end_date', 'N/A')
            },
            'filters_applied': {
                'base_themes': filters.get('base_themes', []),
                'sub_themes': filters.get('sub_themes', []),
                'languages': filters.get('languages', [])
            }
        }
        
        # Sample content for context (limit to 20)
        sample_content = [d.get('content', '')[:200] for d in data[:20] if d.get('content')]
        
        # Generate AI insights
        client = get_openai_client()
        
        # Use English for insights (Chinese support removed)
        insight_prompt = f"""You are a professional corporate culture data analyst. Generate specific, actionable insights based on the following filtered data.

Data Overview:
- Total Comments: {data_summary['total_comments']}
- Positive Comments: {data_summary['positive_count']} ({data_summary['positive_rate']}%)
- Negative Comments: {data_summary['negative_count']} ({data_summary['negative_rate']}%)
- Neutral Comments: {data_summary['neutral_count']}

Date Range: {data_summary['date_range']['start']} to {data_summary['date_range']['end']}

Filters Applied:
- Base Themes: {', '.join(data_summary['filters_applied']['base_themes']) if data_summary['filters_applied']['base_themes'] else 'All'}
- Sub Themes: {', '.join(data_summary['filters_applied']['sub_themes']) if data_summary['filters_applied']['sub_themes'] else 'All'}
- Languages: {', '.join(data_summary['filters_applied']['languages']) if data_summary['filters_applied']['languages'] else 'All'}

Top 10 Themes Statistics:
{json.dumps([{'Theme': t['theme'], 'Comments': t['count'], 'Positive Rate': f"{t['positive_rate']}%", 'Negative Rate': f"{t['negative_rate']}%"} for t in data_summary['top_themes']], indent=2)}

Sample Content (first 10):
{json.dumps(sample_content[:10], indent=2)}

Generate 3-5 specific, data-driven insights. Each insight should:
1. Clearly identify a finding, trend, or issue
2. Reference specific data (numbers, percentages)
3. Explain why this finding matters
4. Provide actionable recommendations

Format Requirements:
- Use clear English
- Each insight in a separate paragraph
- Use emojis for readability
- Support claims with specific numbers

Return insights directly, not in JSON format."""
        
        try:
            system_prompt = "You are a professional data analyst specializing in corporate culture and employee sentiment analysis. You provide clear, specific, data-driven insights."
            
            ai_response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": insight_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            insights_text = ai_response.choices[0].message.content
            
            # Parse insights into structured format
            # Split by paragraphs and format
            insights_list = []
            paragraphs = insights_text.split('\n\n')
            
            for para in paragraphs:
                para = para.strip()
                if para and len(para) > 20:  # Filter out very short paragraphs
                    # Extract title and content
                    lines = para.split('\n', 1)
                    if len(lines) > 1:
                        title = lines[0].strip()
                        content = lines[1].strip()
                    else:
                        # Use first sentence as title
                        sentences = para.split('.')
                        title = sentences[0].strip() if sentences else para[:50]
                        content = para
                    
                    insights_list.append({
                        'title': title,
                        'content': content,
                        'importance': 'medium'  # Can be enhanced with AI classification
                    })
            
            # Limit to 5 insights
            insights_list = insights_list[:5]
            
            return jsonify({
                'insights': insights_list,
                'data_summary': data_summary,
                'generated_at': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            import traceback
            print(f"Error generating AI insights: {traceback.format_exc()}")
            # Return empty insights on error
            return jsonify({
                'insights': [],
                'error': str(e)
            }), 200
        
    except Exception as e:
        import traceback
        print(f"Error in generate_dashboard_insights: {traceback.format_exc()}")
        return jsonify({
            'insights': [],
            'error': str(e)
        }), 200
