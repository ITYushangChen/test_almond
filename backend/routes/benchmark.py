from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from supabase_client import get_supabase
from collections import defaultdict
from routes.dashboard import apply_filters

benchmark_bp = Blueprint('benchmark', __name__)

@benchmark_bp.route('/radar-data', methods=['POST'])
def get_radar_data():
    data = request.get_json() or {}
    month_a = data.get('month_a')  # Format: YYYY-MM
    month_b = data.get('month_b')
    metric = data.get('metric', 'count')  # 'count' or 'enps'
    
    if not month_a or not month_b:
        return jsonify({'error': 'Both month_a and month_b are required'}), 400
    
    supabase = get_supabase()
    
    def get_month_data(month_str):
        # Query cb table for the specific month
        # Use date range query (month_str format: YYYY-MM)
        # Calculate start and end dates for the month
        from datetime import datetime
        start_date = f"{month_str}-01"
        # Calculate the first day of next month as end date
        year, month = map(int, month_str.split('-'))
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        # Apply filter logic (exclude others and stock_market)
        query = supabase.table('cb').select('base_theme,sub_theme,likes,sentiment')
        # Apply date range filter
        query = query.gte('date', start_date)
        query = query.lt('date', end_date)
        # Apply default filters
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        # Use limit to get all data
        query = query.limit(10000)
        response = query.execute()
        
        theme_data = defaultdict(lambda: {'count': 0, 'positive': 0})
        for item in response.data:
            theme = item.get('base_theme')
            if theme:
                theme_data[theme]['count'] += 1
                
                # Check sentiment for this specific item
                sentiment = item.get('sentiment')
                if sentiment == 'positive':
                    theme_data[theme]['positive'] += 1
        
        # Calculate metric
        result = {}
        for theme, stats in theme_data.items():
            if metric == 'count':
                result[theme] = stats['count']
            else:  # enps
                # eNPS calculation: positive / total * 100
                enps = (stats['positive'] / stats['count'] * 100) if stats['count'] > 0 else 0
                result[theme] = round(enps, 2)
        
        return result
    
    data_a = get_month_data(month_a)
    data_b = get_month_data(month_b)
    
    # Get all unique themes
    all_themes = sorted(set(data_a.keys()) | set(data_b.keys()))
    
    # Format data for radar chart
    radar_data = {
        'themes': all_themes,
        'month_a': {
            'label': month_a,
            'values': [data_a.get(theme, 0) for theme in all_themes]
        },
        'month_b': {
            'label': month_b,
            'values': [data_b.get(theme, 0) for theme in all_themes]
        }
    }
    
    return jsonify(radar_data), 200

@benchmark_bp.route('/theme-flow', methods=['POST'])
def get_theme_flow():
    """Get theme flow data between two months for Sankey/flow visualization"""
    data = request.get_json() or {}
    month_a = data.get('month_a')  # Format: YYYY-MM
    month_b = data.get('month_b')
    
    if not month_a or not month_b:
        return jsonify({'error': 'Both month_a and month_b are required'}), 400
    
    supabase = get_supabase()
    
    def get_month_data(month_str):
        from datetime import datetime
        start_date = f"{month_str}-01"
        year, month = map(int, month_str.split('-'))
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        query = supabase.table('cb').select('base_theme')
        query = query.gte('date', start_date)
        query = query.lt('date', end_date)
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.limit(10000)
        response = query.execute()
        
        theme_counts = defaultdict(int)
        for item in response.data:
            theme = item.get('base_theme')
            if theme:
                theme_counts[theme] += 1
        
        return theme_counts
    
    data_a = get_month_data(month_a)
    data_b = get_month_data(month_b)
    
    # Get all unique themes
    all_themes = sorted(set(data_a.keys()) | set(data_b.keys()))
    
    # Format data for flow visualization
    flow_data = []
    for theme in all_themes:
        count_a = data_a.get(theme, 0)
        count_b = data_b.get(theme, 0)
        change = count_b - count_a
        flow_data.append({
            'theme': theme,
            'month_a': count_a,
            'month_b': count_b,
            'change': change,
            'change_percent': ((change / count_a * 100) if count_a > 0 else 0) if change != 0 else 0
        })
    
    # Sort by absolute change
    flow_data.sort(key=lambda x: abs(x['change']), reverse=True)
    
    return jsonify({
        'month_a': month_a,
        'month_b': month_b,
        'data': flow_data
    }), 200

