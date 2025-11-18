# -*- coding: utf-8 -*-
"""
Detect the language of content in Supabase posts table
and update the language column
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from langdetect import detect, detect_langs, LangDetectException
from typing import Optional

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def detect_language(text: str) -> Optional[str]:
    """
    Detect text language
    
    Returns:
        Language code (e.g., 'en', 'zh-cn', 'ja', etc.)
        Returns None if detection fails
    """
    if not text or not text.strip():
        return None
    
    try:
        # Use langdetect to detect language
        language = detect(text)
        return language
    except LangDetectException as e:
        print(f"⚠️ Language detection failed: {e}")
        return None


def detect_language_with_confidence(text: str) -> tuple:
    """
    Detect text language and return confidence
    
    Returns:
        (language_code, confidence)
    """
    if not text or not text.strip():
        return (None, 0.0)
    
    try:
        # detect_langs returns all possible languages and their probabilities
        results = detect_langs(text)
        if results:
            # Return the language with the highest probability
            top_result = results[0]
            return (top_result.lang, top_result.prob)
        return (None, 0.0)
    except LangDetectException as e:
        print(f"⚠️ Language detection failed: {e}")
        return (None, 0.0)


def get_language_name(lang_code: str) -> str:
    """
    Convert language code to language name
    """
    language_map = {
        'en': 'English',
        'zh-cn': 'Chinese (Simplified)',
        'zh-tw': 'Chinese (Traditional)',
        'ja': 'Japanese',
        'ko': 'Korean',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'nl': 'Dutch',
        'sv': 'Swedish',
        'no': 'Norwegian',
        'da': 'Danish',
        'fi': 'Finnish',
        'pl': 'Polish',
        'tr': 'Turkish',
        'vi': 'Vietnamese',
        'th': 'Thai',
        'id': 'Indonesian',
        'ms': 'Malay',
    }
    return language_map.get(lang_code, lang_code.upper())


def fetch_all_posts(batch_size=1000):
    """
    Fetch all posts in batches
    """
    print("📥 Fetching posts data...")
    
    all_posts = []
    offset = 0
    
    while True:
        # Paginated query
        response = supabase.table("cb") \
            .select("id, content") \
            .range(offset, offset + batch_size - 1) \
            .execute()
        
        posts = response.data
        
        if not posts:
            break
        
        all_posts.extend(posts)
        offset += batch_size
        print(f"   Fetched {len(all_posts)} records...")
        
        if len(posts) < batch_size:
            break
    
    print(f"✅ Total fetched {len(all_posts)} posts")
    return all_posts


def update_post_language(post_id: str, language: str, confidence: float = None):
    """
    Update language information for a single post
    """
    try:
        update_data = {"language": language}
        
        # If needed, can also store confidence
        # update_data["language_confidence"] = confidence
        
        supabase.table("cb").update(update_data).eq("id", post_id).execute()
        return True
    except Exception as e:
        print(f"❌ Update failed (ID: {post_id}): {e}")
        return False


def process_posts_language_detection(batch_size=100):
    """
    Batch process language detection for posts
    """
    print("\n" + "="*60)
    print("🌍 Starting language detection for posts")
    print("="*60)
    
    # Fetch all posts
    posts = fetch_all_posts()
    
    if not posts:
        print("⚠️ No posts found")
        return
    
    print(f"\n🔍 Starting language detection...")
    
    success_count = 0
    fail_count = 0
    language_stats = {}
    
    for i, post in enumerate(posts, 1):
        post_id = post.get('id')
        
        # Prefer content, if empty use post_title + post_selftext
        text = post.get('content') or ''
        if not text.strip():
            title = post.get('post_title') or ''
            selftext = post.get('post_selftext') or ''
            text = f"{title} {selftext}".strip()
        
        if not text:
            print(f"   ⚠️ [{i}/{len(posts)}] Skipped (no text content): {post_id}")
            fail_count += 1
            continue
        
        # Detect language
        lang_code, confidence = detect_language_with_confidence(text)
        
        if lang_code:
            # Update database
            if update_post_language(post_id, lang_code, confidence):
                success_count += 1
                language_stats[lang_code] = language_stats.get(lang_code, 0) + 1
                
                if i % batch_size == 0:
                    print(f"   ✅ [{i}/{len(posts)}] Processed {success_count} posts")
            else:
                fail_count += 1
        else:
            print(f"   ⚠️ [{i}/{len(posts)}] Language detection failed: {post_id}")
            fail_count += 1
    
    # Print statistics report
    print("\n" + "="*60)
    print("📊 Processing Complete - Statistics Report")
    print("="*60)
    print(f"\nTotal: {len(posts)} posts")
    print(f"✅ Succeeded: {success_count} posts")
    print(f"❌ Failed: {fail_count} posts")
    
    print(f"\n🌍 Language Distribution:")
    # Sort by count
    sorted_langs = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)
    for lang_code, count in sorted_langs:
        lang_name = get_language_name(lang_code)
        percentage = (count / success_count * 100) if success_count > 0 else 0
        print(f"   {lang_name:20s} ({lang_code}): {count:4d} ({percentage:.1f}%)")
    
    print("\n✅ Language detection completed!")


def test_language_detection():
    """
    Test language detection functionality
    """
    print("🧪 Testing language detection functionality\n")
    
    test_texts = [
        "This is an English text about Rio Tinto mining company.",
        "这是一段关于力拓公司的中文文本。",
        "これはリオ・ティントに関する日本語のテキストです。",
        "Este es un texto en español sobre Rio Tinto.",
        "C'est un texte en français sur Rio Tinto.",
        "Это русский текст о компании Rio Tinto.",
    ]
    
    for text in test_texts:
        lang_code, confidence = detect_language_with_confidence(text)
        lang_name = get_language_name(lang_code) if lang_code else "Unknown"
        print(f"Text: {text[:50]}...")
        print(f"Language: {lang_name} ({lang_code})")
        print(f"Confidence: {confidence:.2%}\n")


def main():
    """
    Main function
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        test_language_detection()
    else:
        # Normal processing mode
        process_posts_language_detection()


if __name__ == "__main__":
    main()

