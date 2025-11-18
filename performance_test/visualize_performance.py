#!/usr/bin/env python3
"""
Visualize Performance Test Results
Generates charts comparing before/after performance

Usage:
    python3 backend/visualize_performance.py [comparison_file.json]
    python3 backend/visualize_performance.py --latest
"""

import os
import sys
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-darkgrid' if 'darkgrid' in plt.style.available else 'seaborn-v0_8')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11

def load_comparison(filepath):
    """Load comparison JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_latest_comparison():
    """Find the latest comparison file"""
    # Look in data-pre/performance_results
    project_root = Path(__file__).parent.parent
    results_dir = project_root / 'data-pre' / 'performance_results'
    if not results_dir.exists():
        # Fallback to backend/performance_results for backward compatibility
        results_dir = Path(__file__).parent / 'performance_results'
        if not results_dir.exists():
            return None
    
    comparison_files = sorted(
        [f for f in results_dir.glob('comparison_*.json')],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    return str(comparison_files[0]) if comparison_files else None

def visualize_performance_comparison(comparison_data, output_path=None):
    """Create visualization charts for performance comparison"""
    
    comparisons = comparison_data.get('comparisons', [])
    summary = comparison_data.get('summary', {})
    
    if not comparisons:
        print("No comparison data found")
        return
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 1. Bar Chart: Query Time Comparison
    ax1 = fig.add_subplot(gs[0, :])
    test_names = [c['test_name'] for c in comparisons]
    before_times = [c['before'] for c in comparisons]
    after_times = [c['after'] for c in comparisons]
    
    x = np.arange(len(test_names))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, before_times, width, label='Before Indexes', 
                    color='#e57373', alpha=0.8)
    bars2 = ax1.bar(x + width/2, after_times, width, label='After Indexes', 
                    color='#81c784', alpha=0.8)
    
    ax1.set_xlabel('Test Query', fontweight='bold')
    ax1.set_ylabel('Time (seconds)', fontweight='bold')
    ax1.set_title('Query Performance: Before vs After Indexes', fontsize=14, fontweight='bold', pad=20)
    ax1.set_xticks(x)
    ax1.set_xticklabels([name.replace(' Query', '').replace(' (Monthly)', '') for name in test_names], 
                        rotation=15, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}s',
                    ha='center', va='bottom', fontsize=9)
    
    # 2. Improvement Percentage Chart
    ax2 = fig.add_subplot(gs[1, 0])
    improvements = [c['improvement_percent'] for c in comparisons]
    colors = ['#81c784' if imp > 0 else '#e57373' for imp in improvements]
    
    bars = ax2.barh(test_names, improvements, color=colors, alpha=0.8)
    ax2.set_xlabel('Improvement (%)', fontweight='bold')
    ax2.set_title('Performance Improvement by Query', fontsize=12, fontweight='bold')
    ax2.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax2.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (bar, imp) in enumerate(zip(bars, improvements)):
        ax2.text(imp, i, f'{imp:.1f}%',
                ha='left' if imp > 0 else 'right', va='center', fontsize=9, fontweight='bold')
    
    # 3. Speedup Chart
    ax3 = fig.add_subplot(gs[1, 1])
    speedups = [c['speedup'] for c in comparisons]
    colors_speedup = ['#81c784' if s > 1 else '#e57373' for s in speedups]
    
    bars = ax3.barh(test_names, speedups, color=colors_speedup, alpha=0.8)
    ax3.set_xlabel('Speedup (x)', fontweight='bold')
    ax3.set_title('Query Speedup Factor', fontsize=12, fontweight='bold')
    ax3.axvline(x=1, color='black', linestyle='--', linewidth=1, label='No change')
    ax3.grid(axis='x', alpha=0.3)
    ax3.legend()
    
    # Add value labels
    for i, (bar, speedup) in enumerate(zip(bars, speedups)):
        ax3.text(speedup, i, f'{speedup:.2f}x',
                ha='left' if speedup > 1 else 'right', va='center', fontsize=9, fontweight='bold')
    
    # 4. Summary Statistics
    ax4 = fig.add_subplot(gs[2, :])
    ax4.axis('off')
    
    # Create summary text
    avg_improvement = summary.get('average_improvement_percent', 0)
    avg_speedup = summary.get('average_speedup', 1)
    
    summary_text = f"""
    Performance Optimization Summary
    {'='*60}
    
    Average Improvement: {avg_improvement:.1f}%
    Average Speedup: {avg_speedup:.2f}x
    
    Test Details:
    """
    
    for c in comparisons:
        improvement = c['improvement_percent']
        speedup = c['speedup']
        status = "✅ Improved" if improvement > 0 else "⚠️ Slower"
        status_symbol = "[OK]" if improvement > 0 else "[SLOW]"
        summary_text += f"\n  • {c['test_name']}: {improvement:.1f}% improvement ({speedup:.2f}x) {status_symbol}"
    
    summary_text += f"\n\n{'='*60}"
    summary_text += f"\nBefore: {comparison_data.get('before_label', 'unknown')}"
    summary_text += f"\nAfter:  {comparison_data.get('after_label', 'unknown')}"
    summary_text += f"\nTimestamp: {comparison_data.get('timestamp', 'unknown')}"
    
    ax4.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # Overall title
    fig.suptitle('Database Performance Optimization Results', fontsize=16, fontweight='bold', y=0.98)
    
    # Save figure
    if output_path is None:
        project_root = Path(__file__).parent.parent
        results_dir = project_root / 'data-pre' / 'performance_results' / 'visualizations'
        results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = comparison_data.get('timestamp', '').replace(':', '-').split('.')[0]
        output_path = results_dir / f'performance_comparison_{timestamp}.png'
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n[SUCCESS] Visualization saved to: {output_path}")
    
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Visualize Performance Test Results')
    parser.add_argument('comparison_file', nargs='?', default=None,
                       help='Path to comparison JSON file')
    parser.add_argument('--latest', action='store_true',
                       help='Use the latest comparison file')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path (default: auto-generated)')
    
    args = parser.parse_args()
    
    # Determine which file to use
    if args.latest:
        comparison_file = find_latest_comparison()
        if not comparison_file:
            print("❌ No comparison files found. Run performance tests first.")
            return
        print(f"Using latest comparison: {comparison_file}")
    elif args.comparison_file:
        comparison_file = args.comparison_file
    else:
        # Try to find latest if no file specified
        comparison_file = find_latest_comparison()
        if not comparison_file:
            print("❌ No comparison file specified and none found.")
            print("Usage: python3 visualize_performance.py [file.json] or --latest")
            return
        print(f"Using latest comparison: {comparison_file}")
    
    # Load and visualize
    try:
        comparison_data = load_comparison(comparison_file)
        visualize_performance_comparison(comparison_data, args.output)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