@benchmark_bp.route('/year-data', methods=['POST'])
def get_year_data():
    """Get radar data for a full year comparison"""
    data = request.get_json() or {}
    year_a = data.get('year_a')  # Format: YYYY
    year_b = data.get('year_b')
    metric = data.get('metric', 'count')  # 'count' or 'enps'
    
    if not year_a or not year_b:
        return jsonify({'error': 'Both year_a and year_b are required'}), 400
    
    supabase = get_supabase()
    
    def get_year_data(year_str):
        # Query cb table for the entire year
        start_date = f"{year_str}-01-01"
        end_date = f"{int(year_str) + 1}-01-01"
        
        # Apply filter logic (exclude others and stock_market)
        query = supabase.table('cb').select('base_theme,sub_theme,likes,sentiment')
        # Apply date range filter
        query = query.gte('date', start_date)
        query = query.lt('date', end_date)
        # Apply default filters
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        # Use limit to get all data
        query = query.limit(100000)  # Increased limit for full year
        response = query.execute()
        
        theme_data = defaultdict(lambda: {'count': 0, 'positive': 0})
        for item in response.data:
            theme = item.get('base_theme')
            if theme:
                theme_data[theme]['count'] += 1
                
                # Check sentiment for this specific item
                sentiment = item.get('sentiment')
                if sentiment == 'positive':
                    theme_data[theme]['positive'] += 1
        
        # Calculate metric
        result = {}
        for theme, stats in theme_data.items():
            if metric == 'count':
                result[theme] = stats['count']
            else:  # enps
                # eNPS calculation: positive / total * 100
                enps = (stats['positive'] / stats['count'] * 100) if stats['count'] > 0 else 0
                result[theme] = round(enps, 2)
        
        return result
    
    data_a = get_year_data(year_a)
    data_b = get_year_data(year_b)
    
    # Get all unique themes
    all_themes = sorted(set(data_a.keys()) | set(data_b.keys()))
    
    # Format data for radar chart
    radar_data = {
        'themes': all_themes,
        'year_a': {
            'label': year_a,
            'values': [data_a.get(theme, 0) for theme in all_themes]
        },
        'year_b': {
            'label': year_b,
            'values': [data_b.get(theme, 0) for theme in all_themes]
        }
    }
    
    return jsonify(radar_data), 200

@benchmark_bp.route('/year-flow', methods=['POST'])
def get_year_flow():
    """Get theme flow data between two years for flow visualization"""
    data = request.get_json() or {}
    year_a = data.get('year_a')  # Format: YYYY
    year_b = data.get('year_b')
    
    if not year_a or not year_b:
        return jsonify({'error': 'Both year_a and year_b are required'}), 400
    
    supabase = get_supabase()
    
    def get_year_data(year_str):
        start_date = f"{year_str}-01-01"
        end_date = f"{int(year_str) + 1}-01-01"
        
        query = supabase.table('cb').select('base_theme')
        query = query.gte('date', start_date)
        query = query.lt('date', end_date)
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.limit(100000)  # Increased limit for full year
        response = query.execute()
        
        theme_counts = defaultdict(int)
        for item in response.data:
            theme = item.get('base_theme')
            if theme:
                theme_counts[theme] += 1
        
        return theme_counts
    
    data_a = get_year_data(year_a)
    data_b = get_year_data(year_b)
    
    # Get all unique themes
    all_themes = sorted(set(data_a.keys()) | set(data_b.keys()))
    
    # Format data for flow visualization
    flow_data = []
    for theme in all_themes:
        count_a = data_a.get(theme, 0)
        count_b = data_b.get(theme, 0)
        change = count_b - count_a
        flow_data.append({
            'theme': theme,
            'year_a': count_a,
            'year_b': count_b,
            'change': change,
            'change_percent': ((change / count_a * 100) if count_a > 0 else 0) if change != 0 else 0
        })
    
    # Sort by absolute change
    flow_data.sort(key=lambda x: abs(x['change']), reverse=True)
    
    return jsonify({
        'year_a': year_a,
        'year_b': year_b,
        'data': flow_data
    }), 200

