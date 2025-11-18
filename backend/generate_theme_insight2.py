#!/usr/bin/env python3
"""
Advanced Script to generate AI insights for all base_themes and sub_themes.

3-step pipeline per theme & sentiment:
1. Local summaries: summarize each comment into 1–2 bullet points.
2. Clustering: embed summaries and cluster into sub-topics.
3. Insight: generate final JSON insights based on cluster structure.

Usage:
    cd backend
    python generate_theme_insights_advanced.py
"""

import os
import sys
import json
import re
import math
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

from dotenv import load_dotenv

# ------------------ Env & imports ------------------

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from ../.env or ./.env
env_path = os.path.join(script_dir, '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    alt_env = os.path.join(script_dir, '.env')
    if os.path.exists(alt_env):
        load_dotenv(alt_env)
    else:
        load_dotenv()

# Allow importing backend modules
sys.path.insert(0, script_dir)

from supabase import create_client  # type: ignore
from routes.ai_analysis import get_openai_client  # type: ignore
from config import Config  # type: ignore

try:
    from sklearn.cluster import KMeans
except ImportError:
    KMeans = None  # We'll fallback to "single cluster" if sklearn is missing

from openai import OpenAI

# ------------------ Configurable constants ------------------

# Max number of comments fetched per theme per sentiment
MAX_COMMENTS_PER_THEME = 600

# Max number of comments to summarize per theme & sentiment
MAX_SUMMARIES_PER_THEME = 300

# Clustering parameters
MIN_CLUSTER_SUMMARIES = 12           # below this → no clustering, single cluster
MIN_POINTS_PER_CLUSTER = 18
MAX_CLUSTERS = 5

# Embedding model (fallback to text-embedding-3-small if not in Config)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

# ------------------ Stopwords & tokenisation ------------------

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

# ------------------ Helpers ------------------

def get_supabase_client():
    """Create Supabase client without Flask context."""
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def get_openai_embedding_client() -> OpenAI:
    """Return an OpenAI client for embeddings & chat."""
    if hasattr(Config, "OPENAI_API_KEY") and Config.OPENAI_API_KEY:
        return OpenAI(api_key=Config.OPENAI_API_KEY)
    # fallback: let get_openai_client handle key
    return get_openai_client()

def get_embedding_model_name() -> str:
    return getattr(Config, "OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

def get_all_themes() -> Tuple[List[str], List[str]]:
    """Get all unique base_themes and sub_themes from database."""
    supabase = get_supabase_client()
    resp = supabase.table('cb').select('base_theme,sub_theme').limit(100000).execute()
    data = resp.data or []

    exclude_values = {'others', 'stock_market', None, ''}

    base_themes = sorted({
        d.get('base_theme') for d in data
        if d.get('base_theme') not in exclude_values
    })

    sub_themes = sorted({
        d.get('sub_theme') for d in data
        if d.get('sub_theme') not in exclude_values
    })

    return base_themes, sub_themes

def get_theme_content(theme_type: str, theme_name: str) -> Tuple[List[str], List[str]]:
    """
    Get raw contents for a specific theme, split into positive and negative lists.
    Uses existing 'sentiment' column and falls back to 'likes' heuristic.
    """
    supabase = get_supabase_client()

    query = supabase.table('cb').select('content,sentiment,likes')

    if theme_type == 'base_theme':
        query = query.eq('base_theme', theme_name)
    else:
        query = query.eq('sub_theme', theme_name)

    # Exclude generic/irrelevant buckets
    query = (query
        .neq('base_theme', 'others')
        .neq('base_theme', 'stock_market')
        .neq('sub_theme', 'others')
        .limit(MAX_COMMENTS_PER_THEME)
    )

    resp = query.execute()
    all_data = resp.data or []

    pos = []
    neg = []

    for item in all_data:
        content = (item.get('content') or '').strip()
        if not content:
            continue

        sentiment = (item.get('sentiment') or '').lower()
        likes = item.get('likes', 0) or 0

        is_positive = sentiment == 'positive'
        is_negative = sentiment == 'negative'

        if not is_positive and not is_negative:
            # Fallback heuristic based on likes (can be tuned)
            if likes > 5:
                is_positive = True
            elif likes < -5:
                is_negative = True

        if is_positive:
            pos.append(content)
        elif is_negative:
            neg.append(content)

    return pos, neg

def _evenly_sample(items: List[str], max_samples: int) -> List[str]:
    """Evenly spaced sampling over list indices."""
    if len(items) <= max_samples:
        return items[:]
    samples = []
    step = len(items) / max_samples
    idx = 0.0
    used = set()
    for _ in range(max_samples):
        pos = int(idx)
        while pos in used and pos < len(items) - 1:
            pos += 1
        samples.append(items[pos])
        used.add(pos)
        idx += step
    return samples

# ------------------ Step 1: Comment-level Local Summaries ------------------

def summarize_comments(
    comments: List[str],
    client: OpenAI,
    sentiment_label: str,
    theme_name: str,
    theme_type: str,
    max_summaries: int = MAX_SUMMARIES_PER_THEME
) -> List[str]:
    """
    Summarize each comment into 1–2 bullet points.
    Returns a list of short summary lines (used for clustering & insight).
    """
    if not comments:
        return []

    # Sample if too many
    comments_to_use = _evenly_sample(comments, max_summaries)

    summaries: List[str] = []

    print(f"    - Summarizing {len(comments_to_use)} {sentiment_label} comments for {theme_type} '{theme_name}'")

    for idx, text in enumerate(comments_to_use, 1):
        prompt = f"""Summarise the following employee feedback into 1–2 bullet points.
Focus on concrete issues, situations, or positive aspects. Avoid generic phrases.

Feedback:
\"\"\"{text[:1000]}\"\"\"

Output format:
- bullet point 1
- bullet point 2 (optional)
"""

        try:
            resp = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a concise workplace culture analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=120,
            )
            content = (resp.choices[0].message.content or "").strip()
            # Split into lines, keep lines starting with "-"
            lines = [ln.strip() for ln in content.splitlines() if ln.strip().startswith("-")]
            if not lines:
                # fallback: just use first 150 chars
                lines = [f"- {text[:150]}"]
            summaries.extend(lines)
        except Exception as e:
            print(f"      ⚠️ Summary error on comment {idx}: {e}")
            # Fallback: rough truncation
            summaries.append(f"- {text[:150]}")

        if idx % 20 == 0:
            print(f"      ... {idx}/{len(comments_to_use)} summarized")

    return summaries

# ------------------ Step 2: Embedding & Clustering ------------------

def embed_texts(texts: List[str], client: OpenAI) -> List[List[float]]:
    """Get embeddings for a list of texts."""
    if not texts:
        return []
    model_name = get_embedding_model_name()
    resp = client.embeddings.create(
        model=model_name,
        input=texts,
    )
    return [d.embedding for d in resp.data]

def keywords_from_texts(texts: List[str], top_k: int = 8) -> List[str]:
    """Extract top keywords from a list of texts using simple token frequency."""
    tokens = []
    for t in texts:
        for token in TOKEN_PATTERN.findall(t.lower()):
            if token not in STOP_WORDS:
                tokens.append(token)
    counts = Counter(tokens).most_common(top_k)
    return [w for w, _ in counts]

def cluster_summaries(
    summaries: List[str],
    embeddings: List[List[float]],
) -> List[Dict]:
    """
    Cluster summaries into sub-topics using KMeans (if available).
    Returns a list of cluster dicts:
    {
      "cluster_id": int,
      "size": int,
      "summaries": [...],
      "example_summaries": [...],
      "keywords": [...]
    }
    """
    n = len(summaries)
    if n == 0:
        return []

    # If too few points or sklearn missing → single cluster
    if (KMeans is None) or (n < MIN_CLUSTER_SUMMARIES):
        return [{
            "cluster_id": 0,
            "size": n,
            "summaries": summaries,
            "example_summaries": summaries[:5],
            "keywords": keywords_from_texts(summaries, top_k=8),
        }]

    # Choose K based on data size
    k = max(2, min(MAX_CLUSTERS, n // MIN_POINTS_PER_CLUSTER))
    if k <= 1:
        k = 2
    if k > n:
        k = n

    try:
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
    except Exception as e:
        print(f"      ⚠️ KMeans failed ({e}), falling back to single cluster")
        return [{
            "cluster_id": 0,
            "size": n,
            "summaries": summaries,
            "example_summaries": summaries[:5],
            "keywords": keywords_from_texts(summaries, top_k=8),
        }]

    clusters: Dict[int, List[str]] = defaultdict(list)
    for summary, lbl in zip(summaries, labels):
        clusters[int(lbl)].append(summary)

    cluster_list = []
    for cid, items in clusters.items():
        cluster_list.append({
            "cluster_id": cid,
            "size": len(items),
            "summaries": items,
            "example_summaries": items[:5],
            "keywords": keywords_from_texts(items, top_k=8),
        })

    # Sort by size descending
    cluster_list.sort(key=lambda c: c["size"], reverse=True)
    return cluster_list

# ------------------ Step 3: Generate Insight from Cluster Structure ------------------

def build_cluster_prompt_block(clusters: List[Dict]) -> str:
    """Build a text block summarising clusters for the final GPT insight."""
    lines = []
    for c in clusters:
        cid = c["cluster_id"]
        size = c["size"]
        kws = c["keywords"]
        examples = c["example_summaries"]

        lines.append(f"Sub-topic {cid} (approx. {size} comments)")
        lines.append(f"  Keywords: {', '.join(kws) if kws else 'N/A'}")
        lines.append("  Example summaries:")
        for ex in examples[:3]:
            lines.append(f"    {ex}")
        lines.append("")  # blank line between clusters

    return "\n".join(lines)

def generate_theme_insight_from_clusters(
    theme_type: str,
    theme_name: str,
    sentiment_label: str,
    clusters: List[Dict],
    total_comments: int,
    client: OpenAI,
) -> Dict:
    """
    Use GPT to generate final summary & recommendations from cluster information.
    Returns dict: {"summary": str, "recommendations": [..]}.
    """
    if not clusters or total_comments == 0:
        return {
            "summary": "",
            "recommendations": []
        }

    cluster_block = build_cluster_prompt_block(clusters)

    prompt = f"""You are analyzing {sentiment_label} employee feedback for the theme "{theme_name}" (theme type: {theme_type}).

There are approximately {total_comments} {sentiment_label} comments in total.
They have been clustered into several sub-topics. Each sub-topic includes rough size estimates, top keywords, and example bullet-point summaries:

{cluster_block}

Requirements:
1. Summary:
   - Directly state specific examples of {sentiment_label} patterns.
   - Do NOT use meta phrases like "the comments reflect" or "people say".
   - Write 2–3 concise sentences with concrete, stakeholder-friendly descriptions.
   - Include specific numbers, timeframes, or concrete examples when mentioned in the clusters.
2. Recommendations:
   - Provide 1–3 actionable recommendations that are SPECIFIC and MEASURABLE.
   - Each recommendation should:
     * Address a concrete issue or opportunity identified in the clusters
     * Be specific enough that someone could implement it (e.g., "Reduce hiring process from 3-6 months to 4-6 weeks" instead of "Improve hiring")
     * Include a target outcome or metric when possible (e.g., "Increase manager feedback frequency to monthly" instead of "More feedback")
   - Avoid vague phrases like "improve", "enhance", "better" without specifics.
   - Good examples: "Implement 30-day hiring timeline with weekly status updates", "Create structured mentorship program pairing senior staff with new hires", "Establish quarterly performance reviews with clear promotion criteria"
   - Bad examples: "Improve communication", "Better training", "More support"

Output JSON in this exact format:
{{
  "summary": "Direct, concrete description of the main {sentiment_label} patterns",
  "recommendations": ["short phrase 1", "short phrase 2"]
}}"""

    try:
        resp = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior workplace culture analyst. "
                        "Always respond with valid JSON only. Be concrete and avoid meta-commentary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            data = json.loads(json_match.group())
            summary = data.get("summary", "").strip()
            recs = data.get("recommendations") or []
            if isinstance(recs, list):
                recs = [str(r).strip() for r in recs if str(r).strip()]
            else:
                recs = [str(recs).strip()]
            return {
                "summary": summary,
                "recommendations": recs[:3],
            }
        # fallback: use raw text if JSON parsing fails
        return {
            "summary": text[:300],
            "recommendations": [],
        }
    except Exception as e:
        print(f"    ⚠️ Insight generation error for {theme_type} {theme_name} ({sentiment_label}): {e}")
        return {
            "summary": "",
            "recommendations": [],
        }

# ------------------ Orchestrator per theme ------------------

def generate_insights_for_theme(
    theme_type: str,
    theme_name: str,
    pos_contents: List[str],
    neg_contents: List[str],
    client: OpenAI,
) -> Dict:
    """
    Full 3-step pipeline for a single theme:
    - Summarize comments
    - Cluster summaries
    - Generate final insight JSON
    """
    insights = {
        "positive_summary": "",
        "negative_summary": "",
        "positive_recommendations": [],
        "negative_recommendations": [],
    }

    # --- Positive side ---
    if pos_contents:
        pos_summaries = summarize_comments(
            pos_contents, client,
            sentiment_label="positive",
            theme_name=theme_name,
            theme_type=theme_type,
        )
        if pos_summaries:
            pos_embeddings = embed_texts(pos_summaries, client)
            pos_clusters = cluster_summaries(pos_summaries, pos_embeddings)
            pos_insight = generate_theme_insight_from_clusters(
                theme_type=theme_type,
                theme_name=theme_name,
                sentiment_label="positive",
                clusters=pos_clusters,
                total_comments=len(pos_contents),
                client=client,
            )
            insights["positive_summary"] = pos_insight.get("summary", "")
            insights["positive_recommendations"] = pos_insight.get("recommendations", [])

    # --- Negative side ---
    if neg_contents:
        neg_summaries = summarize_comments(
            neg_contents, client,
            sentiment_label="negative",
            theme_name=theme_name,
            theme_type=theme_type,
        )
        if neg_summaries:
            neg_embeddings = embed_texts(neg_summaries, client)
            neg_clusters = cluster_summaries(neg_summaries, neg_embeddings)
            neg_insight = generate_theme_insight_from_clusters(
                theme_type=theme_type,
                theme_name=theme_name,
                sentiment_label="negative",
                clusters=neg_clusters,
                total_comments=len(neg_contents),
                client=client,
            )
            insights["negative_summary"] = neg_insight.get("summary", "")
            insights["negative_recommendations"] = neg_insight.get("recommendations", [])

    return insights

# ------------------ Main script ------------------

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate AI insights for themes using 3-step pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with first 2 base themes
  python generate_theme_insight2.py --type base --limit 2
  
  # Test with first 1 sub theme
  python generate_theme_insight2.py --type sub --limit 1
  
  # Test specific theme
  python generate_theme_insight2.py --type base --theme "work_life_balance"
  
  # Process all themes (default)
  python generate_theme_insight2.py
        """
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["base", "sub", "all"],
        default="all",
        help="Process base_themes, sub_themes, or all (default: all)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of themes to process (for testing)"
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Process a specific theme by name"
    )
    
    args = parser.parse_args()
    
    if not getattr(Config, "OPENAI_API_KEY", None):
        print("Error: OPENAI_API_KEY not configured in Config.")
        sys.exit(1)

    base_themes, sub_themes = get_all_themes()
    print(f"Found {len(base_themes)} base_themes and {len(sub_themes)} sub_themes")

    client = get_openai_embedding_client()
    all_insights: Dict[str, Dict] = {}

    # Determine which themes to process
    themes_to_process = []
    
    if args.theme:
        # Process specific theme
        if args.type == "base" or args.type == "all":
            if args.theme in base_themes:
                themes_to_process.append(("base_theme", args.theme))
            else:
                print(f"Warning: '{args.theme}' not found in base_themes")
        if args.type == "sub" or args.type == "all":
            if args.theme in sub_themes:
                themes_to_process.append(("sub_theme", args.theme))
            else:
                print(f"Warning: '{args.theme}' not found in sub_themes")
    else:
        # Process based on type and limit
        if args.type == "base" or args.type == "all":
            themes_list = base_themes[:args.limit] if args.limit else base_themes
            themes_to_process.extend([("base_theme", t) for t in themes_list])
        
        if args.type == "sub" or args.type == "all":
            themes_list = sub_themes[:args.limit] if args.limit else sub_themes
            themes_to_process.extend([("sub_theme", t) for t in themes_list])

    print(f"\nWill process {len(themes_to_process)} theme(s)")

    # Process themes
    for idx, (theme_type, theme_name) in enumerate(themes_to_process, 1):
        print(f"\n[{idx}/{len(themes_to_process)}] {theme_type}: {theme_name}")
        try:
            pos, neg = get_theme_content(theme_type, theme_name)
            if not pos and not neg:
                print(f"  - No content found, skipping.")
                continue
            
            print(f"  Found {len(pos)} positive and {len(neg)} negative comments")
            insights = generate_insights_for_theme(theme_type, theme_name, pos, neg, client)
            all_insights[f"{theme_type}_{theme_name}"] = insights
            print(f"  ✓ Done.")
            
            # Print preview of results
            print(f"\n  Preview:")
            if insights.get("positive_summary"):
                print(f"    Positive: {insights['positive_summary'][:150]}...")
            if insights.get("positive_recommendations"):
                print(f"    Recommendations: {insights['positive_recommendations']}")
            if insights.get("negative_summary"):
                print(f"    Negative: {insights['negative_summary'][:150]}...")
            if insights.get("negative_recommendations"):
                print(f"    Recommendations: {insights['negative_recommendations']}")
        except Exception as e:
            print(f"  ✗ Error on {theme_name}: {e}")
            import traceback
            traceback.print_exc()

    # Save to JSON
    data_dir = os.path.join(script_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "theme_insights_advanced.json")

    print(f"\nSaving advanced insights to {out_path} ...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_insights, f, indent=2, ensure_ascii=False)

    print(f"✓ Successfully generated advanced insights for {len(all_insights)} themes")
    print(f"✓ Saved to {out_path}")

if __name__ == "__main__":
    main()
