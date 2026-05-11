import os
import uuid
import random
import hashlib
from typing import List, Dict, Any, Optional
import google.generativeai as genai
try:
    import praw
except ImportError:
    praw = None

from ..config import settings
from ..database import insert_raw_story, match_stories

# Authentic pre-seeded stories for testing & initial dashboard population
PRE_SEEDED_STORIES = [
    {
        "source": "seed_data",
        "source_id": "seed_001",
        "raw_text": "I came to Dallas for my Masters in Computer Science. Rent is $800 but my roommates are putting cooking video songs in Telugu with full sound on the speaker at 2 AM. When I ask them to lower it, they say 'bhayya you should adjust, this is student life'. I am crying.",
        "author": "DallasMS_Student",
        "url": "https://reddit.com/r/msinus/seed_001"
    },
    {
        "source": "seed_data",
        "source_id": "seed_002",
        "raw_text": "My consultancy manager in New Jersey promised me to run my H1B payroll on time. It has been 3 months and I did not receive any salary. Whenever I call him, he says 'the client did not pay yet, please hold on'. I have to pay my OPT health insurance and rent. Any suggestions on legal action?",
        "author": "H1B_Survivor_NJ",
        "url": "https://reddit.com/r/h1b/seed_002"
    },
    {
        "source": "seed_data",
        "source_id": "seed_003",
        "raw_text": "I met a girl through a Telugu matchmaking site. Her family is asking for green card holder only. I have a stable job in Chicago with an approved I-140 on H1B but my priority date is years away. She rejected me saying 'H1B is insecure, my sister got GC holder from Dallas'. Is marriage only about visa status now?",
        "author": "Chicago_Techie",
        "url": "https://reddit.com/r/TeluguNRIs/seed_003"
    },
    {
        "source": "seed_data",
        "source_id": "seed_004",
        "raw_text": "Dallas Desi grocery stores are selling 5kg Sona Masoori rice for $25 now. Last year it was $14. On top of that, roommates are eating 4 times a day. We bought 2 bags last week and both are already finished. House meeting decided to put labels on food packages. It feels like hostel rooms in Hyderabad again.",
        "author": "RiceLover_Dallas",
        "url": "https://reddit.com/r/msinus/seed_004"
    },
    {
        "source": "seed_data",
        "source_id": "seed_005",
        "raw_text": "Manager calls me at 9 PM EST for 'urgent code deployment'. When I say I finished my 8 hours, he says 'you are on H1B, remember we are processing your green card sponsorship'. This is literal blackmail in corporate style. I want to shift companies but market is very bad.",
        "author": "OPT_Developer_Frustrated",
        "url": "https://reddit.com/r/h1b/seed_005"
    }
]

def get_text_embedding(text: str) -> List[float]:
    """
    Generates a 768-dimension float vector for semantic search.
    If GEMINI_API_KEY is not configured, generates a deterministic mock vector 
    using the text hash so that de-duplication testing works offline.
    """
    if not settings.GEMINI_API_KEY:
        # Create a deterministic mock vector from md5 hash
        h = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        random.seed(h)
        return [random.uniform(-1.0, 1.0) for _ in range(768)]
        
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Gemini Embedding API failed: {e}. Falling back to deterministic mock vectors.")
        h = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        random.seed(h)
        return [random.uniform(-1.0, 1.0) for _ in range(768)]

def ingest_single_story(source: str, source_id: str, raw_text: str, author: Optional[str] = None, url: Optional[str] = None) -> bool:
    """
    Handles semantic deduplication and inserts the story if it's unique.
    Returns True if ingested, False if duplicate or skipped.
    """
    # 1. Generate text embedding
    embedding = get_text_embedding(raw_text)
    
    # 2. Perform Cosine Similarity matching in local DB
    # We use a threshold of 0.85 (85% similar) to catch story duplicates
    matches = match_stories(embedding, similarity_threshold=0.85, match_count=1)
    if matches:
        print(f"Skipping story [{source_id}] - Semantically duplicate to existing story ID: {matches[0]['id']} (Similarity: {matches[0]['similarity']:.2%})")
        return False
        
    # 3. Create unique UUID and insert
    story_id = str(uuid.uuid4())
    success = insert_raw_story(story_id, source, source_id, raw_text, author, url, embedding)
    if success:
        print(f"Successfully ingested story [{source_id}] from {source}!")
    return success

