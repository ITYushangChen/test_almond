# -*- coding: utf-8 -*-
"""
reddit_stage2_posts_and_comments.py
根据 post_id 列表抓取：①完整评论树 ②对应帖子元数据

用法：
    python3 reddit_official_comments.py \
        --ids post_ids.txt \
        --out reddit_stage4_post_comments \
        --sleep 0.3
"""
import os, json, csv, argparse, time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import praw
from praw.models import MoreComments

# -------- Reddit Client --------
def load_reddit():
    load_dotenv()
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=None,                  # read-only，无需 secret
        user_agent=os.getenv("REDDIT_USER_AGENT") or "COMP9900/0.1",
        check_for_async=False,
    )
    reddit.read_only = True
    print("✅ Reddit read-only client ready")
    return reddit

# -------- Helpers --------
def _submission_row(s):
    """把帖子对象拍成一行 dict（用于posts文件 & 合并到评论里）"""
    return {
        "post_id": s.id,
        "post_title": s.title or "",
        "post_selftext": s.selftext or "",
        "post_author": str(s.author) if s.author else "",
        "post_subreddit": str(s.subreddit) if s.subreddit else "",
        "post_score": s.score,
        "post_num_comments": s.num_comments,
        "post_created_utc": datetime.utcfromtimestamp(s.created_utc).isoformat(),
        "post_permalink": f"https://www.reddit.com{s.permalink}",
        "post_url": s.url or "",
        "post_over_18": bool(getattr(s, "over_18", False)),
        "post_spoiler": bool(getattr(s, "spoiler", False)),
        "post_locked": bool(getattr(s, "locked", False)),
    }

def fetch_comments_with_post(submission):
    """返回 (post_row, comments_rows) 元组"""
    post_row = _submission_row(submission)

    # 展开完整评论树
    submission.comments.replace_more(limit=None)
    comments_rows = []
    for c in submission.comments.list():
        if isinstance(c, MoreComments):
            continue
        comments_rows.append({
            # 评论字段
            "post_id": submission.id,
            "comment_id": c.id,
            "parent_id": c.parent_id,
            "author": str(c.author) if c.author else "",
            "body": (c.body or "")[:8000],
            "score": c.score,
            "created_utc": datetime.utcfromtimestamp(c.created_utc).isoformat(),
            "depth": int(getattr(c, "depth", 0)),
            # 方便分析：把关键信息并到每条评论
            **{
                k: post_row[k] for k in [
                    "post_title", "post_selftext", "post_author", "post_subreddit",
                    "post_score", "post_num_comments", "post_created_utc",
                    "post_permalink", "post_url"
                ]
            }
        })
    return post_row, comments_rows

# -------- Main --------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True, help="包含 post_id 的 txt 文件，每行一个，如：1abcde")
    parser.add_argument("--out", default="reddit_stage4_post_comments", help="输出目录")
    parser.add_argument("--sleep", type=float, default=0.3, help="每个帖子之间的停顿秒数")
    args = parser.parse_args()

    reddit = load_reddit()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 读取待抓 post_id 列表
    with open(args.ids, "r", encoding="utf-8") as f:
        post_ids = [line.strip() for line in f if line.strip()]

    all_posts = []
    all_comments = []

    for idx, pid in enumerate(post_ids, 1):
        try:
            s = reddit.submission(id=pid)
            post_row, comments_rows = fetch_comments_with_post(s)
            all_posts.append(post_row)
            all_comments.extend(comments_rows)
            print(f"✅ [{idx}/{len(post_ids)}] {pid}: {len(comments_rows)} comments")
        except Exception as e:
            print(f"⚠️  [{idx}/{len(post_ids)}] {pid} failed: {e}")
        time.sleep(args.sleep)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    posts_json = out_dir / f"posts_{ts}.json"
    posts_csv  = out_dir / f"posts_{ts}.csv"
    cmts_json  = out_dir / f"comments_{ts}.json"
    cmts_csv   = out_dir / f"comments_{ts}.csv"

    # 保存 posts
    with open(posts_json, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    if all_posts:
        with open(posts_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_posts[0].keys()))
            w.writeheader()
            w.writerows(all_posts)

    # 保存 comments
    with open(cmts_json, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    if all_comments:
        with open(cmts_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_comments[0].keys()))
            w.writeheader()
            w.writerows(all_comments)

    print(f"💾 Saved {len(all_posts)} posts → {posts_json}")
    print(f"💾 Saved {len(all_comments)} comments → {cmts_json}")

if __name__ == "__main__":
    main()
