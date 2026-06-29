import redis.asyncio as redis
from bot.config import settings
import hashlib
import json

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,  # None => no auth (unchanged)
            decode_responses=True,
        )
        self.ttl = 60 * 60 * 24 * 7  # 1 week cache
        self.log_max_len = 5000  # cap question_log so it can't grow unbounded

    def _get_key(self, question: str) -> str:
        # Normalize: lowercase, strip
        normalized = question.strip().lower()
        # Hash to keep keys short and clean
        return f"q_cache:{hashlib.md5(normalized.encode()).hexdigest()}"

    async def get_answer(self, question: str) -> str | None:
        key = self._get_key(question)
        return await self.redis.get(key)
        
    async def set_answer(self, question: str, answer: str):
        key = self._get_key(question)
        await self.redis.set(key, answer, ex=self.ttl)

    async def log_question(self, user_id: int, question: str, answer: str):
        """
        Simple logging to a list for now, as requested 'simplified in Redis'.
        """
        entry = json.dumps({
            "user_id": user_id,
            "question": question,
            "answer": answer
        })
        # Push then trim so the log keeps only the most recent N entries,
        # preventing unbounded Redis memory growth.
        pipe = self.redis.pipeline()
        pipe.lpush("question_log", entry)
        pipe.ltrim("question_log", 0, self.log_max_len - 1)
        await pipe.execute()

    async def clear_all_answers(self):
        """Clears all cached answers."""
        keys = []
        async for key in self.redis.scan_iter("q_cache:*"):
           keys.append(key)
        
        if keys:
            await self.redis.delete(*keys)

    async def set_full_text(self, text: str):
        """Stores the full text of the regulation."""
        await self.redis.set("regulations_full_text", text)

    async def get_full_text(self) -> str | None:
        """Retrieves the full text of the regulation."""
        return await self.redis.get("regulations_full_text")
