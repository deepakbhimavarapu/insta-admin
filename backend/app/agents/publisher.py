import os
import json
import requests
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from ..config import settings
from ..database import get_db_connection

# Extend config settings inside script if not defined in Settings class yet
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
NGROK_TUNNEL_URL = os.getenv("NGROK_TUNNEL_URL", "") # Optional tunnel to expose local assets publicly

def create_instagram_media_container(image_url: str, caption: str) -> str:
    """
    Step 1: Creates an Instagram Media Container on Meta's servers.
    Returns the container ID.
    """
    if not FACEBOOK_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        raise ValueError("Meta API credentials (FACEBOOK_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID) are missing.")

    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    print(f"Contacting Meta API to create container for: {image_url}...")
    response = requests.post(url, data=payload)
    res_data = response.json()
    
    if response.status_code != 200 or "id" not in res_data:
        error_msg = res_data.get("error", {}).get("message", "Unknown Meta API error.")
        raise Exception(f"Meta Media Container creation failed: {error_msg}")
        
    container_id = res_data["id"]
    print(f"Container created successfully. ID: {container_id}")
    return container_id

def poll_container_status(container_id: str, timeout_seconds: int = 60) -> bool:
    """
    Step 2: Polls the media container status until it is 'FINISHED' and ready to publish.
    """
    url = f"https://graph.facebook.com/v19.0/{container_id}"
    params = {
        "fields": "status_code,status",
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        response = requests.get(url, params=params)
        res_data = response.json()
        status_code = res_data.get("status_code")
        
        print(f"Polling container {container_id} status... Status code: {status_code}")
        if status_code == "FINISHED":
            return True
        elif status_code == "ERROR":
            error_msg = res_data.get("error", {}).get("message", "Media processing failed.")
            raise Exception(f"Meta container processing encountered an error: {error_msg}")
            
        time.sleep(5) # Wait 5 seconds before polling again
        
    raise TimeoutError("Meta API media container processing timed out.")

def publish_media_container(container_id: str) -> str:
    """
    Step 3: Publishes the fully processed media container to the Instagram feed.
    Returns the published Instagram Post ID.
    """
    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    print(f"Publishing container {container_id} to Instagram feed...")
    response = requests.post(url, data=payload)
    res_data = response.json()
    
    if response.status_code != 200 or "id" not in res_data:
        error_msg = res_data.get("error", {}).get("message", "Unknown Meta publish error.")
        raise Exception(f"Meta publish failed: {error_msg}")
        
    post_id = res_data["id"]
    print(f"Success! Post published. Instagram Post ID: {post_id}")
    return post_id

def publish_single_post(queue_id: str, local_image_paths: List[str], caption: str) -> Tuple[bool, str]:
    """
    Resolves image routes, exposes them via ngrok if available, and issues Meta Graph requests.
    NOTE: Currently only publishes single-image posts. Carousel container posting is also supported 
    by Meta via multiple children items, but single image is standard for basic posts.
    """
    if not local_image_paths:
        return False, "No graphic slides associated with this queued post."
        
    # Pick the first slide for the Instagram feed post
    first_image_relative = local_image_paths[0] # e.g. "/assets/slide_abc_1.jpg"
    
    # Resolve the public image URL
    if NGROK_TUNNEL_URL:
        # Strip trailing slash from ngrok and leading slash from assets
        base_tunnel = NGROK_TUNNEL_URL.rstrip("/")
        relative_path = first_image_relative.lstrip("/")
        image_url = f"{base_tunnel}/{relative_path}"
    else:
        # Fallback to local address (this will error on Meta's server unless ngrok/tunnel is configured)
        image_url = f"http://127.0.0.1:8000{first_image_relative}"
        print("[WARNING] NGROK_TUNNEL_URL not configured. Meta will likely fail to crawl this local image address!")

    try:
        # 1. Create container
        container_id = create_instagram_media_container(image_url, caption)
        
        # 2. Wait for processing
        poll_container_status(container_id)
        
        # 3. Publish
        instagram_post_id = publish_media_container(container_id)
        return True, instagram_post_id
    except Exception as e:
        return False, str(e)

def publish_due_posts():
    """
    Primary cron/worker entry point.
    Searches SQLite database for queued scheduled posts that are due,
    publishes them, and logs success or failure states.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_str = datetime.now(timezone.utc).isoformat()
    
    # Query due scheduled items
    cursor.execute("""
        SELECT q.id, q.selected_caption, q.scheduled_at, p.graphic_urls, p.id as pending_id
        FROM published_queue q
        JOIN pending_review p ON q.pending_review_id = p.id
        WHERE q.status = 'queued' AND q.scheduled_at <= ?
    """, (now_str,))
    
    due_posts = cursor.fetchall()
    print(f"Checking for due posts at {now_str}. Found: {len(due_posts)} posts ready to publish.")
    
    for post in due_posts:
        queue_id = post["id"]
        caption = post["selected_caption"]
        graphic_urls = json.loads(post["graphic_urls"])
        
        print(f"Processing queued item ID: {queue_id} (Scheduled for {post['scheduled_at']})...")
        
        # Mark as publishing first to avoid double-processing
        cursor.execute("UPDATE published_queue SET status = 'publishing' WHERE id = ?", (queue_id,))
        conn.commit()
        
        success, result_str = publish_single_post(queue_id, graphic_urls, caption)
        
        finished_now = datetime.now(timezone.utc).isoformat()
        if success:
            # Update success stats
            cursor.execute("""
                UPDATE published_queue 
                SET status = 'published', instagram_post_id = ?, published_at = ? 
                WHERE id = ?
            """, (result_str, finished_now, queue_id))
            print(f"Successfully posted item {queue_id} to Instagram!")
        else:
            # Update failure logs
            cursor.execute("""
                UPDATE published_queue 
                SET status = 'failed', error_message = ? 
                WHERE id = ?
            """, (result_str, queue_id))
            print(f"FAILED to publish item {queue_id}. Error: {result_str}")
            
        conn.commit()
        
    conn.close()

if __name__ == "__main__":
    # Local worker testing loop
    publish_due_posts()
