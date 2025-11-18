from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from supabase_client import get_supabase
from datetime import datetime
from collections import defaultdict
from routes.dashboard import apply_filters
from routes.ai_analysis import get_openai_client
from config import Config
import json

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/monthly-comments', methods=['POST'])
def get_monthly_comments():
    filters = request.get_json() or {}
    supabase = get_supabase()
    
    query = supabase.table('cb').select('date')
    query = apply_filters(query, filters)
    response = query.execute()
    
    # Group by month
    monthly_counts = defaultdict(int)
    for item in response.data:
        if item.get('date'):
            month = item['date'][:7]  # YYYY-MM
            monthly_counts[month] += 1
    
    data = [{'month': month, 'count': count} 
            for month, count in sorted(monthly_counts.items())]
    
    return jsonify(data), 200

@analysis_bp.route('/monthly-enps', methods=['POST'])
def get_monthly_enps():
    filters = request.get_json() or {}
    supabase = get_supabase()
    
    # Get data from cb table
    query = supabase.table('cb').select('date,likes,sentiment')
    query = apply_filters(query, filters)
    response = query.execute()
    
    # Group by month
    monthly_data = defaultdict(lambda: {'total': 0, 'positive': 0})
    for item in response.data:
        if item.get('date'):
            month = item['date'][:7]
            monthly_data[month]['total'] += 1
            
            # Check sentiment for this specific item
            sentiment = item.get('sentiment')
            if sentiment == 'positive':
                # Use actual sentiment if available
                monthly_data[month]['positive'] += 1
            else:
                # Fallback to likes-based (likes > 5 as positive proxy)
                likes = item.get('likes', 0)
                if likes > 5:
                    monthly_data[month]['positive'] += 1
    
    data = []
    for month in sorted(monthly_data.keys()):
        stats = monthly_data[month]
        # eNPS calculation: positive / total * 100
        enps = (stats['positive'] / stats['total'] * 100) if stats['total'] > 0 else 0
        data.append({
            'month': month,
            'enps': round(enps, 2),
            'total': stats['total'],
            'positive': stats['positive']
        })
    
    return jsonify(data), 200

