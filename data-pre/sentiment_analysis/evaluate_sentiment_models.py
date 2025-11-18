"""
Script to evaluate different sentiment analysis models on the test set
"""
import os
import sys
import json
from typing import List, Dict, Tuple

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load from backend/.env first (if exists)
    backend_env = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    # Also try to load from data-pre/.env (if exists)
    data_pre_env = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(data_pre_env):
        load_dotenv(data_pre_env)
except ImportError:
    print("Warning: python-dotenv not installed. Make sure environment variables are set.")
    print("Install with: pip install python-dotenv")

# Add backend directory to path to import Config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Try to import different sentiment analysis libraries
try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    print("TextBlob not installed. Install with: pip install textblob")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    HAS_VADER = True
except ImportError:
    HAS_VADER = False
    print("VaderSentiment not installed. Install with: pip install vaderSentiment")

try:
    import openai
    from config import Config
    HAS_OPENAI = bool(Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else False
except ImportError:
    HAS_OPENAI = False
except Exception as e:
    HAS_OPENAI = False
    print(f"OpenAI not configured: {e}")

def load_test_set(filename='sentiment_test_set.json'):
    """Load test set with labels"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def textblob_analyze(text: str) -> str:
    """Analyze sentiment using TextBlob"""
    if not HAS_TEXTBLOB:
        return None
    
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    
    if polarity > 0.1:
        return 'positive'
    elif polarity < -0.1:
        return 'negative'
    else:
        return 'neutral'

def vader_analyze(text: str) -> str:
    """Analyze sentiment using VADER"""
    if not HAS_VADER:
        return None
    
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text)
    compound = scores['compound']
    
    if compound >= 0.05:
        return 'positive'
    elif compound <= -0.05:
        return 'negative'
    else:
        return 'neutral'

def openai_analyze(text: str) -> str:
    """Analyze sentiment using OpenAI"""
    if not HAS_OPENAI:
        return None
    
    try:
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a sentiment analysis assistant. Classify the sentiment of the given text as 'positive', 'negative', or 'neutral'. Only respond with one word: positive, negative, or neutral."},
                {"role": "user", "content": text[:500]}  # Limit to 500 chars
            ],
            temperature=0.3,
            max_tokens=10
        )
        result = response.choices[0].message.content.strip().lower()
        if result in ['positive', 'negative', 'neutral']:
            return result
        return 'neutral'
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None

def evaluate_model(predictions: List[str], labels: List[str], model_name: str) -> Dict:
    """Evaluate model predictions against ground truth labels"""
    if len(predictions) != len(labels):
        print(f"Warning: Mismatch in predictions ({len(predictions)}) and labels ({len(labels)})")
        return None
    
    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    total = len(labels)
    accuracy = correct / total if total > 0 else 0
    
    # Calculate per-class metrics
    classes = ['positive', 'negative', 'neutral']
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
        'per_class': class_metrics
    }

def print_results(results: Dict):
    """Print evaluation results in a formatted way"""
    print("\n" + "="*60)
    print(f"Results for {results['model']}")
    print("="*60)
    print(f"Accuracy: {results['accuracy']:.2%} ({results['correct']}/{results['total']})")
    print("\nPer-class metrics:")
    print(f"{'Class':<10} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    print("-" * 60)
    
    for cls, metrics in results['per_class'].items():
        print(f"{cls:<10} {metrics['precision']:<12.2%} {metrics['recall']:<12.2%} {metrics['f1']:<12.2%} {metrics['support']:<10}")

def main():
    # Load test set
    test_set_path = os.path.join(os.path.dirname(__file__), 'sentiment_test_set.json')
    if not os.path.exists(test_set_path):
        print("Error: sentiment_test_set.json not found. Run test_sentiment_models.py first.")
        return
    
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test samples")
    
    # Get ground truth labels
    # Use existing sentiment if available, otherwise use likes as proxy
    labels = []
    texts = []
    
    for item in test_set:
        text = item.get('content', '').strip()
        if not text:
            continue
        
        texts.append(text)
        
        # Ground truth: use sentiment if available, otherwise infer from likes
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
    
    print(f"Processing {len(texts)} samples...\n")
    
    # Run different models
    results = []
    
    # TextBlob
    if HAS_TEXTBLOB:
        print("Running TextBlob...")
        predictions = [textblob_analyze(text) for text in texts]
        results.append(evaluate_model(predictions, labels, "TextBlob"))
    else:
        print("Skipping TextBlob (not installed)")
    
    # VADER
    if HAS_VADER:
        print("Running VADER...")
        predictions = [vader_analyze(text) for text in texts]
        results.append(evaluate_model(predictions, labels, "VADER"))
    else:
        print("Skipping VADER (not installed)")
    
    # OpenAI
    if HAS_OPENAI:
        print("Running OpenAI GPT-3.5-turbo...")
        predictions = []
        for i, text in enumerate(texts):
            print(f"  Processing {i+1}/{len(texts)}...", end='\r')
            pred = openai_analyze(text)
            predictions.append(pred or 'neutral')
        print()  # New line after progress
        results.append(evaluate_model(predictions, labels, "OpenAI GPT-3.5-turbo"))
    else:
        print("Skipping OpenAI (not configured)")
    
    # Print results
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    
    for result in results:
        if result:
            print_results(result)
    
    # Compare models
    if len(results) > 1:
        print("\n" + "="*60)
        print("MODEL COMPARISON")
        print("="*60)
        print(f"{'Model':<25} {'Accuracy':<15} {'Correct/Total':<15}")
        print("-" * 60)
        for result in results:
            if result:
                print(f"{result['model']:<25} {result['accuracy']:<15.2%} {result['correct']}/{result['total']}")

if __name__ == '__main__':
    main()

