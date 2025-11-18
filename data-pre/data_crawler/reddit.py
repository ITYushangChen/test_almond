import os
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import praw

def load_reddit():
    load_dotenv()
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=None,
        user_agent=os.getenv("REDDIT_USER_AGENT"),
        check_for_async=False,
    )
    reddit.read_only = True
    print("✅ Reddit read-only client initialized")
    return reddit


# ---------------- Core Search ----------------
def search_posts(
    reddit, query, subreddit="all", limit=200, sort="new",
    time_filter="all", after=None, seen_ids=None
):
    sr = reddit.subreddit(subreddit)
    params = {}
    if after:
        params["after"] = after

    print(f"🔍 Searching '{query}' in r/{subreddit} (sort={sort}, time={time_filter})...")
    print(f"   ➡️ Continue from after={after if after else 'start'}")

    count = 0
    for s in sr.search(
        query=query,
        sort=sort,
        time_filter=time_filter,
        syntax="lucene",
        limit=limit,
        params=params,
    ):
        if seen_ids and s.id in seen_ids:
            continue

        yield {
            "id": s.id,
            "title": s.title,
            "selftext": s.selftext,
            # "author": str(s.author) if s.author else "",
            "score": s.score,
            "num_comments": s.num_comments,
            "subreddit": str(s.subreddit),
            "created_utc": datetime.utcfromtimestamp(s.created_utc).isoformat(),
            # "permalink": f"https://www.reddit.com{s.permalink}",
            # "url": s.url,
        }
        count += 1

    print(f"✅ Search finished. Total fetched: {count}")


# ---------------- Save / Resume ----------------
def load_seen_ids(history_dir: Path):
    seen = set()
    for f in history_dir.glob("*.json"):
        try:
            data = json.load(open(f, encoding="utf-8"))
            seen.update([r["id"] for r in data])
        except:
            pass
    print(f"📚 Found {len(seen)} historical IDs to skip duplicates.")
    return seen


def save_data(rows, query, out_dir):
    if not rows:
        print("⚠️ No posts fetched.")
        return None

    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = f"posts_{query.replace(' ', '_')}_{timestamp}"

    json_path = out_dir / f"{base_name}.json"
    csv_path = out_dir / f"{base_name}.csv"
    last_id_path = out_dir / f"{base_name}_last_id.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    last_id = rows[-1]["id"]
    with open(last_id_path, "w") as f:
        f.write(last_id)

    print(f"💾 JSON saved: {json_path}")
    print(f"💾 CSV saved:  {csv_path}")
    print(f"📌 Last post ID saved to {last_id_path}")
    return last_id


# ---------------- Merge JSON ----------------
def merge_json_files(out_dir: Path, query: str):
    files = sorted(out_dir.glob("posts_*.json"))
    if not files:
        print("⚠️ No JSON files found to merge.")
        return

    all_data = []
    seen = set()

    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
            for r in data:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    all_data.append(r)
        except Exception as e:
            print(f"⚠️ Failed to read {f}: {e}")

    print(f"🔗 Merging {len(files)} files, total unique posts: {len(all_data)}")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = f"merged_posts_{query.replace(' ', '_')}_{timestamp}"

    json_path = out_dir / f"{base_name}.json"
    csv_path = out_dir / f"{base_name}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_data[0].keys()))
        w.writeheader()
        w.writerows(all_data)

    print(f"✅ Merged JSON: {json_path}")
    print(f"✅ Merged CSV:  {csv_path}")


# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", required=True, help="keyword")
    parser.add_argument("--subreddit", default="all")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--sort", default="relevance", choices=["relevance", "hot", "top", "new", "comments"])
    parser.add_argument("--time", default="all", choices=["all", "hour", "day", "week", "month", "year"])
    parser.add_argument("--after", default=None, help="after id")
    parser.add_argument("--out", default="reddit_output")
    parser.add_argument("--resume_from", default=None, help=" last id")
    parser.add_argument("--avoid_duplicates", action="store_true", help="json")
    parser.add_argument("--merge", action="store_true", help="is merge JSON")
    args = parser.parse_args()

    reddit = load_reddit()

    after_id = args.after
    if args.resume_from and Path(args.resume_from).exists():
        after_id = open(args.resume_from).read().strip()

    seen_ids = load_seen_ids(Path(args.out)) if args.avoid_duplicates else set()

    rows = list(search_posts(
        reddit, args.q, subreddit=args.subreddit, limit=args.limit,
        sort=args.sort, time_filter=args.time, after=after_id, seen_ids=seen_ids
    ))
    print(f"✅ Done: {len(rows)} posts fetched.")

    last_id = save_data(rows, args.q, args.out)
    if last_id:
        print(f"👉 Next run: use  --after {last_id}")
        print(f"   or  --resume_from {args.out}/posts_{args.q.replace(' ', '_')}_<timestamp>_last_id.txt")

    if args.merge:
        merge_json_files(Path(args.out), args.q)


if __name__ == "__main__":
    main()
