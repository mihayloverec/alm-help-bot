import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from bot.config import settings
from bot.services.openai_svc import OpenAIService
from bot.services.qdrant import QdrantService
from bot.services.cache import CacheService
from bot.services.indexer import IndexerService
from bot.handlers.admin import is_admin

logger = logging.getLogger(__name__)

router = Router()

def get_services(bot):
    # Retrieve services from bot context (middleware injection style or direct access)
    # For simplicity, we assume they are injected into bot or accessible via simple dependency container
    # But here we will assume they are initialized in main and passed to router via data
    pass

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я ассистент судьи Лиги Азии. Задай мне вопрос по регламенту.")

@router.message(Command("update_kbase"))
async def cmd_update(message: Message, indexer: IndexerService, cache_svc: CacheService):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администраторам.")
        return

    await message.answer("Начинаю обновление базы знаний и очистку кэша...")
    try:
        await cache_svc.clear_all_answers()
        await indexer.run_indexing()
        await message.answer("✅ Обновление завершено.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обновлении: {e}")

@router.message(F.text)
async def handle_question(message: Message,
                          openai_svc: OpenAIService,
                          qdrant_svc: QdrantService,
                          cache_svc: CacheService):
    question = message.text.strip()
    user_id = message.from_user.id

    # 0. Validate input length to avoid oversized, expensive requests.
    if len(question) > settings.MAX_QUESTION_LENGTH:
        await message.answer(
            f"Вопрос слишком длинный (максимум {settings.MAX_QUESTION_LENGTH} символов). "
            "Сформулируйте, пожалуйста, короче."
        )
        return

    # 1. Check Cache
    cached_answer = await cache_svc.get_answer(question)
    if cached_answer:
        await message.answer(f"{cached_answer}") # (из кэша)
        await cache_svc.log_question(user_id, question, cached_answer)
        return

    try:
        # 2. Search Qdrant (Smart RAG with Fat Chunks)
        # We now use retrieval again because we have "Fat Chunks" (3000 chars) that hold enough context.
        # This saves tokens compared to sending the whole 40k text.
        q_vector = await openai_svc.get_embedding(question)
        relevant_chunks = await qdrant_svc.search(q_vector, limit=5)

        # 3. Generate Answer
        if not relevant_chunks:
            answer = "В регламенте нет информации по данному вопросу."
        else:
            answer = await openai_svc.get_answer(question, relevant_chunks)
    except Exception:
        # Log the full error server-side, but never leak internals to the user.
        logger.exception("Failed to answer question from user %s", user_id)
        await message.answer(
            "Извините, произошла ошибка при обработке вопроса. Попробуйте позже."
        )
        return

    # 4. Reply & Cache
    await message.answer(answer)
    await cache_svc.set_answer(question, answer)
    await cache_svc.log_question(user_id, question, answer)
