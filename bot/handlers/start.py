from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.keyboards.keyboards import get_start_keyboard
from bot.database.db_adapter import db_adapter as db
from bot.config import logger

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username
    
    try:
        logger.info(f"Получена команда /start от пользователя {user_id} (@{username})")
        
        # Проверяем существует ли пользователь в БД
        exists = await db.user_exists(user_id)
        logger.info(f"Проверка существования пользователя {user_id}: {exists}")
        
        if not exists:
            # Если нет - создаем нового пользователя
            logger.info(f"Начинаем создание пользователя {user_id}")
            created = await db.create_user(user_id)
            logger.info(f"Результат создания пользователя {user_id}: {'успешно' if created else 'ошибка'}")
            
            if not created:
                logger.error(f"Не удалось создать пользователя {user_id}")
                await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
                return
        
        await message.answer(
            text="👋 Привет! 🤖 Я бот для просмотра расписания БТК.\n\n⚙️ Вы можете изменить свою роль в меню настроек.",
            reply_markup=get_start_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")