@analysis_bp.route('/topic-hotness', methods=['POST'])
def get_topic_hotness():
    filters = request.get_json() or {}
    supabase = get_supabase()
    
    # Get data from cb table
    query = supabase.table('cb').select('base_theme,likes,sentiment')
    query = apply_filters(query, filters)
    response = query.execute()
    data_items = response.data
    
    # Calculate hotness by theme
    theme_data = defaultdict(lambda: {
        'hotness': 0,
        'total': 0,
        'positive': 0
    })
    
    for item in data_items:
        theme = item.get('base_theme')
        if not theme:
            continue
        
        # Calculate hotness based on likes
        likes = item.get('likes', 0)
        theme_data[theme]['hotness'] += likes
        theme_data[theme]['total'] += 1
        
        # Count positive comments - check sentiment for this specific item
        sentiment = item.get('sentiment')
        if sentiment == 'positive':
            # Use actual sentiment if available
            theme_data[theme]['positive'] += 1
        else:
            # Fallback to likes-based (likes > 5 as positive proxy)
            if likes > 5:
                theme_data[theme]['positive'] += 1
    
    data = []
    for theme, stats in theme_data.items():
        # eNPS calculation: positive / total * 100
        enps_now = (stats['positive'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        data.append({
            'base_theme': theme,
            'hotness_score': stats['hotness'],
            'enps_now': round(enps_now, 2),
            'total_comments': stats['total']  # Total number of comments/rows
        })
    
    data.sort(key=lambda x: x['hotness_score'], reverse=True)
    return jsonify(data), 200

@analysis_bp.route('/sub-theme-hotness', methods=['POST'])
def get_sub_theme_hotness():
    """Get hotness statistics for sub_themes under a specific base_theme"""
    data = request.get_json() or {}
    base_theme = data.get('base_theme')
    filters = data.get('filters', {})
    
    if not base_theme:
        return jsonify({'error': 'base_theme is required'}), 400
    
    supabase = get_supabase()
    
    # Get data from cb table, filtered by base_theme and other filters
    query = supabase.table('cb').select('sub_theme,likes,sentiment')
    query = apply_filters(query, filters)
    query = query.eq('base_theme', base_theme)
    response = query.execute()
    data_items = response.data
    
    # Calculate hotness by sub_theme
    sub_theme_data = defaultdict(lambda: {
        'hotness': 0,
        'total': 0,
        'positive': 0
    })
    
    for item in data_items:
        sub_theme = item.get('sub_theme')
        if not sub_theme:
            continue
        
        # Calculate hotness based on likes
        likes = item.get('likes', 0)
        sub_theme_data[sub_theme]['hotness'] += likes
        sub_theme_data[sub_theme]['total'] += 1
        
        # Count positive comments - check sentiment for this specific item
        sentiment = item.get('sentiment')
        if sentiment == 'positive':
            # Use actual sentiment if available
            sub_theme_data[sub_theme]['positive'] += 1
        else:
            # Fallback to likes-based (likes > 5 as positive proxy)
            if likes > 5:
                sub_theme_data[sub_theme]['positive'] += 1
    
    result = []
    for sub_theme, stats in sub_theme_data.items():
        # eNPS calculation: positive / total * 100
        enps_now = (stats['positive'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        result.append({
            'sub_theme': sub_theme,
            'hotness_score': stats['hotness'],
            'enps_now': round(enps_now, 2),
            'total_comments': stats['total']
        })
    
    result.sort(key=lambda x: x['hotness_score'], reverse=True)
    return jsonify(result), 200

@analysis_bp.route('/risky-themes', methods=['GET'])
def get_risky_themes():
    """Get risky sub_themes for 2025 data with risk ratings and YoY comparison"""
    supabase = get_supabase()
    
    def get_year_data(year):
        """Get data for a specific year"""
        start_date = f'{year}-01-01'
        end_date = f'{int(year) + 1}-01-01'
        
        query = supabase.table('cb').select('sub_theme,base_theme,likes,sentiment,date')
        query = query.gte('date', start_date)
        query = query.lt('date', end_date)
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        query = query.limit(100000)
        response = query.execute()
        
        # Filter out null sub_themes in Python (Supabase may not handle null filtering well)
        return [item for item in response.data if item.get('sub_theme')]
    
    # Get 2025 and 2024 data
    data_2025 = get_year_data('2025')
    data_2024 = get_year_data('2024')
    
    total_responses = len(data_2025)
    
    def calculate_theme_stats(data_items):
        """Calculate statistics for each sub_theme separately"""
        theme_stats = defaultdict(lambda: {
            'count': 0,
            'positive': 0,
            'negative': 0,
            'neutral': 0
        })
        
        for item in data_items:
            # Get sub_theme - must be a non-empty string
            sub_theme = item.get('sub_theme')
            if not sub_theme or not isinstance(sub_theme, str) or sub_theme.strip() == '':
                continue
            
            # Normalize sub_theme (strip whitespace)
            sub_theme = sub_theme.strip()
            
            # Count total comments for this sub_theme
            theme_stats[sub_theme]['count'] += 1
            
            likes = item.get('likes', 0) or 0
            sentiment = item.get('sentiment')
            
            # Determine sentiment for THIS specific comment/item
            # Priority: actual sentiment field > likes-based proxy
            if sentiment == 'positive':
                # Use actual positive sentiment
                theme_stats[sub_theme]['positive'] += 1
            elif sentiment == 'negative':
                # Use actual negative sentiment
                theme_stats[sub_theme]['negative'] += 1
            elif sentiment:
                # Other sentiment values (neutral, etc.)
                theme_stats[sub_theme]['neutral'] += 1
            else:
                # Fallback to likes-based proxy when sentiment is null
                # Lower threshold: likes > 0 for positive, likes < 0 for negative
                if likes > 0:
                    theme_stats[sub_theme]['positive'] += 1
                elif likes < 0:
                    theme_stats[sub_theme]['negative'] += 1
                else:
                    theme_stats[sub_theme]['neutral'] += 1
        
        return theme_stats
    
    # Calculate statistics for each sub_theme separately for 2025 and 2024
    stats_2025 = calculate_theme_stats(data_2025)
    stats_2024 = calculate_theme_stats(data_2024)
    
    # Calculate risk scores and YoY changes for EACH sub_theme individually
    risky_themes = []
    for sub_theme, stats_2025_data in stats_2025.items():
        total_2025 = stats_2025_data['count']
        # Filter: Only include sub_themes with at least 5 comments in 2025
        if total_2025 < 5:
            continue
        
        # Calculate stats for THIS specific sub_theme in 2025
        negative_rate_2025 = (stats_2025_data['negative'] / total_2025 * 100) if total_2025 > 0 else 0
        positive_count_2025 = stats_2025_data['positive']
        positive_rate_2025 = (positive_count_2025 / total_2025 * 100) if total_2025 > 0 else 0
        
        # Calculate eNPS for THIS specific sub_theme in 2025: (positive / total) * 100
        # This is calculated separately for each sub_theme
        enps_2025 = (positive_count_2025 / total_2025 * 100) if total_2025 > 0 else 0
        
        # Risk score calculation (0-100 scale)
        volume_factor = min(total_2025 / 50, 1.0)
        risk_score = (negative_rate_2025 * 0.7) + (volume_factor * 30 * 0.3)
        risk_score = min(max(risk_score, 0), 100)
        
        # 2024 stats for THIS specific sub_theme for comparison
        stats_2024_data = stats_2024.get(sub_theme, {'count': 0, 'positive': 0, 'negative': 0, 'neutral': 0})
        total_2024 = stats_2024_data['count']
        positive_count_2024 = stats_2024_data['positive']
        
        # Calculate eNPS for THIS specific sub_theme in 2024: (positive / total) * 100
        enps_2024 = (positive_count_2024 / total_2024 * 100) if total_2024 > 0 else 0
        
        # Calculate YoY changes
        if total_2024 > 0:
            comments_yoy_change = ((total_2025 - total_2024) / total_2024 * 100)
        else:
            comments_yoy_change = 100 if total_2025 > 0 else 0  # New theme in 2025
        
        # Calculate eNPS YoY change
        if enps_2024 > 0:
            enps_yoy_change = ((enps_2025 - enps_2024) / enps_2024 * 100)
        elif enps_2025 > 0:
            enps_yoy_change = 100  # New positive sentiment in 2025
        else:
            enps_yoy_change = 0  # Both are 0
        
        risky_themes.append({
            'sub_theme': sub_theme,
            'risk_score': round(risk_score, 1),
            'total_count': total_2025,
            'total_count_2024': total_2024,
            'comments_yoy_change': round(comments_yoy_change, 1),
            'enps': round(enps_2025, 1),
            'enps_2024': round(enps_2024, 1),
            'enps_yoy_change': round(enps_yoy_change, 1),
            'negative_rate': round(negative_rate_2025, 1),
            'positive_rate': round(positive_rate_2025, 1)
        })
    
    # Sort by risk score (highest first)
    risky_themes.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Calculate overall risk rating
    top_10_avg_risk = sum(t['risk_score'] for t in risky_themes[:10]) / min(len(risky_themes), 10) if risky_themes else 0
    overall_risk_rating = round(top_10_avg_risk, 1)
    
    # Determine risk level
    if overall_risk_rating >= 50:
        risk_level = 'Very High'
    elif overall_risk_rating >= 40:
        risk_level = 'High'
    elif overall_risk_rating >= 35:
        risk_level = 'Moderate-High'
    elif overall_risk_rating >= 25:
        risk_level = 'Moderate'
    elif overall_risk_rating >= 20:
        risk_level = 'Low-Moderate'
    elif overall_risk_rating >= 5:
        risk_level = 'Low'
    else:
        risk_level = 'Very Low'
    
    return jsonify({
        'total_responses': total_responses,
        'overall_risk_rating': overall_risk_rating,
        'risk_level': risk_level,
        'risky_themes': risky_themes[:10]  # Top 10 only
    }), 200

@analysis_bp.route('/positive-themes', methods=['GET'])
def get_positive_themes():
    """Get top 10 positive sub_themes with positive ratings and YoY comparison"""
    supabase = get_supabase()
    
    def get_year_data(year):
        """Get data for a specific year"""
        start_date = f'{year}-01-01'
        end_date = f'{int(year) + 1}-01-01'
        
        query = supabase.table('cb').select('sub_theme,base_theme,likes,sentiment,date')
        query = query.gte('date', start_date)
        query = query.lt('date', end_date)
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        query = query.limit(100000)
        response = query.execute()
        
        # Filter out null sub_themes
        return [item for item in response.data if item.get('sub_theme')]
    
    # Get 2025 and 2024 data
    data_2025 = get_year_data('2025')
    data_2024 = get_year_data('2024')
    
    total_responses = len(data_2025)
    
    def calculate_theme_stats(data_items):
        """Calculate statistics for each sub_theme separately"""
        theme_stats = defaultdict(lambda: {
            'count': 0,
            'positive': 0,
            'negative': 0,
            'neutral': 0
        })
        
        for item in data_items:
            sub_theme = item.get('sub_theme')
            if not sub_theme or not isinstance(sub_theme, str) or sub_theme.strip() == '':
                continue
            
            sub_theme = sub_theme.strip()
            theme_stats[sub_theme]['count'] += 1
            
            likes = item.get('likes', 0) or 0
            sentiment = item.get('sentiment')
            
            if sentiment == 'positive':
                theme_stats[sub_theme]['positive'] += 1
            elif sentiment == 'negative':
                theme_stats[sub_theme]['negative'] += 1
            elif sentiment:
                theme_stats[sub_theme]['neutral'] += 1
            else:
                # Fallback to likes-based proxy
                if likes > 0:
                    theme_stats[sub_theme]['positive'] += 1
                elif likes < 0:
                    theme_stats[sub_theme]['negative'] += 1
                else:
                    theme_stats[sub_theme]['neutral'] += 1
        
        return theme_stats
    
    stats_2025 = calculate_theme_stats(data_2025)
    stats_2024 = calculate_theme_stats(data_2024)
    
    # Calculate positive scores and YoY changes
    positive_themes = []
    for sub_theme, stats_2025_data in stats_2025.items():
        total_2025 = stats_2025_data['count']
        # Filter: Only include sub_themes with at least 5 comments in 2025
        if total_2025 < 5:
            continue
        
        positive_count_2025 = stats_2025_data['positive']
        positive_rate_2025 = (positive_count_2025 / total_2025 * 100) if total_2025 > 0 else 0
        negative_rate_2025 = (stats_2025_data['negative'] / total_2025 * 100) if total_2025 > 0 else 0
        
        # Calculate eNPS for this sub_theme in 2025
        enps_2025 = (positive_count_2025 / total_2025 * 100) if total_2025 > 0 else 0
        
        # Positive score calculation (0-100 scale, inverse of risk score)
        # Higher positive rate and engagement = higher positive score
        volume_factor = min(total_2025 / 50, 1.0)
        positive_score = (positive_rate_2025 * 0.7) + (volume_factor * 30 * 0.3)
        positive_score = min(max(positive_score, 0), 100)
        
        # 2024 stats for comparison
        stats_2024_data = stats_2024.get(sub_theme, {'count': 0, 'positive': 0, 'negative': 0, 'neutral': 0})
        total_2024 = stats_2024_data['count']
        positive_count_2024 = stats_2024_data['positive']
        
        enps_2024 = (positive_count_2024 / total_2024 * 100) if total_2024 > 0 else 0
        
        # Calculate YoY changes
        if total_2024 > 0:
            comments_yoy_change = ((total_2025 - total_2024) / total_2024 * 100)
        else:
            comments_yoy_change = 100 if total_2025 > 0 else 0
        
        if enps_2024 > 0:
            enps_yoy_change = ((enps_2025 - enps_2024) / enps_2024 * 100)
        elif enps_2025 > 0:
            enps_yoy_change = 100
        else:
            enps_yoy_change = 0
        
        positive_themes.append({
            'sub_theme': sub_theme,
            'positive_score': round(positive_score, 1),
            'total_count': total_2025,
            'total_count_2024': total_2024,
            'comments_yoy_change': round(comments_yoy_change, 1),
            'enps': round(enps_2025, 1),
            'enps_2024': round(enps_2024, 1),
            'enps_yoy_change': round(enps_yoy_change, 1),
            'positive_rate': round(positive_rate_2025, 1),
            'negative_rate': round(negative_rate_2025, 1)
        })
    
    # Sort by positive score (highest first)
    positive_themes.sort(key=lambda x: x['positive_score'], reverse=True)
    
    # Calculate overall positive rating (average of top 10)
    top_10_avg_positive = sum(t['positive_score'] for t in positive_themes[:10]) / min(len(positive_themes), 10) if positive_themes else 0
    overall_positive_rating = round(top_10_avg_positive, 1)
    
    return jsonify({
        'total_responses': total_responses,
        'overall_positive_rating': overall_positive_rating,
        'positive_themes': positive_themes[:10]  # Top 10 only
    }), 200

# Cache for theme insights loaded from static file
_theme_insights_cache = None

def load_theme_insights():
    """Load theme insights from static JSON file"""
    global _theme_insights_cache
    
    if _theme_insights_cache is not None:
        return _theme_insights_cache
    
    try:
        import os
        # Get the backend directory (parent of routes directory)
        routes_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(routes_dir)
        insights_file = os.path.join(backend_dir, 'data', 'theme_insights.json')
        
        if os.path.exists(insights_file):
            with open(insights_file, 'r', encoding='utf-8') as f:
                _theme_insights_cache = json.load(f)
            print(f"Loaded {len(_theme_insights_cache)} theme insights from {insights_file}")
        else:
            print(f"Theme insights file not found at {insights_file}, returning empty insights")
            print(f"Please run: python backend/generate_theme_insights.py to generate insights")
            _theme_insights_cache = {}
    except Exception as e:
        print(f"Error loading theme insights: {e}")
        import traceback
        traceback.print_exc()
        _theme_insights_cache = {}
    
    return _theme_insights_cache

@analysis_bp.route('/theme-insights', methods=['POST'])
def get_theme_insights():
    """Get AI insights for a specific base_theme or sub_theme from static file"""
    data = request.get_json() or {}
    theme_type = data.get('theme_type')  # 'base_theme' or 'sub_theme'
    theme_name = data.get('theme_name')
    filters = data.get('filters', {})  # Filters are ignored since we use static data
    
    if not theme_type or not theme_name:
        return jsonify({'error': 'theme_type and theme_name are required'}), 400
    
    if theme_type not in ['base_theme', 'sub_theme']:
        return jsonify({'error': 'theme_type must be either "base_theme" or "sub_theme"'}), 400
    
    try:
        # Load insights from static file
        insights_data = load_theme_insights()
        
        # Look up insights for this theme
        insight_key = f"{theme_type}_{theme_name}"
        
        if insight_key in insights_data:
            return jsonify(insights_data[insight_key]), 200
        else:
            # Return empty insights if not found
            return jsonify({
                'positive_summary': 'No insights available for this theme.',
                'negative_summary': 'No insights available for this theme.',
                'positive_recommendations': [],
                'negative_recommendations': []
            }), 200
        
    except Exception as e:
        import traceback
        print(f"Error in get_theme_insights: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'positive_summary': '',
            'negative_summary': '',
            'positive_recommendations': [],
            'negative_recommendations': []
        }), 200
