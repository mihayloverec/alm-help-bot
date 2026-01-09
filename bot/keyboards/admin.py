from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Обновить регламент")]
        ],
        resize_keyboard=True
    )
