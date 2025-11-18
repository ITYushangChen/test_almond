#!/usr/bin/env python3
"""
Performance Testing Script for Database Queries
Compares query performance before and after adding indexes

Usage:
    python3 backend/performance_test.py
"""

import os
import sys
import time
import statistics
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from config import Config

def get_supabase_client():
    """Get Supabase client directly without Flask context"""
    supabase_url = Config.SUPABASE_URL
    supabase_key = Config.SUPABASE_KEY
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(supabase_url, supabase_key)

def time_query(query_func, iterations=5):
    """Time a query function multiple times and return statistics"""
    times = []
    
    for i in range(iterations):
        start = time.time()
        try:
            result = query_func()
            elapsed = time.time() - start
            times.append(elapsed)
        except Exception as e:
            print(f"Query failed: {e}")
            return None
    
    return {
        'min': min(times),
        'max': max(times),
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'times': times
    }

def test_benchmark_radar_query():
    """Test benchmark radar data query"""
    supabase = get_supabase_client()
    
    def query():
        query = supabase.table('cb').select('base_theme,sub_theme,likes,sentiment')
        query = query.gte('date', '2024-01-01')
        query = query.lt('date', '2024-02-01')
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        query = query.limit(10000)
        response = query.execute()
        return len(response.data)
    
    return time_query(query, iterations=5)

def test_year_query():
    """Test year-based query"""
    supabase = get_supabase_client()
    
    def query():
        query = supabase.table('cb').select('base_theme,sub_theme,likes,sentiment')
        query = query.gte('date', '2024-01-01')
        query = query.lt('date', '2025-01-01')
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        query = query.limit(100000)
        response = query.execute()
        return len(response.data)
    
    return time_query(query, iterations=3)

def test_dimension_query():
    """Test dimension-based query (source/language)"""
    supabase = get_supabase_client()
    
    def query():
        query = supabase.table('cb').select('base_theme,sub_theme,likes,sentiment')
        query = query.eq('source', 'Reddit')  # Adjust based on your data
        query = query.neq('base_theme', 'others')
        query = query.neq('base_theme', 'stock_market')
        query = query.neq('sub_theme', 'others')
        query = query.limit(100000)
        response = query.execute()
        return len(response.data)
    
    return time_query(query, iterations=3)

def test_dashboard_kpis():
    """Test dashboard KPIs query"""
    supabase = get_supabase_client()
    
    def query():
        query = supabase.table('cb').select('sentiment,base_theme,likes')
        query = query.not_.in_('base_theme', ['others', 'stock_market'])
        query = query.not_.in_('sub_theme', ['others', 'stock_market'])
        response = query.execute()
        return len(response.data)
    
    return time_query(query, iterations=5)

def test_filter_options():
    """Test filter options query"""
    supabase = get_supabase_client()
    
    def query():
        response = supabase.table('cb').select('base_theme,sub_theme,language,source,date').execute()
        return len(response.data)
    
    return time_query(query, iterations=3)

def print_results(test_name, results):
    """Print formatted test results"""
    if results is None:
        print(f"\n{test_name}: FAILED")
        return
    
    print(f"\n{'='*60}")
    print(f"{test_name}")
    print(f"{'='*60}")
    print(f"  Mean:    {results['mean']:.4f}s")
    print(f"  Median:  {results['median']:.4f}s")
    print(f"  Min:     {results['min']:.4f}s")
    print(f"  Max:     {results['max']:.4f}s")
    print(f"  StdDev:  {results['stdev']:.4f}s")
    print(f"  Times:   {[f'{t:.4f}' for t in results['times']]}")

def save_results(results, label='before'):
    """Save test results to JSON file"""
    # Save to data/performance_results instead of backend/performance_results
    backend_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(backend_dir)
    results_dir = os.path.join(project_root, 'data-pre', 'performance_results')
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'performance_{label}_{timestamp}.json'
    filepath = os.path.join(results_dir, filename)
    
    data = {
        'label': label,
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'summary': {
            'successful_tests': len([k for k, v in results.items() if v is not None]),
            'total_tests': len(results),
        }
    }
    
    # Calculate average time for successful tests
    successful_results = [v for v in results.values() if v is not None]
    if successful_results:
        data['summary']['average_time'] = statistics.mean([r['mean'] for r in successful_results])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {filepath}")
    return filepath

