import time
import logging
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Simple in-memory, per-user sliding-window rate limiter.

    Allows at most `rate_limit` messages per `window` seconds for each user.
    When the limit is exceeded the update is dropped (the handler is not
    called) and the user is warned at most once per window.

    In-memory state is fine for a single-process bot. If the bot is ever
    scaled to multiple workers, move this state into Redis.
    """

    def __init__(self, rate_limit: int = 5, window: float = 10.0):
        self.rate_limit = rate_limit
        self.window = window
        self._hits: Dict[int, List[float]] = {}
        self._warned: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        hits = [t for t in self._hits.get(user.id, []) if now - t < self.window]

        if len(hits) >= self.rate_limit:
            self._hits[user.id] = hits  # keep pruned window, don't add this hit
            # Warn at most once per window to avoid amplifying the flood.
            if now - self._warned.get(user.id, 0.0) > self.window:
                self._warned[user.id] = now
                try:
                    await event.answer("⏳ Слишком много запросов. Подождите немного.")
                except Exception:
                    logger.debug("Failed to send throttle warning", exc_info=True)
            return None  # drop the update

        hits.append(now)
        self._hits[user.id] = hits
        return await handler(event, data)
