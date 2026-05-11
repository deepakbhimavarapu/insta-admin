import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Google Gemini Configuration
    GEMINI_API_KEY: str = ""
    
    # Reddit PRAW Configuration (Optional - scraper will fall back to mock or public feeds if empty)
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "SwayamScoutAgent/1.0"
    
    # Target size of the pending review queue
    PENDING_QUEUE_TARGET: int = 10
    
    # Directory to store local image/video assets
    ASSETS_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "public", "assets"))
    
    model_config = SettingsConfigDict(
        env_file=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure assets directory exists for Pillow to output images
os.makedirs(settings.ASSETS_DIR, exist_ok=True)