def load_results(filepath):
    """Load test results from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading results: {e}")
        return None

def list_saved_results():
    """List all saved performance test results"""
    backend_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(backend_dir)
    results_dir = os.path.join(project_root, 'data-pre', 'performance_results')
    if not os.path.exists(results_dir):
        return []
    
    results = []
    for filename in sorted(os.listdir(results_dir), reverse=True):
        if filename.endswith('.json'):
            filepath = os.path.join(results_dir, filename)
            try:
                data = load_results(filepath)
                if data:
                    results.append({
                        'filename': filename,
                        'filepath': filepath,
                        'label': data.get('label', 'unknown'),
                        'timestamp': data.get('timestamp', ''),
                        'summary': data.get('summary', {})
                    })
            except:
                pass
    
    return results

def compare_results(before, after, test_name):
    """Compare before and after results"""
    if before is None or after is None:
        return None
    
    improvement = ((before['mean'] - after['mean']) / before['mean']) * 100
    speedup = before['mean'] / after['mean']
    
    comparison = {
        'test_name': test_name,
        'before': before['mean'],
        'after': after['mean'],
        'improvement_percent': improvement,
        'speedup': speedup
    }
    
    print(f"\n{test_name} - Performance Comparison:")
    print(f"  Before:  {before['mean']:.4f}s")
    print(f"  After:   {after['mean']:.4f}s")
    print(f"  Improvement: {improvement:.1f}%")
    print(f"  Speedup: {speedup:.2f}x")
    
    return comparison

def compare_saved_results(before_file, after_file):
    """Compare two saved result files"""
    before_data = load_results(before_file)
    after_data = load_results(after_file)
    
    if not before_data or not after_data:
        print("Error: Could not load one or both result files")
        return
    
    before_results = before_data.get('results', {})
    after_results = after_data.get('results', {})
    
    print(f"\n{'='*60}")
    print("Performance Comparison Report")
    print(f"{'='*60}")
    print(f"Before: {before_data.get('label', 'unknown')} - {before_data.get('timestamp', '')}")
    print(f"After:  {after_data.get('label', 'unknown')} - {after_data.get('timestamp', '')}")
    print(f"{'='*60}\n")
    
    comparisons = []
    for test_name in before_results.keys():
        if test_name in after_results:
            before_result = before_results[test_name]
            after_result = after_results[test_name]
            
            if before_result is not None and after_result is not None:
                comparison = compare_results(before_result, after_result, test_name)
                if comparison:
                    comparisons.append(comparison)
    
    # Overall summary
    if comparisons:
        avg_improvement = statistics.mean([c['improvement_percent'] for c in comparisons])
        avg_speedup = statistics.mean([c['speedup'] for c in comparisons])
        
        print(f"\n{'='*60}")
        print("Overall Summary")
        print(f"{'='*60}")
        print(f"Average Improvement: {avg_improvement:.1f}%")
        print(f"Average Speedup: {avg_speedup:.2f}x")
        print(f"{'='*60}")
        
        # Save comparison report
        backend_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(backend_dir)
        results_dir = os.path.join(project_root, 'data-pre', 'performance_results')
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        comparison_file = os.path.join(results_dir, f'comparison_{timestamp}.json')
        
        comparison_data = {
            'before_file': before_file,
            'after_file': after_file,
            'before_label': before_data.get('label', 'unknown'),
            'after_label': after_data.get('label', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'comparisons': comparisons,
            'summary': {
                'average_improvement_percent': avg_improvement,
                'average_speedup': avg_speedup
            }
        }
        
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Comparison report saved to: {comparison_file}")
        
        return comparison_data
    
    return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Performance Test')
    parser.add_argument('--label', type=str, default='test', 
                       help='Label for this test run (e.g., "before" or "after")')
    parser.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'),
                       help='Compare two saved result files')
    parser.add_argument('--list', action='store_true',
                       help='List all saved results')
    args = parser.parse_args()
    
    # List saved results
    if args.list:
        saved_results = list_saved_results()
        if saved_results:
            print("\n" + "="*60)
            print("Saved Performance Test Results")
            print("="*60)
            for i, result in enumerate(saved_results, 1):
                print(f"\n{i}. {result['filename']}")
                print(f"   Label: {result['label']}")
                print(f"   Timestamp: {result['timestamp']}")
                summary = result.get('summary', {})
                print(f"   Tests: {summary.get('successful_tests', 0)}/{summary.get('total_tests', 0)}")
                if 'average_time' in summary:
                    print(f"   Avg Time: {summary['average_time']:.4f}s")
            print("\n" + "="*60)
        else:
            print("No saved results found.")
        return
    
    # Compare two result files
    if args.compare:
        compare_saved_results(args.compare[0], args.compare[1])
        return
    
    # Run performance tests
    print("="*60)
    print("Database Performance Test")
    print("="*60)
    print(f"\nTest Label: {args.label}")
    print("This script tests query performance.")
    print("Run this BEFORE and AFTER creating indexes to compare results.\n")
    
    # Check if indexes exist
    try:
        supabase = get_supabase_client()
        # Try to get index info (this might not work with Supabase client)
        print("Note: Index existence check may not work with Supabase client.")
        print("Please verify indexes are created in Supabase dashboard.\n")
    except Exception as e:
        print(f"Warning: Could not check indexes: {e}\n")
    
    input("Press Enter to start performance tests...")
    
    print("\nRunning performance tests (this may take a while)...\n")
    
    # Run tests
    tests = [
        ("Benchmark Radar Query (Monthly)", test_benchmark_radar_query),
        ("Year Query", test_year_query),
        ("Dimension Query (Source)", test_dimension_query),
        ("Dashboard KPIs", test_dashboard_kpis),
        ("Filter Options", test_filter_options),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            print_results(test_name, result)
        except Exception as e:
            print(f"\n{test_name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = None
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    
    successful_tests = [k for k, v in results.items() if v is not None]
    print(f"Successful tests: {len(successful_tests)}/{len(tests)}")
    
    if successful_tests:
        avg_time = statistics.mean([results[k]['mean'] for k in successful_tests])
        print(f"Average query time: {avg_time:.4f}s")
    
    # Save results
    saved_file = save_results(results, label=args.label)
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("1. Create indexes using: backend/database_indexes.sql")
    print(f"2. Run this script again with: python3 performance_test.py --label after")
    print(f"3. Compare results with: python3 performance_test.py --compare <before_file> <after_file>")
    print(f"4. List all results with: python3 performance_test.py --list")
    print(f"5. Visualize results with: python3 backend/visualize_performance.py --latest")
    print("="*60)
    print(f"\n💡 Results are saved to: data-pre/performance_results/")
    print(f"💡 Visualizations will be saved to: data-pre/performance_results/visualizations/")

if __name__ == '__main__':
    main()

