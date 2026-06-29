import asyncio
import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings
from bot.handlers import user, admin
from bot.services.openai_svc import OpenAIService
from bot.services.qdrant import QdrantService
from bot.services.cache import CacheService
from bot.services.indexer import IndexerService
from bot.middlewares.throttling import ThrottlingMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    # Initialize Services
    openai_svc = OpenAIService()
    qdrant_svc = QdrantService()
    cache_svc = CacheService()
    indexer_svc = IndexerService(qdrant_svc, openai_svc, cache_svc)

    # Ensure collection exists
    await qdrant_svc.ensure_collection()

    # Dependency Injection (simple dictionary approach for now)
    dp["openai_svc"] = openai_svc
    dp["qdrant_svc"] = qdrant_svc
    dp["cache_svc"] = cache_svc
    dp["indexer"] = indexer_svc
    
    # Anti-flood: limit how often a single user can trigger handlers.
    dp.message.middleware(ThrottlingMiddleware(rate_limit=5, window=10.0))

    # Register Routers
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(indexer_svc.run_indexing, 'interval', weeks=1)
    scheduler.start()

    # Initial Indexing Check (Optional: Run on startup if needed, or rely on command)
    # await indexer_svc.run_indexing()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
