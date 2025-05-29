from functools import wraps
from aiogram.types import Message
from bot.database.db_adapter import db_adapter as db
from bot.config import logger

def user_exists_check():
    def decorator(func):
        @wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            user_id = message.from_user.id
            
            try:
                # Проверяем существование пользователя в БД
                if not await db.user_exists(user_id):
                    logger.info(f"Пользователь {user_id} не найден в БД")
                    await message.answer(
                        "⚠️ Для использования бота необходимо выполнить команду /start"
                    )
                    return
                
                # Если пользователь существует, выполняем основную функцию
                return await func(message, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Ошибка при проверке пользователя {user_id}: {e}")
                await message.answer("❌ Произошла ошибка. Попробуйте позже.")
                
        return wrapper
    return decorator 