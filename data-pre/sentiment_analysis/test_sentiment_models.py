"""
Script to randomly sample 50 contents from cb table for sentiment analysis testing
"""
import os
import sys
import json
import random
from supabase import create_client

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
from config import Config

def get_random_samples(n=50):
    """Get n random samples from cb table with content
    
    Filters:
    - base_theme and sub_theme are not null
    - base_theme and sub_theme are not 'others' or 'stock_market'
    - content is not empty
    """
    # Create Supabase client directly (not using Flask context)
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    # Get all IDs that match the criteria
    print("Fetching records that match criteria...")
    query = supabase.table('cb').select('id,base_theme,sub_theme,content')
    # Filter out 'others' and 'stock_market' (Supabase query)
    query = query.neq('base_theme', 'others')
    query = query.neq('base_theme', 'stock_market')
    query = query.neq('sub_theme', 'others')
    query = query.neq('sub_theme', 'stock_market')
    query = query.limit(100000)
    
    response = query.execute()
    
    # Filter in Python to ensure:
    # - base_theme and sub_theme are not null
    # - base_theme and sub_theme are not empty
    # - content is not empty
    # (Supabase may not handle null filtering well, so we do it in Python)
    valid_records = []
    for item in response.data:
        base_theme = item.get('base_theme')
        sub_theme = item.get('sub_theme')
        content = item.get('content', '')
        
        # Validate: all fields must be non-null and non-empty
        if (base_theme and 
            sub_theme and 
            base_theme.strip() != '' and 
            sub_theme.strip() != '' and
            base_theme not in ['others', 'stock_market'] and
            sub_theme not in ['others', 'stock_market'] and
            content and 
            len(content.strip()) > 0):
            valid_records.append(item['id'])
    
    print(f"Found {len(valid_records)} valid records")
    
    if len(valid_records) < n:
        print(f"Warning: Only {len(valid_records)} valid records available, requesting all")
        n = len(valid_records)
    
    # Randomly sample from valid records
    random_ids = random.sample(valid_records, min(n, len(valid_records)))
    
    # Fetch the actual records
    print(f"Fetching {len(random_ids)} random records...")
    samples = []
    for record_id in random_ids:
        try:
            response = supabase.table('cb').select('*').eq('id', record_id).limit(1).execute()
            if response.data:
                record = response.data[0]
                # Double-check criteria
                base_theme = record.get('base_theme')
                sub_theme = record.get('sub_theme')
                content = record.get('content', '')
                
                if (base_theme and 
                    sub_theme and 
                    base_theme not in ['others', 'stock_market'] and
                    sub_theme not in ['others', 'stock_market'] and
                    content and 
                    len(content.strip()) > 0):
                    samples.append(record)
        except Exception as e:
            print(f"Error fetching record {record_id}: {e}")
            continue
    
    return samples[:n]

def save_test_set(samples, filename='sentiment_test_set.json'):
    """Save test set to JSON file"""
    # Prepare data for saving
    test_data = []
    for sample in samples:
        test_data.append({
            'id': sample.get('id'),
            'content': sample.get('content', ''),
            'sentiment': sample.get('sentiment'),  # Current sentiment (may be null)
            'likes': sample.get('likes', 0),
            'base_theme': sample.get('base_theme'),
            'sub_theme': sample.get('sub_theme'),
            'date': sample.get('date'),
            'source': sample.get('source'),
            'language': sample.get('language')
        })
    
    # Save in data-pre directory
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(test_data)} samples to {filepath}")
    return test_data

def load_test_set(filename='sentiment_test_set.json'):
    """Load test set from JSON file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == '__main__':
    print("Fetching random samples from cb table...")
    samples = get_random_samples(50)
    
    if not samples:
        print("No samples found. Make sure cb table has records with content.")
        exit(1)
    
    print(f"✓ Retrieved {len(samples)} samples")
    
    # Save to file
    test_set = save_test_set(samples)
    
    # Print summary
    print("\n" + "="*60)
    print("Test Set Summary:")
    print("="*60)
    print(f"Total samples: {len(test_set)}")
    
    # Count by sentiment
    sentiment_counts = {}
    for item in test_set:
        sent = item.get('sentiment') or 'null'
        sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1
    
    print(f"\nSentiment distribution:")
    for sentiment, count in sentiment_counts.items():
        print(f"  {sentiment}: {count}")
    
    # Count by likes
    likes_positive = sum(1 for item in test_set if item.get('likes', 0) > 0)
    likes_negative = sum(1 for item in test_set if item.get('likes', 0) < 0)
    likes_neutral = sum(1 for item in test_set if item.get('likes', 0) == 0)
    
    print(f"\nLikes distribution (proxy for sentiment):")
    print(f"  Positive (likes > 0): {likes_positive}")
    print(f"  Negative (likes < 0): {likes_negative}")
    print(f"  Neutral (likes = 0): {likes_neutral}")
    
    print(f"\n✓ Test set saved to: data-pre/sentiment_test_set.json")
    print("\nNext steps:")
    print("1. Manually label the sentiment for each sample (or use current sentiment if available)")
    print("2. Run different sentiment analysis models on this test set")
    print("3. Compare accuracy of different models")

