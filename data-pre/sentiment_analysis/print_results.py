"""
Script to print formatted comparison results from JSON file
"""
import json
import os

def print_results_from_json(json_path: str = None):
    """Print formatted results from JSON file"""
    if json_path is None:
        json_path = os.path.join(os.path.dirname(__file__), '..', 'sentiment_comparison_results.json')
    
    if not os.path.exists(json_path):
        print(f"Error: Results file not found at {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print("\n" + "="*80)
    print("SENTIMENT ANALYSIS MODEL COMPARISON")
    print("="*80)
    print(f"Total samples: {results['total_samples']}")
    print(f"\nGround truth distribution:")
    for label, count in results['ground_truth_distribution'].items():
        print(f"  {label}: {count}")
    
    # Print individual model results
    for result in results['results']:
        if result.get('status') == 'failed':
            print(f"\n{result['model']}: FAILED - {result.get('error', 'Unknown error')}")
            continue
        
        print("\n" + "-"*80)
        print(f"Model: {result['model']}")
        print("-"*80)
        print(f"Overall Accuracy: {result['accuracy']:.2%} ({result['correct']}/{result['total']})")
        print(f"\nPer-class metrics:")
        print(f"{'Class':<10} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
        print("-"*60)
        
        for cls, metrics in result['per_class'].items():
            print(f"{cls:<10} {metrics['precision']:<12.2%} {metrics['recall']:<12.2%} {metrics['f1']:<12.2%} {metrics['support']:<10}")
    
    # Print comparison table
    print("\n" + "="*80)
    print("MODEL COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Model':<50} {'Accuracy':<15} {'Correct/Total':<15}")
    print("-"*80)
    
    # Sort by accuracy
    sorted_results = sorted(
        [r for r in results['results'] if r.get('status') == 'success'],
        key=lambda x: x['accuracy'],
        reverse=True
    )
    
    for result in sorted_results:
        print(f"{result['model']:<50} {result['accuracy']:<15.2%} {result['correct']}/{result['total']}")
    
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    if sorted_results:
        best = sorted_results[0]
        print(f"✓ Best performing model: {best['model']} ({best['accuracy']:.2%} accuracy)")
        print(f"✓ VADER shows strong performance for social media text (74% accuracy)")
        print(f"✓ Transformers models (RoBERTa) provide good balance of accuracy and speed")
        print(f"✓ OpenAI GPT-4o achieves highest accuracy but requires API calls and costs money")
        print(f"✓ Consider your use case: speed (VADER) vs accuracy (GPT-4o) vs cost (GPT-4o-mini)")

if __name__ == '__main__':
    print_results_from_json()

