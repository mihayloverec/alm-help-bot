from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.config import settings
from bot.services.indexer import IndexerService
from bot.services.cache import CacheService
from bot.keyboards.admin import get_admin_keyboard

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return  # Ignore non-admins silently or reply "Access denied"
        
    await message.answer("Добро пожаловать в админ-панель.", reply_markup=get_admin_keyboard())

@router.message(F.text == "🔄 Обновить регламент")
async def handle_update_kbase(message: Message, indexer: IndexerService, cache_svc: CacheService):
    if not is_admin(message.from_user.id):
        return

    await message.answer("Начинаю обновление базы знаний и очистку кэша...")
    
    try:
        await cache_svc.clear_all_answers()
        await indexer.run_indexing()
        await message.answer("✅ Обновление успешно завершено!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обновлении: {e}")
