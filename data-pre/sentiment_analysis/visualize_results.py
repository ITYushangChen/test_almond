"""
Visualize sentiment analysis model comparison results
"""
import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import Dict, List

# Set style
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

def load_results(json_path: str = None) -> Dict:
    """Load results from JSON file"""
    if json_path is None:
        json_path = os.path.join(os.path.dirname(__file__), '..', 'sentiment_comparison_results.json')
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Results file not found at {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def plot_accuracy_comparison(results: Dict, save_path: str = None):
    """Plot accuracy comparison bar chart"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    model_results = [r for r in results['results'] if r.get('status') == 'success']
    model_results.sort(key=lambda x: x['accuracy'], reverse=True)
    
    models = [r['model'] for r in model_results]
    accuracies = [r['accuracy'] * 100 for r in model_results]
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(models)))
    
    bars = ax.barh(models, accuracies, color=colors, edgecolor='black', linewidth=1.2)
    
    # Add value labels on bars
    for i, (bar, acc) in enumerate(zip(bars, accuracies)):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{acc:.1f}%', ha='left', va='center', fontweight='bold', fontsize=11)
    
    ax.set_xlabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Sentiment Analysis Models - Accuracy Comparison', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlim(0, 100)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    
    # Add vertical line at 80%
    ax.axvline(x=80, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(80, len(models) - 0.5, '80% threshold', rotation=90, 
            verticalalignment='bottom', color='red', alpha=0.7)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved accuracy comparison to {save_path}")
    plt.show()

def plot_per_class_metrics(results: Dict, save_path: str = None):
    """Plot per-class metrics (precision, recall, F1) for each model"""
    model_results = [r for r in results['results'] if r.get('status') == 'success']
    model_results.sort(key=lambda x: x['accuracy'], reverse=True)
    
    models = [r['model'] for r in model_results]
    # Only positive and negative, no neutral
    classes = ['positive', 'negative']
    metrics = ['precision', 'recall', 'f1']
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    x = np.arange(len(models))
    width = 0.35
    colors = ['#2ecc71', '#e74c3c']  # green for positive, red for negative
    
    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        
        for i, cls in enumerate(classes):
            values = [r['per_class'][cls][metric] * 100 for r in model_results]
            offset = (i - 1) * width
            bars = ax.bar(x + offset, values, width, label=cls.capitalize(), 
                         color=colors[i], edgecolor='black', linewidth=0.8)
            
            # Add value labels
            for bar, val in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{val:.0f}%', ha='center', va='bottom', fontsize=8)
        
        ax.set_ylabel(f'{metric.capitalize()} (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'{metric.capitalize()} by Class', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([m.split('-')[0] if '-' in m else m[:15] for m in models], 
                          rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend(loc='upper left')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.suptitle('Per-Class Metrics Comparison', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved per-class metrics to {save_path}")
    plt.show()

def plot_radar_chart(results: Dict, save_path: str = None):
    """Plot radar chart for each model showing per-class F1 scores"""
    model_results = [r for r in results['results'] if r.get('status') == 'success']
    model_results.sort(key=lambda x: x['accuracy'], reverse=True)
    
    # Only positive and negative, no neutral
    classes = ['positive', 'negative']
    num_classes = len(classes)
    
    # Calculate angles for radar chart
    angles = np.linspace(0, 2 * np.pi, num_classes, endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(model_results)))
    
    for idx, result in enumerate(model_results):
        values = [result['per_class'][cls]['f1'] * 100 for cls in classes]
        values += values[:1]  # Complete the circle
        
        ax.plot(angles, values, 'o-', linewidth=2, label=result['model'].split('-')[0], 
               color=colors[idx], markersize=8)
        ax.fill(angles, values, alpha=0.15, color=colors[idx])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([cls.capitalize() for cls in classes], fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=9)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_title('F1 Score by Class - Radar Chart', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved radar chart to {save_path}")
    plt.show()

def plot_confusion_heatmap(results: Dict, save_path: str = None):
    """Plot confusion matrix heatmap for each model (estimated from metrics)"""
    model_results = [r for r in results['results'] if r.get('status') == 'success']
    model_results.sort(key=lambda x: x['accuracy'], reverse=True)
    
    # Only positive and negative, no neutral
    classes = ['positive', 'negative']
    n_models = len(model_results)
    
    fig, axes = plt.subplots(1, n_models, figsize=(5*n_models, 4))
    if n_models == 1:
        axes = [axes]
    
    for idx, result in enumerate(model_results):
        ax = axes[idx]
        
        # Estimate confusion matrix from precision and recall
        # This is a simplified estimation
        matrix = np.zeros((2, 2))  # 2x2 for positive and negative only
        support = results['ground_truth_distribution']
        
        for i, cls_true in enumerate(classes):
            precision = result['per_class'][cls_true]['precision']
            recall = result['per_class'][cls_true]['recall']
            support_count = support[cls_true]
            
            # Estimated true positives
            tp = recall * support_count
            # Estimated false positives
            fp = (tp / precision) - tp if precision > 0 else 0
            # Estimated false negatives
            fn = support_count - tp
            
            matrix[i, i] = tp
            # Distribute errors (only between positive and negative)
            if i == 0:  # positive
                matrix[i, 1] = fn  # confused with negative
            else:  # negative
                matrix[i, 0] = fn  # confused with positive
        
        # Normalize to percentages (handle division by zero)
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # Avoid division by zero
        matrix = (matrix / row_sums * 100).round(1)
        
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=100)
        ax.set_xticks(np.arange(len(classes)))
        ax.set_yticks(np.arange(len(classes)))
        ax.set_xticklabels([c.capitalize() for c in classes])
        ax.set_yticklabels([c.capitalize() for c in classes])
        ax.set_title(f"{result['model'].split('-')[0]}\nAccuracy: {result['accuracy']:.1%}", 
                    fontsize=10, fontweight='bold')
        
        # Add text annotations
        for i in range(len(classes)):
            for j in range(len(classes)):
                text = ax.text(j, i, f'{matrix[i, j]:.0f}%',
                             ha="center", va="center", color="black", fontweight='bold')
        
        ax.set_xlabel('Predicted', fontsize=9)
        if idx == 0:
            ax.set_ylabel('Actual', fontsize=9)
    
    plt.suptitle('Confusion Matrix (Estimated) - Heatmaps', fontsize=14, fontweight='bold')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved confusion heatmaps to {save_path}")
    plt.show()

def plot_comprehensive_dashboard(results: Dict, save_path: str = None):
    """Create a comprehensive dashboard with all visualizations"""
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    model_results = [r for r in results['results'] if r.get('status') == 'success']
    model_results.sort(key=lambda x: x['accuracy'], reverse=True)
    
    models = [r['model'].split('-')[0] if '-' in r['model'] else r['model'][:15] for r in model_results]
    # Only positive and negative, no neutral
    classes = ['positive', 'negative']
    
    # 1. Accuracy comparison (top left, spans 2 columns)
    ax1 = fig.add_subplot(gs[0, :2])
    accuracies = [r['accuracy'] * 100 for r in model_results]
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(models)))
    bars = ax1.barh(models, accuracies, color=colors, edgecolor='black', linewidth=1.2)
    for bar, acc in zip(bars, accuracies):
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{acc:.1f}%', ha='left', va='center', fontweight='bold')
    ax1.set_xlabel('Accuracy (%)', fontweight='bold')
    ax1.set_title('Overall Accuracy Comparison', fontweight='bold', fontsize=12)
    ax1.set_xlim(0, 100)
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. F1 scores comparison (top right)
    ax2 = fig.add_subplot(gs[0, 2])
    x = np.arange(len(models))
    width = 0.25
    for i, cls in enumerate(classes):
        f1_scores = [r['per_class'][cls]['f1'] * 100 for r in model_results]
        offset = (i - 1) * width
        ax2.bar(x + offset, f1_scores, width, label=cls.capitalize(), 
               color=['#2ecc71', '#e74c3c'][i])  # green for positive, red for negative
    ax2.set_ylabel('F1 Score (%)', fontweight='bold')
    ax2.set_title('F1 Scores by Class', fontweight='bold', fontsize=11)
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, rotation=45, ha='right', fontsize=8)
    ax2.legend(fontsize=8)
    ax2.grid(axis='y', alpha=0.3)
    
    # 3. Precision comparison (middle left)
    ax3 = fig.add_subplot(gs[1, 0])
    precision_data = [[r['per_class'][cls]['precision'] * 100 for cls in classes] 
                      for r in model_results]
    im3 = ax3.imshow(precision_data, cmap='YlGn', aspect='auto', vmin=60, vmax=95)
    ax3.set_xticks(range(len(classes)))
    ax3.set_xticklabels([c.capitalize() for c in classes])
    ax3.set_yticks(range(len(models)))
    ax3.set_yticklabels(models, fontsize=8)
    ax3.set_title('Precision Heatmap', fontweight='bold', fontsize=11)
    for i in range(len(models)):
        for j in range(len(classes)):
            text = ax3.text(j, i, f'{precision_data[i][j]:.0f}%',
                           ha="center", va="center", color="black", fontweight='bold', fontsize=9)
    plt.colorbar(im3, ax=ax3, fraction=0.046)
    
    # 4. Recall comparison (middle center)
    ax4 = fig.add_subplot(gs[1, 1])
    recall_data = [[r['per_class'][cls]['recall'] * 100 for cls in classes] 
                   for r in model_results]
    im4 = ax4.imshow(recall_data, cmap='YlOrRd', aspect='auto', vmin=60, vmax=95)
    ax4.set_xticks(range(len(classes)))
    ax4.set_xticklabels([c.capitalize() for c in classes])
    ax4.set_yticks(range(len(models)))
    ax4.set_yticklabels(models, fontsize=8)
    ax4.set_title('Recall Heatmap', fontweight='bold', fontsize=11)
    for i in range(len(models)):
        for j in range(len(classes)):
            text = ax4.text(j, i, f'{recall_data[i][j]:.0f}%',
                           ha="center", va="center", color="black", fontweight='bold', fontsize=9)
    plt.colorbar(im4, ax=ax4, fraction=0.046)
    
    # 5. F1 comparison (middle right)
    ax5 = fig.add_subplot(gs[1, 2])
    f1_data = [[r['per_class'][cls]['f1'] * 100 for cls in classes] 
              for r in model_results]
    im5 = ax5.imshow(f1_data, cmap='RdYlGn', aspect='auto', vmin=60, vmax=95)
    ax5.set_xticks(range(len(classes)))
    ax5.set_xticklabels([c.capitalize() for c in classes])
    ax5.set_yticks(range(len(models)))
    ax5.set_yticklabels(models, fontsize=8)
    ax5.set_title('F1 Score Heatmap', fontweight='bold', fontsize=11)
    for i in range(len(models)):
        for j in range(len(classes)):
            text = ax5.text(j, i, f'{f1_data[i][j]:.0f}%',
                           ha="center", va="center", color="black", fontweight='bold', fontsize=9)
    plt.colorbar(im5, ax=ax5, fraction=0.046)
    
    # 6. Radar chart (bottom, spans 3 columns)
    ax6 = fig.add_subplot(gs[2, :], projection='polar')
    angles = np.linspace(0, 2 * np.pi, len(classes), endpoint=False).tolist()
    angles += angles[:1]
    colors_radar = plt.cm.Set3(np.linspace(0, 1, len(models)))
    
    for idx, result in enumerate(model_results):
        values = [result['per_class'][cls]['f1'] * 100 for cls in classes]
        values += values[:1]
        ax6.plot(angles, values, 'o-', linewidth=2, label=result['model'].split('-')[0], 
                color=colors_radar[idx], markersize=6)
        ax6.fill(angles, values, alpha=0.15, color=colors_radar[idx])
    
    ax6.set_xticks(angles[:-1])
    ax6.set_xticklabels([cls.capitalize() for cls in classes])
    ax6.set_ylim(0, 100)
    ax6.set_yticks([20, 40, 60, 80, 100])
    ax6.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=8)
    ax6.grid(True, linestyle='--', alpha=0.5)
    ax6.set_title('F1 Score Radar Chart by Class', fontweight='bold', fontsize=12, pad=20)
    ax6.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1), fontsize=8)
    
    plt.suptitle('Sentiment Analysis Models - Comprehensive Comparison Dashboard', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved comprehensive dashboard to {save_path}")
    plt.show()

def main():
    """Main function to generate all visualizations"""
    try:
        results = load_results()
        
        # Save all visualizations in sentiment_analysis folder
        output_dir = os.path.dirname(__file__)
        
        print("Generating visualizations...")
        print("="*60)
        
        # 1. Accuracy comparison
        plot_accuracy_comparison(results, 
            os.path.join(output_dir, 'visualization_accuracy.png'))
        
        # 2. Per-class metrics
        plot_per_class_metrics(results, 
            os.path.join(output_dir, 'visualization_per_class.png'))
        
        # 3. Radar chart
        plot_radar_chart(results, 
            os.path.join(output_dir, 'visualization_radar.png'))
        
        # 4. Confusion heatmaps
        plot_confusion_heatmap(results, 
            os.path.join(output_dir, 'visualization_confusion.png'))
        
        # 5. Comprehensive dashboard
        plot_comprehensive_dashboard(results, 
            os.path.join(output_dir, 'visualization_dashboard.png'))
        
        print("\n" + "="*60)
        print("✓ All visualizations generated successfully!")
        print(f"✓ Output directory: {output_dir}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

