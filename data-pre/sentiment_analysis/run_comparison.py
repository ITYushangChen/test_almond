"""
Main script to run sentiment analysis model comparison
"""
import os
import sys

# Add backend directory to path for config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Load environment variables
try:
    from dotenv import load_dotenv
    backend_env = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env')
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    data_pre_env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(data_pre_env):
        load_dotenv(data_pre_env)
except ImportError:
    print("Warning: python-dotenv not installed.")

# Handle both direct execution and module import
try:
    from .evaluator import SentimentEvaluator
from .textblob_model import TextBlobModel, HAS_TEXTBLOB
from .vader_model import VaderModel, HAS_VADER
from .transformers_model import TransformersModel, HAS_TRANSFORMERS
from .openai_model import OpenAIModel, HAS_OPENAI
except ImportError:
    # If running as script directly
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from evaluator import SentimentEvaluator
    from textblob_model import TextBlobModel, HAS_TEXTBLOB
    from vader_model import VaderModel, HAS_VADER
    from transformers_model import TransformersModel, HAS_TRANSFORMERS
    from openai_model import OpenAIModel, HAS_OPENAI

def main():
    """Run model comparison"""
    # Path to test set
    test_set_path = os.path.join(os.path.dirname(__file__), '..', 'sentiment_test_set.json')
    
    if not os.path.exists(test_set_path):
        print(f"Error: Test set not found at {test_set_path}")
        print("Please run test_sentiment_models.py first to generate the test set.")
        return
    
    # Initialize evaluator
    evaluator = SentimentEvaluator(test_set_path)
    
    # Initialize models
    models = []
    
    # TextBlob
    if HAS_TEXTBLOB:
        try:
            models.append(TextBlobModel())
            print("✓ TextBlob model loaded")
        except Exception as e:
            print(f"✗ TextBlob failed to load: {e}")
    else:
        print("✗ TextBlob not available (install with: pip install textblob)")
    
    # VADER
    if HAS_VADER:
        try:
            models.append(VaderModel())
            print("✓ VADER model loaded")
        except Exception as e:
            print(f"✗ VADER failed to load: {e}")
    else:
        print("✗ VADER not available (install with: pip install vaderSentiment)")
    
    # Transformers (Twitter RoBERTa)
    if HAS_TRANSFORMERS:
        try:
            models.append(TransformersModel("cardiffnlp/twitter-roberta-base-sentiment-latest"))
            print("✓ Transformers (Twitter RoBERTa) model loaded")
        except Exception as e:
            print(f"✗ Transformers failed to load: {e}")
    else:
        print("✗ Transformers not available (install with: pip install transformers torch)")
    
    # OpenAI models
    if HAS_OPENAI:
        try:
            models.append(OpenAIModel("gpt-3.5-turbo"))
            print("✓ OpenAI GPT-3.5-turbo model loaded")
        except Exception as e:
            print(f"✗ OpenAI GPT-3.5-turbo failed to load: {e}")
        try:
            models.append(OpenAIModel("gpt-4o"))
            print("✓ OpenAI GPT-4o model loaded")
        except Exception as e:
            print(f"✗ OpenAI GPT-4o failed to load: {e}")
        try:
            models.append(OpenAIModel("gpt-4o-mini"))
            print("✓ OpenAI GPT-4o-mini model loaded")
        except Exception as e:
            print(f"✗ OpenAI GPT-4o-mini failed to load: {e}")
    else:
        print("✗ OpenAI not available (configure OPENAI_API_KEY in backend/.env)")
    
    if not models:
        print("\nError: No models available. Please install at least one model library.")
        return
    
    print(f"\n{'='*80}")
    print(f"Running comparison with {len(models)} models...")
    print(f"{'='*80}\n")
    
    # Run comparison
    results = evaluator.compare_models(models)
    
    # Print results
    evaluator.print_results(results)
    
    # Save results to file
    results_file = os.path.join(os.path.dirname(__file__), '..', 'sentiment_comparison_results.json')
    with open(results_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {results_file}")

if __name__ == '__main__':
    main()

