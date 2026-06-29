from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    BOT_TOKEN: str
    # Used for embeddings (OpenRouter has no embeddings endpoint).
    OPENAI_API_KEY: str
    # Used for chat completions via OpenRouter.
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    ADMIN_IDS: List[int] = []
    
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    # Optional: when set, the bot authenticates to Qdrant with this key
    # (must match QDRANT__SERVICE__API_KEY on the Qdrant container).
    QDRANT_API_KEY: Optional[str] = None

    REDIS_URL: str = "redis://redis:6379/0"
    # Optional: when set, used to authenticate to a password-protected Redis.
    REDIS_PASSWORD: Optional[str] = None

    # Max length (in characters) of a user question we will process.
    # Protects against oversized, expensive embedding/LLM requests.
    MAX_QUESTION_LENGTH: int = 1000

    GOOGLE_DOC_ID: str
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
