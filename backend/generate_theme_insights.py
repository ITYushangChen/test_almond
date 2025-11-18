#!/usr/bin/env python3
"""
Script to generate AI insights for all base_themes and sub_themes
and save them to a static JSON file.

Usage:
    cd backend
    python generate_theme_insights.py
"""
import os
import sys
import json
import re
from collections import Counter
from dotenv import load_dotenv

# Load environment variables from .env file
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Try loading from backend/.env
    env_path = os.path.join(script_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Try loading from current directory
        load_dotenv()

# Add current directory to path to import modules
sys.path.insert(0, script_dir)

from supabase import create_client
from routes.ai_analysis import get_openai_client
from config import Config

# Stop words for keyword aggregation (combines generic + domain-specific terms)
BASE_STOP_WORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'have', 'has', 'had', 'was', 'were',
    'are', 'been', 'but', 'not', 'you', 'your', 'they', 'their', 'them', 'our', 'out', 'into',
    'about', 'just', 'very', 'much', 'more', 'than', 'also', 'can', 'will', 'would', 'could',
    'should', 'one', 'two', 'three', 'get', 'got', 'make', 'made', 'even', 'still', 'over',
    'well', 'per', 'each', 'every', 'across', 'because', 'while', 'when', 'where', 'what',
    'who', 'why', 'how', 'does', 'did', 'doing', 'done', 'other', 'another', 'such', 'like',
    'some', 'any', 'all', 'many', 'most', 'few', 'new', 'old'
}

CUSTOM_STOP_WORDS = {
    'rio', 'tinto', 'riotinto', 'rt', 'company', 'work', 'working', 'worked', 'role', 'job',
    'jobs', 'people', 'person', 'team', 'teams', 'employee', 'employees', 'staff', 'manager',
    'management', 'business', 'place', 'industry', 'site', 'sites', 'mine', 'mines', 'mining',
    'year', 'years', 'month', 'months', 'day', 'days', 'time', 'times', 'pros', 'cons',
    'advice', 'summary', 'review', 'reviews'
}

STOP_WORDS = BASE_STOP_WORDS | CUSTOM_STOP_WORDS
TOKEN_PATTERN = re.compile(r"[a-zA-Z]{3,}")
def get_supabase_client():
    """Create Supabase client without Flask context"""
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def get_all_themes():
    """Get all unique base_themes and sub_themes from database"""
    supabase = get_supabase_client()
    
    # Get all themes
    response = supabase.table('cb').select('base_theme,sub_theme').limit(100000).execute()
    data = response.data
    
    exclude_values = ['others', 'stock_market']
    
    # Get unique base_themes
    base_themes = sorted(set(
        d.get('base_theme') for d in data 
        if d.get('base_theme') and d.get('base_theme') not in exclude_values
    ))
    
    # Get unique sub_themes
    sub_themes = sorted(set(
        d.get('sub_theme') for d in data 
        if d.get('sub_theme') and d.get('sub_theme') not in exclude_values
    ))
    
    return base_themes, sub_themes

def _select_diverse_samples(contents, max_samples=40):
    """
    Select evenly spaced samples so that all comments are represented
    without sending every comment to the LLM.
    """
    if len(contents) <= max_samples:
        return contents
    
    samples = []
    step = len(contents) / max_samples
    idx = 0.0
    used = set()
    
    for _ in range(max_samples):
        pos = int(idx)
        # Ensure we don't reuse the same index
        while pos in used and pos < len(contents) - 1:
            pos += 1
        samples.append(contents[pos])
        used.add(pos)
        idx += step
    
    return samples

