import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_youtube_timestamp(ts):
    if not ts:
        return None
    try:
        # YouTube uses ISO 8601 format, e.g., "2023-03-24T00:34:59Z"
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception as e:
        print(f"Failed to parse timestamp: {ts} - {e}")
        return None


def map_video_to_post(video):
    return {
        "id": f"yt_{video.get('video_id')}",  # Add prefix to avoid conflicts with other sources
        "source": "youtube",
        "post_title": video.get("title"),
        "post_selftext": video.get("description"),
        "likes": video.get("like_count") or 0,
        "num_comments": video.get("comment_count") or 0,
        "post_permalink": video.get("url"),
        "base_theme": None,  
        "sub_theme": None,   
        "sentiment": None,   
        "posted_at": parse_youtube_timestamp(video.get("published_at")),
        "content": f"{video.get('title', '')}\n\n{video.get('description', '')}", 
    }


def map_comment_to_comment(comment):
    parent_id = None
    if comment.get("is_reply") and comment.get("parent_comment_id"):
        parent_id = f"yt_c_{comment.get('parent_comment_id')}"
    depth = 1 if comment.get("is_reply") else 0
    
    return {
        "id": f"yt_c_{comment.get('comment_id')}",  
        "post_id": f"yt_{comment.get('video_id')}",  
        "source": "youtube",
        "parent_id": parent_id,
        "author": comment.get("author"),
        "body": comment.get("text"),
        "likes": comment.get("like_count") or 0,
        "depth": depth,
        "sentiment": None,   
        "base_theme": None,  
        "sub_theme": None,   
        "created_at": parse_youtube_timestamp(comment.get("published_at")),
    }


def insert_videos_batch(videos, batch_size=100):
    
    posts = [map_video_to_post(v) for v in videos]
    
    success_count = 0
    error_count = 0
    
    for i in range(0, len(posts), batch_size):
        batch = posts[i:i+batch_size]
        try:
            result = supabase.table("posts").upsert(batch).execute()
            success_count += len(batch)
            print(f"   ✅ Imported {success_count}/{len(posts)} videos")
        except Exception as e:
            error_count += len(batch)
            print(f"   ❌ Batch insert failed: {e}")
            # If batch fails, try inserting one by one
            for post in batch:
                try:
                    supabase.table("posts").upsert(post).execute()
                    success_count += 1
                    error_count -= 1
                except Exception as e2:
                    print(f"   ❌ Single insert failed (ID: {post['id']}): {e2}")
    
    print(f"\n✅ Video import completed: {success_count} succeeded, {error_count} failed")
    return success_count, error_count


def insert_comments_batch(comments, batch_size=100):
    """Batch insert comments into comments table"""
    print(f"\n💬 Starting to import {len(comments)} comments...")
    
    comment_rows = [map_comment_to_comment(c) for c in comments]
    
    # Batch insert
    success_count = 0
    error_count = 0
    
    for i in range(0, len(comment_rows), batch_size):
        batch = comment_rows[i:i+batch_size]
        try:
            result = supabase.table("comments").upsert(batch).execute()
            success_count += len(batch)
            print(f"   ✅ Imported {success_count}/{len(comment_rows)} comments")
        except Exception as e:
            error_count += len(batch)
            print(f"   ❌ Batch insert failed: {e}")
            # If batch fails, try inserting one by one
            for comment in batch:
                try:
                    supabase.table("comments").upsert(comment).execute()
                    success_count += 1
                    error_count -= 1
                except Exception as e2:
                    print(f"   ❌ Single insert failed (ID: {comment['id']}): {e2}")
    
    print(f"\n✅ Comment import completed: {success_count} succeeded, {error_count} failed")
    return success_count, error_count


def import_youtube_json(json_file_path):
    """Import a single YouTube JSON file"""
    print(f"\n{'='*60}")
    print(f"📂 Processing file: {json_file_path}")
    print(f"{'='*60}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        videos = data.get('videos', [])
        comments = data.get('comments', [])
        
        print(f"📊 File statistics:")
        print(f"   - Videos: {len(videos)}")
        print(f"   - Comments: {len(comments)}")
        
        # Import videos
        v_success, v_error = insert_videos_batch(videos)
        
        # Import comments
        c_success, c_error = insert_comments_batch(comments)
        
        return {
            'file': json_file_path,
            'videos_success': v_success,
            'videos_error': v_error,
            'comments_success': c_success,
            'comments_error': c_error
        }
        
    except Exception as e:
        print(f"❌ Failed to process file: {e}")
        import traceback
        traceback.print_exc()
        return None


def import_all_youtube_files(directory="youtube_output"):
    """Import all YouTube JSON files in the directory"""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"❌ Directory does not exist: {directory}")
        return
    
    # Find all JSON files
    json_files = list(dir_path.glob("youtube_results_*.json"))
    
    if not json_files:
        print(f"❌ No YouTube JSON files found in {directory}")
        return
    
    print(f"🔍 Found {len(json_files)} YouTube JSON files")
    
    results = []
    for json_file in json_files:
        result = import_youtube_json(str(json_file))
        if result:
            results.append(result)
    
    # Print summary report
    print("\n" + "="*60)
    print("📊 Import Summary Report")
    print("="*60)
    
    total_v_success = sum(r['videos_success'] for r in results)
    total_v_error = sum(r['videos_error'] for r in results)
    total_c_success = sum(r['comments_success'] for r in results)
    total_c_error = sum(r['comments_error'] for r in results)
    
    print(f"\n📹 Videos:")
    print(f"   ✅ Succeeded: {total_v_success}")
    print(f"   ❌ Failed: {total_v_error}")
    
    print(f"\n💬 Comments:")
    print(f"   ✅ Succeeded: {total_c_success}")
    print(f"   ❌ Failed: {total_c_error}")
    
    print(f"\n🎉 All completed!")


def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        # If file path is provided as argument, import the specified file
        json_file = sys.argv[1]
        import_youtube_json(json_file)
    else:
        # Otherwise import the entire directory
        import_all_youtube_files("youtube_output")


if __name__ == "__main__":
    main()

