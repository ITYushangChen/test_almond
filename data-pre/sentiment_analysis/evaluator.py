"""
Evaluator for comparing multiple sentiment analysis models
"""
import json
import os
from typing import List, Dict, Tuple
try:
    from .base_model import SentimentModel
except ImportError:
    from base_model import SentimentModel

class SentimentEvaluator:
    """Evaluator for sentiment analysis models"""
    
    def __init__(self, test_set_path: str):
        """
        Initialize evaluator with test set
        
        Args:
            test_set_path: Path to JSON test set file
        """
        self.test_set_path = test_set_path
        self.test_data = None
        self.load_test_set()
    
    def load_test_set(self):
        """Load test set from JSON file"""
        if not os.path.exists(self.test_set_path):
            raise FileNotFoundError(f"Test set not found: {self.test_set_path}")
        
        with open(self.test_set_path, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
        
        print(f"Loaded {len(self.test_data)} test samples from {self.test_set_path}")
    
    def get_ground_truth_labels(self) -> Tuple[List[str], List[str]]:
        """
        Get ground truth labels from test set
        
        Returns:
            Tuple of (texts, labels)
        """
        texts = []
        labels = []
        
        for item in self.test_data:
            text = item.get('content', '').strip()
            if not text:
                continue
            
            texts.append(text)
            
            # Get ground truth: use sentiment if available, otherwise infer from likes
            sentiment = item.get('sentiment')
            if sentiment:
                labels.append(sentiment.lower())
            else:
                # Use likes as proxy
                likes = item.get('likes', 0)
                if likes > 0:
                    labels.append('positive')
                elif likes < 0:
                    labels.append('negative')
                else:
                    labels.append('neutral')
        
        return texts, labels
    
    def evaluate_model(self, model: SentimentModel, texts: List[str], labels: List[str]) -> Dict:
        """
        Evaluate a single model
        
        Args:
            model: SentimentModel instance
            texts: List of input texts
            labels: List of ground truth labels
        
        Returns:
            Evaluation metrics dictionary
        """
        print(f"\nEvaluating {model.name}...")
        
        # Initialize model if needed
        if not model.initialized:
            try:
                model.initialize()
            except Exception as e:
                return {
                    'model': model.name,
                    'error': str(e),
                    'status': 'failed'
                }
        
        # Get predictions
        predictions = []
        for i, text in enumerate(texts):
            try:
                result = model.predict(text)
                predictions.append(result['label'])
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{len(texts)}...", end='\r')
            except Exception as e:
                print(f"  Error on sample {i+1}: {e}")
                predictions.append('positive')  # Fallback (default to positive)
        
        print()  # New line
        
        # Calculate metrics
        return self._calculate_metrics(predictions, labels, model.name)
    
    def _calculate_metrics(self, predictions: List[str], labels: List[str], model_name: str) -> Dict:
        """Calculate evaluation metrics"""
        if len(predictions) != len(labels):
            print(f"Warning: Mismatch in predictions ({len(predictions)}) and labels ({len(labels)})")
            return None
        
        # Overall accuracy
        correct = sum(1 for p, l in zip(predictions, labels) if p == l)
        total = len(labels)
        accuracy = correct / total if total > 0 else 0
        
        # Per-class metrics (only positive and negative, no neutral)
        classes = ['positive', 'negative']
        class_metrics = {}
        
        for cls in classes:
            true_positives = sum(1 for p, l in zip(predictions, labels) if p == cls and l == cls)
            false_positives = sum(1 for p, l in zip(predictions, labels) if p == cls and l != cls)
            false_negatives = sum(1 for p, l in zip(predictions, labels) if p != cls and l == cls)
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            class_metrics[cls] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': sum(1 for l in labels if l == cls)
            }
        
        return {
            'model': model_name,
            'accuracy': accuracy,
            'correct': correct,
            'total': total,
            'per_class': class_metrics,
            'status': 'success'
        }
    
    def compare_models(self, models: List[SentimentModel]) -> Dict:
        """
        Compare multiple models on the test set
        
        Args:
            models: List of SentimentModel instances
        
        Returns:
            Dictionary with all results
        """
        texts, labels = self.get_ground_truth_labels()
        
        print(f"Evaluating {len(models)} models on {len(texts)} samples...")
        
        results = []
        for model in models:
            try:
                result = self.evaluate_model(model, texts, labels)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error evaluating {model.name}: {e}")
                results.append({
                    'model': model.name,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return {
            'results': results,
            'total_samples': len(texts),
            'ground_truth_distribution': self._get_label_distribution(labels)
        }
    
    def _get_label_distribution(self, labels: List[str]) -> Dict:
        """Get distribution of labels"""
        distribution = {}
        for label in labels:
            distribution[label] = distribution.get(label, 0) + 1
        return distribution
    
    def print_results(self, comparison_results: Dict):
        """Print comparison results in a formatted way"""
        results = comparison_results['results']
        
        print("\n" + "="*80)
        print("SENTIMENT ANALYSIS MODEL COMPARISON")
        print("="*80)
        print(f"Total samples: {comparison_results['total_samples']}")
        print(f"\nGround truth distribution:")
        for label, count in comparison_results['ground_truth_distribution'].items():
            print(f"  {label}: {count}")
        
        # Print individual model results
        for result in results:
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
        print(f"{'Model':<40} {'Accuracy':<15} {'Correct/Total':<15}")
        print("-"*80)
        
        for result in results:
            if result.get('status') == 'success':
                print(f"{result['model']:<40} {result['accuracy']:<15.2%} {result['correct']}/{result['total']}")
            else:
                print(f"{result['model']:<40} {'FAILED':<15} {'N/A':<15}")

