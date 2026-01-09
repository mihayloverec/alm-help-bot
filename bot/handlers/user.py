from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from bot.services.openai_svc import OpenAIService
from bot.services.qdrant import QdrantService
from bot.services.cache import CacheService
from bot.services.indexer import IndexerService

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
    # Simple auth check (naive)
    # if message.from_user.id not in ADMINS: return
    await message.answer("Начинаю обновление базы знаний и очистку кэша...")
    await cache_svc.clear_all_answers()
    await indexer.run_indexing()
    await message.answer("Обновление завершено.")

@router.message(F.text)
async def handle_question(message: Message, 
                          openai_svc: OpenAIService,
                          qdrant_svc: QdrantService,
                          cache_svc: CacheService):
    question = message.text
    user_id = message.from_user.id
    
    # 1. Check Cache
    cached_answer = await cache_svc.get_answer(question)
    if cached_answer:
        await message.answer(f"{cached_answer}") # (из кэша)
        await cache_svc.log_question(user_id, question, cached_answer)
        return

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

    # 4. Reply & Cache
    await message.answer(answer)
    await cache_svc.set_answer(question, answer)
    await cache_svc.log_question(user_id, question, answer)
