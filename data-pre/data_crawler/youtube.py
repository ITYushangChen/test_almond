#!/usr/bin/env python3
"""
YouTube Video and Comments Crawler
Searches for videos by keyword and retrieves video details and all comments
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()


class YouTubeCrawler:
    """
    YouTube crawler for searching videos and retrieving comments
    Uses official YouTube Data API v3
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube API client
        
        Args:
            api_key: YouTube Data API v3 key (or set YOUTUBE_API_KEY in .env)
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "YouTube API key not found. Please provide api_key parameter "
                "or set YOUTUBE_API_KEY in .env file.\n"
                "Get your API key from: https://console.cloud.google.com/apis/credentials"
            )
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.results = {
            "videos": [],
            "comments": []
        }
        
        print("✅ YouTube API initialized successfully\n")
    
    def search_videos(
        self, 
        keyword: str, 
        max_results: int = 10,
        order: str = "relevance",
        published_after: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for videos by keyword
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of videos to return (default: 10)
            order: Sort order - relevance, date, rating, viewCount, title
            published_after: ISO 8601 date (e.g., "2024-01-01T00:00:00Z")
            
        Returns:
            List of video information dictionaries
        """
        print(f"🔍 Searching for videos with keyword: '{keyword}'")
        print(f"   Max results: {max_results}, Order by: {order}")
        
        videos = []
        next_page_token = None
        
        try:
            while len(videos) < max_results:
                # Search request
                search_params = {
                    'q': keyword,
                    'part': 'id,snippet',
                    'type': 'video',
                    'maxResults': min(50, max_results - len(videos)),  # API max is 50
                    'order': order,
                    'pageToken': next_page_token
                }
                
                if published_after:
                    search_params['publishedAfter'] = published_after
                
                search_response = self.youtube.search().list(**search_params).execute()
                
                # Extract video IDs and basic info
                for item in search_response.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item['snippet']
                    
                    video_info = {
                        'video_id': video_id,
                        'title': snippet['title'],
                        'channel_title': snippet['channelTitle'],
                        'channel_id': snippet['channelId'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail': snippet['thumbnails']['high']['url']
                    }
                    
                    videos.append(video_info)
                    print(f"   ✓ Found: {video_info['title'][:60]}...")
                
                # Check for next page
                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break
                
                time.sleep(0.5)  # Rate limiting
            
            print(f"\n✅ Found {len(videos)} videos\n")
            return videos
            
        except HttpError as e:
            print(f"❌ Error searching videos: {e}")
            return videos
    
    def get_video_details(self, video_ids: List[str]) -> List[Dict]:
        """
        Get detailed information for videos
        
        Args:
            video_ids: List of video IDs
            
        Returns:
            List of detailed video information
        """
        print(f"📊 Fetching details for {len(video_ids)} videos...")
        
        details = []
        
        try:
            # YouTube API allows up to 50 IDs per request
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                
                response = self.youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=','.join(batch_ids)
                ).execute()
                
                for item in response.get('items', []):
                    video_detail = {
                        'video_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'channel_title': item['snippet']['channelTitle'],
                        'channel_id': item['snippet']['channelId'],
                        'published_at': item['snippet']['publishedAt'],
                        'tags': item['snippet'].get('tags', []),
                        'category_id': item['snippet'].get('categoryId'),
                        'view_count': int(item['statistics'].get('viewCount', 0)),
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'comment_count': int(item['statistics'].get('commentCount', 0)),
                        'duration': item['contentDetails']['duration'],
                        'url': f"https://www.youtube.com/watch?v={item['id']}"
                    }
                    
                    details.append(video_detail)
                    print(f"   ✓ {video_detail['title'][:50]}... "
                          f"({video_detail['view_count']:,} views, "
                          f"{video_detail['comment_count']:,} comments)")
                
                time.sleep(0.5)  # Rate limiting
            
            print(f"\n✅ Retrieved details for {len(details)} videos\n")
            self.results["videos"] = details
            return details
            
        except HttpError as e:
            print(f"❌ Error fetching video details: {e}")
            return details
    
    def get_video_comments(
        self, 
        video_id: str, 
        max_comments: Optional[int] = None,
        include_replies: bool = True
    ) -> List[Dict]:
        """
        Get all comments for a specific video
        
        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of comments (None = all)
            include_replies: Whether to include comment replies
            
        Returns:
            List of comment dictionaries
        """
        print(f"💬 Fetching comments for video: {video_id}")
        
        comments = []
        next_page_token = None
        
        try:
            while True:
                response = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=100,  # API max per page
                    pageToken=next_page_token,
                    textFormat='plainText',
                    order='relevance'  # or 'time'
                ).execute()
                
                for item in response.get('items', []):
                    # Top-level comment
                    top_comment = item['snippet']['topLevelComment']['snippet']
                    
                    comment_data = {
                        'video_id': video_id,
                        'comment_id': item['snippet']['topLevelComment']['id'],
                        'author': top_comment['authorDisplayName'],
                        'author_channel_id': top_comment.get('authorChannelId', {}).get('value'),
                        'text': top_comment['textDisplay'],
                        'like_count': top_comment['likeCount'],
                        'published_at': top_comment['publishedAt'],
                        'updated_at': top_comment['updatedAt'],
                        'reply_count': item['snippet']['totalReplyCount'],
                        'is_reply': False,
                        'parent_comment_id': None
                    }
                    
                    comments.append(comment_data)
                    
                    # Get replies if they exist and if requested
                    if include_replies and item['snippet']['totalReplyCount'] > 0:
                        replies = item.get('replies', {}).get('comments', [])
                        
                        for reply in replies:
                            reply_snippet = reply['snippet']
                            
                            reply_data = {
                                'video_id': video_id,
                                'comment_id': reply['id'],
                                'author': reply_snippet['authorDisplayName'],
                                'author_channel_id': reply_snippet.get('authorChannelId', {}).get('value'),
                                'text': reply_snippet['textDisplay'],
                                'like_count': reply_snippet['likeCount'],
                                'published_at': reply_snippet['publishedAt'],
                                'updated_at': reply_snippet['updatedAt'],
                                'reply_count': 0,
                                'is_reply': True,
                                'parent_comment_id': comment_data['comment_id']
                            }
                            
                            comments.append(reply_data)
                
                print(f"   Retrieved {len(comments)} comments so far...")
                
                # Check if we should continue
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
                
                if max_comments and len(comments) >= max_comments:
                    comments = comments[:max_comments]
                    break
                
                time.sleep(0.5)  # Rate limiting
            
            print(f"   ✅ Total comments retrieved: {len(comments)}\n")
            return comments
            
        except HttpError as e:
            if 'commentsDisabled' in str(e):
                print(f"   ⚠️  Comments are disabled for this video\n")
            else:
                print(f"   ❌ Error fetching comments: {e}\n")
            return comments
    
    def crawl_by_keyword(
        self,
        keyword: str,
        max_videos: int = 10,
        max_comments_per_video: Optional[int] = None,
        order: str = "relevance",
        published_after: Optional[str] = None,
        include_replies: bool = True
    ) -> Dict:
        """
        Complete crawl: search videos and get all comments
        
        Args:
            keyword: Search keyword
            max_videos: Maximum number of videos to crawl
            max_comments_per_video: Max comments per video (None = all)
            order: Sort order for search results
            published_after: Filter videos published after this date
            include_replies: Whether to include comment replies
            
        Returns:
            Dictionary with videos and comments data
        """
        print("="*70)
        print(f"🚀 Starting YouTube Crawl")
        print("="*70)
        print(f"Keyword: {keyword}")
        print(f"Max videos: {max_videos}")
        print(f"Max comments per video: {max_comments_per_video or 'All'}")
        print("="*70 + "\n")
        
        # Step 1: Search for videos
        videos = self.search_videos(
            keyword=keyword,
            max_results=max_videos,
            order=order,
            published_after=published_after
        )
        
        if not videos:
            print("❌ No videos found")
            return self.results
        
        # Step 2: Get detailed video information
        video_ids = [v['video_id'] for v in videos]
        video_details = self.get_video_details(video_ids)
        
        # Step 3: Get comments for each video
        all_comments = []
        
        for i, video in enumerate(video_details, 1):
            print(f"[{i}/{len(video_details)}] Processing: {video['title'][:50]}...")
            
            comments = self.get_video_comments(
                video_id=video['video_id'],
                max_comments=max_comments_per_video,
                include_replies=include_replies
            )
            
            all_comments.extend(comments)
        
        self.results = {
            "videos": video_details,
            "comments": all_comments,
            "metadata": {
                "keyword": keyword,
                "total_videos": len(video_details),
                "total_comments": len(all_comments),
                "crawled_at": datetime.utcnow().isoformat()
            }
        }
        
        print("="*70)
        print("✅ Crawl Complete!")
        print("="*70)
        print(f"Videos crawled: {len(video_details)}")
        print(f"Comments collected: {len(all_comments)}")
        print("="*70 + "\n")
        
        return self.results
    
    def save_to_json(self, filename: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_results_{timestamp}.json"
        
        output_dir = Path(__file__).parent / "youtube_output"
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Saved JSON: {filepath}")
        return str(filepath)
    
    def save_to_csv(self, filename_prefix: Optional[str] = None) -> tuple:
        """Save results to CSV files (separate for videos and comments)"""
        if not filename_prefix:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"youtube_{timestamp}"
        
        output_dir = Path(__file__).parent / "youtube_output"
        output_dir.mkdir(exist_ok=True)
        
        # Save videos
        videos_file = output_dir / f"{filename_prefix}_videos.csv"
        if self.results.get("videos"):
            with open(videos_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.results["videos"][0].keys())
                writer.writeheader()
                writer.writerows(self.results["videos"])
            print(f"💾 Saved videos CSV: {videos_file}")
        
        # Save comments
        comments_file = output_dir / f"{filename_prefix}_comments.csv"
        if self.results.get("comments"):
            with open(comments_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.results["comments"][0].keys())
                writer.writeheader()
                writer.writerows(self.results["comments"])
            print(f"💾 Saved comments CSV: {comments_file}")
        
        return str(videos_file), str(comments_file)


def main():
    """Main execution with command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YouTube Video and Comments Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for Rio Tinto videos and get all comments
  python youtube_crawler.py --keyword "Rio Tinto mining" --max-videos 5
  
  # Search with date filter
  python youtube_crawler.py --keyword "Rio Tinto" --max-videos 10 --after 2024-01-01
  
  # Limit comments per video
  python youtube_crawler.py --keyword "Rio Tinto culture" --max-videos 5 --max-comments 100
  
  # Sort by most recent
  python youtube_crawler.py --keyword "Rio Tinto" --max-videos 10 --order date

API Key Setup:
  1. Get API key from: https://console.cloud.google.com/apis/credentials
  2. Enable YouTube Data API v3
  3. Add to .env file: YOUTUBE_API_KEY=your-key-here
  Or use --api-key parameter
        """
    )
    
    parser.add_argument(
        '--keyword',
        type=str,
        required=True,
        help='Search keyword (e.g., "Rio Tinto")'
    )
    parser.add_argument(
        '--max-videos',
        type=int,
        default=10,
        help='Maximum number of videos to crawl (default: 10)'
    )
    parser.add_argument(
        '--max-comments',
        type=int,
        default=None,
        help='Maximum comments per video (default: all)'
    )
    parser.add_argument(
        '--order',
        choices=['relevance', 'date', 'rating', 'viewCount', 'title'],
        default='relevance',
        help='Sort order for video search (default: relevance)'
    )
    parser.add_argument(
        '--after',
        type=str,
        default=None,
        help='Only videos published after this date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--no-replies',
        action='store_true',
        help='Exclude comment replies (faster)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='YouTube API key (or set YOUTUBE_API_KEY in .env)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'csv', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    
    args = parser.parse_args()
    
    # Convert date format if provided
    published_after = None
    if args.after:
        try:
            published_after = f"{args.after}T00:00:00Z"
        except:
            print(f"⚠️  Invalid date format: {args.after}. Use YYYY-MM-DD")
    
    try:
        # Initialize crawler
        crawler = YouTubeCrawler(api_key=args.api_key)
        
        # Perform crawl
        results = crawler.crawl_by_keyword(
            keyword=args.keyword,
            max_videos=args.max_videos,
            max_comments_per_video=args.max_comments,
            order=args.order,
            published_after=published_after,
            include_replies=not args.no_replies
        )
        
        # Save results
        print("\n📁 Saving results...")
        if args.output_format in ['json', 'both']:
            crawler.save_to_json()
        
        if args.output_format in ['csv', 'both']:
            crawler.save_to_csv()
        
        print("\n✅ All done!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

