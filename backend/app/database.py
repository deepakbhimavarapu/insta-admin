import sqlite3
import json
import os
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Path to the local SQLite database file (placed in the root of the project)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "swayam.db"))

def get_db_connection() -> sqlite3.Connection:
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables accessing columns by name
    return conn

def init_db():
    """Initializes the database schema if the tables do not already exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. RAW_STORIES: Store stories crawled from Reddit/Forms
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_stories (
        id TEXT PRIMARY KEY,               -- UUID string
        source TEXT NOT NULL,              -- 'reddit', 'google_forms', etc.
        source_id TEXT UNIQUE,             -- External post ID (to avoid duplicates)
        raw_text TEXT NOT NULL,
        author TEXT,
        url TEXT,
        embedding TEXT,                    -- JSON string representation of float vector list
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processed', 'ignored'
        created_at TEXT NOT NULL
    )
    """)

    # 2. PENDING_REVIEW: The 10-Story Dashboard Queue
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_review (
        id TEXT PRIMARY KEY,               -- UUID string
        raw_story_id TEXT,                 -- Foreign key (loose association)
        adapted_text TEXT NOT NULL,        -- Tanglish version
        tone_location TEXT,                -- e.g., 'Dallas', 'NJ'
        graphic_urls TEXT NOT NULL,        -- JSON string list of local image file paths
        caption_options TEXT NOT NULL,     -- JSON string list of caption options
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
        created_at TEXT NOT NULL,
        FOREIGN KEY (raw_story_id) REFERENCES raw_stories (id) ON DELETE SET NULL
    )
    """)

    # 3. PUBLISHED_QUEUE: Automated publishing schedules
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS published_queue (
        id TEXT PRIMARY KEY,               -- UUID string
        pending_review_id TEXT NOT NULL,   -- Foreign key
        selected_caption TEXT NOT NULL,
        scheduled_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued', -- 'queued', 'publishing', 'published', 'failed'
        instagram_post_id TEXT,
        error_message TEXT,
        published_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (pending_review_id) REFERENCES pending_review (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes the cosine similarity between two numeric vectors."""
    arr1 = np.array(v1)
    arr2 = np.array(v2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))

def match_stories(query_embedding: List[float], similarity_threshold: float = 0.85, match_count: int = 5) -> List[Dict[str, Any]]:
    """
    Compares query embedding with existing story embeddings in raw_stories.
    Returns similar stories that exceed the similarity_threshold.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query all raw stories that have an embedding
    cursor.execute("SELECT id, raw_text, embedding FROM raw_stories WHERE embedding IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    
    matches = []
    for row in rows:
        try:
            stored_vector = json.loads(row["embedding"])
            similarity = cosine_similarity(query_embedding, stored_vector)
            if similarity >= similarity_threshold:
                matches.append({
                    "id": row["id"],
                    "raw_text": row["raw_text"],
                    "similarity": similarity
                })
        except Exception as e:
            # Skip invalid embeddings gracefully
            continue
            
    # Sort matches in descending order of similarity
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches[:match_count]

def insert_raw_story(story_id: str, source: str, source_id: Optional[str], raw_text: str, author: Optional[str], url: Optional[str], embedding: Optional[List[float]]) -> bool:
    """Inserts a new crawled raw story into the database. Returns True if successful, False if duplicate."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    embedding_str = json.dumps(embedding) if embedding else None
    now_str = datetime.now(timezone.utc).isoformat()
    
    try:
        cursor.execute("""
        INSERT INTO raw_stories (id, source, source_id, raw_text, author, url, embedding, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (story_id, source, source_id, raw_text, author, url, embedding_str, now_str))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Avoid duplicate ingestion if source_id is already present
        return False
    finally:
        conn.close()

def get_pending_review_count() -> int:
    """Returns the current number of pending items in the review queue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pending_review WHERE status = 'pending'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def insert_pending_review(review_id: str, raw_story_id: Optional[str], adapted_text: str, tone_location: str, graphic_urls: List[str], caption_options: List[str]):
    """Inserts an AI-processed story into the pending review table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
    INSERT INTO pending_review (id, raw_story_id, adapted_text, tone_location, graphic_urls, caption_options, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (review_id, raw_story_id, adapted_text, tone_location, json.dumps(graphic_urls), json.dumps(caption_options), now_str))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Local database initialized successfully at:", DB_PATH)