@benchmark_bp.route('/dimension-data', methods=['POST'])
def get_dimension_data():
    """Get radar data for comparison by dimension (source, language, etc.)"""
    data = request.get_json() or {}
    dimension = data.get('dimension')  # 'source' or 'language'
    value_a = data.get('value_a')
    value_b = data.get('value_b')
    metric = data.get('metric', 'count')  # 'count' or 'enps'
    
    if not dimension or not value_a or not value_b:
        return jsonify({'error': 'dimension, value_a, and value_b are required'}), 400
    
    if dimension not in ['source', 'language']:
        return jsonify({'error': 'dimension must be "source" or "language"'}), 400
    
    supabase = get_supabase()
    
    def get_dimension_data(value):
        # Query cb table filtered by dimension value
        query = supabase.table('cb').select('base_theme,sub_theme,likes,sentiment')
        # Apply dimension filter
        query = query.eq(dimension, value)
        # Apply default filters
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        query = query.limit(100000)
        response = query.execute()
        
        theme_data = defaultdict(lambda: {'count': 0, 'positive': 0})
        for item in response.data:
            theme = item.get('base_theme')
            if theme:
                theme_data[theme]['count'] += 1
                
                # Check sentiment for this specific item
                sentiment = item.get('sentiment')
                if sentiment == 'positive':
                    theme_data[theme]['positive'] += 1
                else:
                    # Fallback to likes-based (likes > 5 as positive proxy)
                    likes = item.get('likes', 0)
                    if likes > 5:
                        theme_data[theme]['positive'] += 1
        
        # Calculate metric
        result = {}
        for theme, stats in theme_data.items():
            if metric == 'count':
                result[theme] = stats['count']
            else:  # enps
                # eNPS calculation: positive / total * 100
                enps = (stats['positive'] / stats['count'] * 100) if stats['count'] > 0 else 0
                result[theme] = round(enps, 2)
        
        return result
    
    data_a = get_dimension_data(value_a)
    data_b = get_dimension_data(value_b)
    
    # Get all unique themes
    all_themes = sorted(set(data_a.keys()) | set(data_b.keys()))
    
    # Format data for radar chart
    radar_data = {
        'themes': all_themes,
        'value_a': {
            'label': value_a,
            'values': [data_a.get(theme, 0) for theme in all_themes]
        },
        'value_b': {
            'label': value_b,
            'values': [data_b.get(theme, 0) for theme in all_themes]
        }
    }
    
    return jsonify(radar_data), 200

@benchmark_bp.route('/dimension-flow', methods=['POST'])
def get_dimension_flow():
    """Get theme flow data between two dimension values"""
    data = request.get_json() or {}
    dimension = data.get('dimension')  # 'source' or 'language'
    value_a = data.get('value_a')
    value_b = data.get('value_b')
    
    if not dimension or not value_a or not value_b:
        return jsonify({'error': 'dimension, value_a, and value_b are required'}), 400
    
    if dimension not in ['source', 'language']:
        return jsonify({'error': 'dimension must be "source" or "language"'}), 400
    
    supabase = get_supabase()
    
    def get_dimension_data(value):
        query = supabase.table('cb').select('base_theme')
        query = query.eq(dimension, value)
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.limit(100000)
        response = query.execute()
        
        theme_counts = defaultdict(int)
        for item in response.data:
            theme = item.get('base_theme')
            if theme:
                theme_counts[theme] += 1
        
        return theme_counts
    
    data_a = get_dimension_data(value_a)
    data_b = get_dimension_data(value_b)
    
    # Get all unique themes
    all_themes = sorted(set(data_a.keys()) | set(data_b.keys()))
    
    # Format data for flow visualization
    flow_data = []
    for theme in all_themes:
        count_a = data_a.get(theme, 0)
        count_b = data_b.get(theme, 0)
        change = count_b - count_a
        flow_data.append({
            'theme': theme,
            'value_a': count_a,
            'value_b': count_b,
            'change': change,
            'change_percent': ((change / count_a * 100) if count_a > 0 else 0) if change != 0 else 0
        })
    
    # Sort by absolute change
    flow_data.sort(key=lambda x: abs(x['change']), reverse=True)
    
    return jsonify({
        'value_a': value_a,
        'value_b': value_b,
        'data': flow_data
    }), 200