def _build_prompt_input(contents, sentiment_label, max_samples=40):
    """
    Build condensed input covering all comments via keyword stats + diverse samples.
    """
    total = len(contents)
    if total == 0:
        return f"{sentiment_label.title()} Comments: None"
    
    # Keyword aggregation over all comments
    tokens = []
    for text in contents:
        tokens.extend([
            token.lower()
            for token in TOKEN_PATTERN.findall(text.lower())
            if token.lower() not in STOP_WORDS
        ])
    
    keyword_counts = Counter(tokens).most_common(12)
    keywords_str = ', '.join(f"{word}({count})" for word, count in keyword_counts) or "N/A"
    
    avg_word_len = sum(len(comment.split()) for comment in contents) / total
    
    representative_samples = _select_diverse_samples(contents, max_samples=max_samples)
    sample_lines = '\n'.join([
        f"- {comment.strip()[:300]}{'...' if len(comment.strip()) > 300 else ''}"
        for comment in representative_samples
    ])
    
    return (
        f"{sentiment_label.title()} Comments Summary Input:\n"
        f"Total Comments: {total}\n"
        f"Average Comment Length (words): {avg_word_len:.1f}\n"
        f"Top Keywords (covering entire dataset): {keywords_str}\n"
        f"Diverse Sample (evenly spaced across all comments):\n"
        f"{sample_lines}"
    )

def get_theme_content(theme_type, theme_name):
    """Get content for a specific theme"""
    supabase = get_supabase_client()
    
    query = supabase.table('cb').select('content,sentiment,likes')
    
    # Filter by theme type
    if theme_type == 'base_theme':
        query = query.eq('base_theme', theme_name)
    else:
        query = query.eq('sub_theme', theme_name)
    
    # Exclude others and stock_market
    query = query.neq('base_theme', 'others')
    query = query.neq('base_theme', 'stock_market')
    query = query.neq('sub_theme', 'others')
    
    query = query.limit(1000)
    response = query.execute()
    all_data = response.data
    
    # Separate positive and negative content
    positive_contents = []
    negative_contents = []
    
    for item in all_data:
        content = item.get('content', '')
        if not content:
            continue
            
        sentiment = item.get('sentiment')
        likes = item.get('likes', 0) or 0
        
        # Determine if positive or negative
        is_positive = False
        is_negative = False
        
        if sentiment == 'positive':
            is_positive = True
        elif sentiment == 'negative':
            is_negative = True
        else:
            # Fallback to likes-based proxy
            if likes > 5:
                is_positive = True
            elif likes < -5:
                is_negative = True
        
        if is_positive:
            positive_contents.append(content)
        elif is_negative:
            negative_contents.append(content)
    
    return positive_contents, negative_contents

