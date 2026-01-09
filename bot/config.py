from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    BOT_TOKEN: str
    OPENAI_API_KEY: str
    ADMIN_IDS: List[int] = []
    
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    
    REDIS_URL: str = "redis://redis:6379/0"
    
    GOOGLE_DOC_ID: str
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
