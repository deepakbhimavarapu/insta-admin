import os
import sqlite3
import json
import uuid
import random
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from .config import settings
from .database import get_db_connection, get_pending_review_count, init_db
from .agents.scout import run_scout_agent, ingest_single_story
from .agents.editor import process_and_create_confession
from .agents.publisher import publish_due_posts

# Initialize FastAPI application
app = FastAPI(title="Swayam-Admin API Engine", version="1.0.0")

# Enable CORS for Next.js Dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure assets directory exists and mount it as static files
os.makedirs(settings.ASSETS_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory=settings.ASSETS_DIR), name="assets")

# Ensure database is initialized on server startup
@app.on_event("startup")
def on_startup():
    init_db()

# Request/Response schemas
class ReviewAction(BaseModel):
    action: str                       # 'approve' or 'reject'
    selected_caption: Optional[str] = None # Mandatory if approved
    schedule_hours: Optional[int] = 4  # Post in X hours from now if approved

def run_refill_pipeline():
    """Background task to refill the PENDING_REVIEW queue up to 10 items."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    pending_count = get_pending_review_count()
    target = settings.PENDING_QUEUE_TARGET
    
    print(f"Refill trigger started. Current pending queue count: {pending_count}/{target}")
    
    if pending_count >= target:
        conn.close()
        return
        
    needed = target - pending_count
    
    # 1. Fetch unused raw stories
    cursor.execute("""
        SELECT id, raw_text 
        FROM raw_stories 
        WHERE status = 'pending' 
        ORDER BY created_at ASC 
        LIMIT ?
    """, (needed,))
    raw_rows = cursor.fetchall()
    
    # 2. If raw stories are insufficient, run the Scout Agent to pull more data
    if len(raw_rows) < needed:
        print("Raw stories are insufficient. Triggering Scout Agent to crawl more content...")
        run_scout_agent()
        
        # Re-fetch after scouting
        cursor.execute("""
            SELECT id, raw_text 
            FROM raw_stories 
            WHERE status = 'pending' 
            ORDER BY created_at ASC 
            LIMIT ?
        """, (needed,))
        raw_rows = cursor.fetchall()
        
    # 3. Process each raw story into a beautiful Tanglish image
    processed_count = 0
    for row in raw_rows:
        raw_id = row["id"]
        raw_text = row["raw_text"]
        
        # Select a random common location for context
        location = random_nri_location()
        print(f"Editor processing raw story ID {raw_id} with location: {location}...")
        
        try:
            # Run LLM and Graphic generation
            result = process_and_create_confession(raw_text, location, raw_id)
            
            # Map graphic paths to relative URLs served by FastAPI
            relative_urls = []
            for filepath in result["graphic_urls"]:
                filename = os.path.basename(filepath)
                # Static path matching mounted assets folder
                relative_urls.append(f"/assets/{filename}")
                
            # Insert into pending_review table
            now_str = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO pending_review (id, raw_story_id, adapted_text, tone_location, graphic_urls, caption_options, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                result["id"], 
                raw_id, 
                result["adapted_text"], 
                result["tone_location"], 
                json.dumps(relative_urls), 
                json.dumps(result["caption_options"]), 
                now_str
            ))
            
            # Mark raw story as processed
            cursor.execute("UPDATE raw_stories SET status = 'processed' WHERE id = ?", (raw_id,))
            conn.commit()
            processed_count += 1
            print(f"Success! story ID {raw_id} promoted to PENDING_REVIEW.")
            
        except Exception as e:
            print(f"Failed to process raw story ID {raw_id}: {e}")
            cursor.execute("UPDATE raw_stories SET status = 'ignored' WHERE id = ?", (raw_id,))
            conn.commit()
            
    conn.close()
    print(f"Refill task complete. Promoted {processed_count} stories to dashboard.")

def random_nri_location() -> str:
    """Returns a random NRI-heavy diaspora hub."""
    locations = ["Dallas", "New Jersey", "Chicago", "London", "Bay Area", "New York"]
    import random
    return random.choice(locations)

@app.get("/api/dashboard")
def get_dashboard_queue():
    """Returns the current 10-Story review queue and publishing stats."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch pending reviews
    cursor.execute("""
        SELECT id, adapted_text, tone_location, graphic_urls, caption_options, created_at 
        FROM pending_review 
        WHERE status = 'pending' 
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()
    
    # Fetch scheduled counts
    cursor.execute("SELECT COUNT(*) FROM published_queue WHERE status = 'queued'")
    scheduled_count = cursor.fetchone()[0]
    
    conn.close()
    
    dashboard_items = []
    for row in rows:
        dashboard_items.append({
            "id": row["id"],
            "adapted_text": row["adapted_text"],
            "tone_location": row["tone_location"],
            "graphic_urls": json.loads(row["graphic_urls"]),
            "caption_options": json.loads(row["caption_options"]),
            "created_at": row["created_at"]
        })
        
    return {
        "pending_count": len(dashboard_items),
        "scheduled_queue_count": scheduled_count,
        "items": dashboard_items
    }

@app.post("/api/review/{id}")
def review_story(id: str, action_data: ReviewAction, background_tasks: BackgroundTasks):
    """Approves or rejects a story card on the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify story exists and is pending
    cursor.execute("SELECT id FROM pending_review WHERE id = ? AND status = 'pending'", (id,))
    story = cursor.fetchone()
    if not story:
        conn.close()
        raise HTTPException(status_code=404, detail="Pending story not found.")
        
    now_str = datetime.now(timezone.utc).isoformat()
    
    if action_data.action == "approve":
        if not action_data.selected_caption:
            conn.close()
            raise HTTPException(status_code=400, detail="selected_caption is required for approval.")
            
        # Update pending_review status
        cursor.execute("UPDATE pending_review SET status = 'approved' WHERE id = ?", (id,))
        
        # Calculate schedule time with AI auto-spacing queue pacing algorithm
        # Grab the maximum scheduled_at timestamp of any active queued posts
        cursor.execute("SELECT MAX(scheduled_at) FROM published_queue WHERE status = 'queued'")
        max_scheduled_row = cursor.fetchone()
        
        spacing_hours = action_data.schedule_hours if action_data.schedule_hours and action_data.schedule_hours > 0 else 4
        
        if max_scheduled_row and max_scheduled_row[0]:
            try:
                # Add spacing hours after the last queued post for seamless pacing
                latest_dt = datetime.fromisoformat(max_scheduled_row[0])
                scheduled_dt = latest_dt + timedelta(hours=spacing_hours)
            except Exception:
                scheduled_dt = datetime.now(timezone.utc) + timedelta(hours=spacing_hours)
        else:
            # If queue is completely empty, post in 2 hours
            scheduled_dt = datetime.now(timezone.utc) + timedelta(hours=2)
            
        scheduled_time = scheduled_dt.isoformat()
        
        # Insert into published_queue
        pub_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO published_queue (id, pending_review_id, selected_caption, scheduled_at, status, created_at)
            VALUES (?, ?, ?, ?, 'queued', ?)
        """, (pub_id, id, action_data.selected_caption, scheduled_time, now_str))
        
        print(f"Story {id} approved. AI Scheduled to post at {scheduled_time} (Auto-spaced after previous queue).")
        
    elif action_data.action == "reject":
        # Simply mark as rejected
        cursor.execute("UPDATE pending_review SET status = 'rejected' WHERE id = ?", (id,))
        print(f"Story {id} rejected and archived.")
        
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'approve' or 'reject'.")
        
    conn.commit()
    conn.close()
    
    # Run the refill pipeline in background to keep queue count at 10 automatically!
    background_tasks.add_task(run_refill_pipeline)
    
    return {"status": "success", "message": f"Story successfully {action_data.action}ed."}

@app.post("/api/refill")
def trigger_refill(background_tasks: BackgroundTasks):
    """Triggers an asynchronous refill of the dashboard queue."""
    background_tasks.add_task(run_refill_pipeline)
    return {"status": "success", "message": "Queue refill triggered in background."}

@app.post("/api/publish/due")
def trigger_publishing(background_tasks: BackgroundTasks):
    """Triggers an asynchronous scan and publication of scheduled due posts."""
    background_tasks.add_task(publish_due_posts)
    return {"status": "success", "message": "Publisher scanner triggered in background."}

class UserSubmission(BaseModel):
    raw_text: str
    location: Optional[str] = "Anonymous"
    category: Optional[str] = "General"

@app.post("/api/submissions")
def create_user_submission(submission: UserSubmission, background_tasks: BackgroundTasks):
    """Saves a follower's anonymous confession, runs de-duplication, and schedules a refill."""
    if not submission.raw_text.strip() or len(submission.raw_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Confession text must be at least 20 characters long.")
        
    sub_uuid = str(uuid.uuid4())
    source_id = f"user_sub_{sub_uuid[:8]}"
    
    # Formulate context header if location/category is provided
    combined_text = f"[{submission.category} in {submission.location}] {submission.raw_text}"
    
    # Run the standard deduplication ingestion pipeline
    success = ingest_single_story(
        source="user_submission",
        source_id=source_id,
        raw_text=combined_text,
        author="anonymous",
        url="user_submit"
    )
    
    if not success:
        return {
            "status": "success",
            "message": "Thank you for your submission! Our team is reviewing it.",
            "duplicate": True
        }
        
    # Trigger an asynchronous queue refill so that if we have fewer than 10 cards,
    # this user submission immediately gets promoted to the dashboard!
    background_tasks.add_task(run_refill_pipeline)
    
    return {
        "status": "success",
        "message": "Confession submitted successfully and sent to the editorial pipeline!",
        "duplicate": False
    }