def run_scout_agent():
    """Scout Agent entry point. Connects to Reddit if PRAW is available, otherwise uses pre-seeds/mock data."""
    print("Scout Agent initiated...")
    
    # Seed local DB first if empty
    print("Seeding initial high-quality test stories...")
    seed_count = 0
    for seed in PRE_SEEDED_STORIES:
        if ingest_single_story(seed["source"], seed["source_id"], seed["raw_text"], seed["author"], seed["url"]):
            seed_count += 1
    print(f"Completed seeding: {seed_count} stories added.")

    # Reddit scraping check
    if praw and settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
        print("Reddit PRAW API Credentials found! Connecting to Reddit...")
        try:
            reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT
            )
            
            subreddits = ["msinus", "h1b", "TeluguNRIs"]
            for sub_name in subreddits:
                print(f"Scouting r/{sub_name} rising posts...")
                subreddit = reddit.subreddit(sub_name)
                # Fetch rising submissions
                for submission in subreddit.rising(limit=10):
                    # Filter for self-text posts with length > 50 characters
                    if submission.is_self and len(submission.selftext) > 50:
                        ingest_single_story(
                            source="reddit",
                            source_id=submission.id,
                            raw_text=submission.selftext,
                            author=str(submission.author),
                            url=submission.url
                        )
        except Exception as e:
            print(f"Reddit scouting encountered an error: {e}")
    else:
        print("Reddit PRAW credentials not set (or praw not installed). Skipping real-time Reddit crawling.")
        
        # Synthesize brand-new dynamic raw confessions using Gemini to allow infinite testing!
        if settings.GEMINI_API_KEY:
            print("Gemini API key is configured. Synthesizing 3 brand-new unique anonymous confessions for local testing...")
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                topics = [
                    "gossip about a consultancy manager named Prasad who is blackmailing an OPT student named Srinu for running fake payrolls in New Jersey",
                    "hilarious roommate fight in Chicago where a guy named Bunty cooks smelly non-veg curry on Thursday, which is a strictly veg day for his flatmate Chinna, and now they are dividing the fridge into physical borders",
                    "matchmaking marriage proposal drama in Dallas where a girl named Swapna rejected a techie named Akhil because his I-140 priority date is late, and Akhil found out Swapna married a local motel owner",
                    "corporate tea about an onshore manager named Bobby who holds status calls at 11 PM EST just to brag about his golf skills to scared H1B OPT developers",
                    "funny dating drama in Bay Area where a girl named Harika went on a boba date with Akhil, who split a $12 bill down to the exact penny and Venmo requested her while driving a Model Y",
                    "Masters student named Kalyan in London who is secretly working cash-in-hand shifts at a local off-license grocery and hid in the store room when inspectors visited",
                    "gossip about a consultant named Lucky who lied on his resume about having 8 years of Java experience, got placed in a client, and is now paying a proxy developer named Sandeep to do his daily coding tasks",
                    "petty fight in New York between Telugu housemates over who is stealing the special avakaya pickle bottles sent by mom from Hyderabad",
                    "consultancy scandal where a vendor named Venkat promised H1B sponsorship, took a deposit from Akhila, and then vanished/ghosted her calls",
                    "Matchmaking setup where an NRI guy named Srinu went to Hyderabad for pelli choopulu and the girl asked him what his credit score and 401k balance is before saying hello"
                ]
                
                # Pick 3 random topics to guarantee diversity on every run
                selected_topics = random.sample(topics, 3)
                
                for idx, topic in enumerate(selected_topics):
                    prompt = f"""
                    Write a highly realistic, raw, first-person anonymous confession written in simple English by a Telugu NRI student or IT professional.
                    Topic context: {topic}.
                    Focus on making it sound extremely authentic, emotional, raw, and full of natural frustration or humor.
                    Do NOT include any hashtags, titles, or intros. Return ONLY the raw story confession text itself, around 80 to 120 words.
                    """
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                    raw_text = response.text.strip()
                    
                    if raw_text:
                        sub_id = f"synth_{uuid.uuid4().hex[:8]}"
                        ingest_single_story(
                            source="gemini_synthesizer",
                            source_id=sub_id,
                            raw_text=raw_text,
                            author="synthetic_user",
                            url="gemini_synth"
                        )
            except Exception as e:
                print(f"Failed to synthesize dynamic confessions: {e}")
        else:
            print("GEMINI_API_KEY not configured. Cannot run dynamic confession generator fallback.")

if __name__ == "__main__":
    run_scout_agent()