def generate_insights_for_theme(theme_type, theme_name, positive_contents, negative_contents, client):
    """Generate AI insights for a theme"""
    insights = {
        'positive_summary': '',
        'negative_summary': '',
        'positive_recommendations': [],
        'negative_recommendations': []
    }
    
    # Generate positive insights
    if positive_contents:
        positive_text = _build_prompt_input(positive_contents, "positive")
        
        positive_prompt = f"""Analyze the aggregated positive feedback about "{theme_name}" (theme type: {theme_type}).

{positive_text}

Requirements:
1. Summary: Directly state specific examples of advantages mentioned in the comments. Do NOT use phrases like "The comments reflect..." or "The comments highlight...". Instead, directly list concrete examples (e.g., "Employees appreciate flexible work schedules and mentorship programs"). Keep it concise, 2-3 sentences maximum.
2. Recommendations: Provide 1-2 short phrases (not full sentences) summarizing improvement directions to maintain/enhance these positive aspects.

Format your response as JSON:
{{
  "summary": "Direct examples of advantages from comments",
  "recommendations": ["short phrase 1", "short phrase 2"]
}}

Example format:
{{
  "summary": "Employees value flexible FIFO schedules allowing more leisure time. They appreciate competitive compensation packages and union protections.",
  "recommendations": ["Maintain flexible work arrangements", "Continue competitive benefits"]
}}"""
        
        try:
            ai_response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a data analyst. Always respond in valid JSON format. Be direct and concise. Avoid generic introductory phrases."},
                    {"role": "user", "content": positive_prompt}
                ],
                temperature=0.5,
                max_tokens=450
            )
            
            response_text = ai_response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                positive_data = json.loads(json_match.group())
                insights['positive_summary'] = positive_data.get('summary', '')
                insights['positive_recommendations'] = positive_data.get('recommendations', [])[:2]  # Max 2 recommendations
            else:
                insights['positive_summary'] = response_text[:200]
        except Exception as e:
            print(f"Error generating positive insights for {theme_type} {theme_name}: {e}")
            insights['positive_summary'] = 'Unable to generate insights at this time.'
    
    # Generate negative insights
    if negative_contents:
        negative_text = _build_prompt_input(negative_contents, "negative")
        
        negative_prompt = f"""Analyze the aggregated negative feedback about "{theme_name}" (theme type: {theme_type}).

{negative_text}

Requirements:
1. Summary: Directly state specific examples of problems or concerns mentioned in the comments. Do NOT use phrases like "The comments reflect..." or "The main concerns revolve around...". Instead, directly list concrete examples (e.g., "Employees report prolonged hiring processes taking months. Job requirements for graduate roles are unrealistic."). Keep it concise, 2-3 sentences maximum.
2. Recommendations: Provide 1-2 short phrases (not full sentences) summarizing improvement directions to address these concerns.

Format your response as JSON:
{{
  "summary": "Direct examples of problems from comments",
  "recommendations": ["short phrase 1", "short phrase 2"]
}}

Example format:
{{
  "summary": "Hiring processes take 3-6 months with unclear timelines. Job descriptions require 5+ years experience for graduate positions.",
  "recommendations": ["Streamline hiring timeline", "Align job requirements with role level"]
}}"""
        
        try:
            ai_response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a data analyst. Always respond in valid JSON format. Be direct and concise. Avoid generic introductory phrases."},
                    {"role": "user", "content": negative_prompt}
                ],
                temperature=0.5,
                max_tokens=450
            )
            
            response_text = ai_response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                negative_data = json.loads(json_match.group())
                insights['negative_summary'] = negative_data.get('summary', '')
                insights['negative_recommendations'] = negative_data.get('recommendations', [])[:2]  # Max 2 recommendations
            else:
                insights['negative_summary'] = response_text[:200]
        except Exception as e:
            print(f"Error generating negative insights for {theme_type} {theme_name}: {e}")
            insights['negative_summary'] = 'Unable to generate insights at this time.'
    
    return insights

def main():
    """Main function to generate all insights"""
    # Check OpenAI API key
    if not Config.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not configured!")
        sys.exit(1)
    
    print("Fetching all themes from database...")
    base_themes, sub_themes = get_all_themes()
    print(f"Found {len(base_themes)} base_themes and {len(sub_themes)} sub_themes")
    
    client = get_openai_client()
    all_insights = {}
    
    # Process base_themes
    print("\nProcessing base_themes...")
    for i, theme in enumerate(base_themes, 1):
        print(f"[{i}/{len(base_themes)}] Processing base_theme: {theme}")
        try:
            positive_contents, negative_contents = get_theme_content('base_theme', theme)
            
            if not positive_contents and not negative_contents:
                print(f"  No content found for {theme}, skipping...")
                continue
            
            insights = generate_insights_for_theme('base_theme', theme, positive_contents, negative_contents, client)
            all_insights[f"base_theme_{theme}"] = insights
            print(f"  ✓ Generated insights for {theme}")
        except Exception as e:
            print(f"  ✗ Error processing {theme}: {e}")
            import traceback
            traceback.print_exc()
    
    # Process sub_themes
    print("\nProcessing sub_themes...")
    for i, theme in enumerate(sub_themes, 1):
        print(f"[{i}/{len(sub_themes)}] Processing sub_theme: {theme}")
        try:
            positive_contents, negative_contents = get_theme_content('sub_theme', theme)
            
            if not positive_contents and not negative_contents:
                print(f"  No content found for {theme}, skipping...")
                continue
            
            insights = generate_insights_for_theme('sub_theme', theme, positive_contents, negative_contents, client)
            all_insights[f"sub_theme_{theme}"] = insights
            print(f"  ✓ Generated insights for {theme}")
        except Exception as e:
            print(f"  ✗ Error processing {theme}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save to JSON file
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    output_file = os.path.join(data_dir, 'theme_insights.json')
    
    print(f"\nSaving insights to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_insights, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Successfully generated insights for {len(all_insights)} themes")
    print(f"✓ Saved to {output_file}")

if __name__ == '__main__':
    main()

