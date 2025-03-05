from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.keyboards.keyboards import get_start_keyboard
from bot.services.database import Database
from bot.config import logger

router = Router()
db = Database()

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    
    try:
        # Проверяем существует ли пользователь в БД
        if not await db.user_exists(user_id):
            # Если нет - создаем нового пользователя
            await db.create_user(user_id)
            logger.info(f"Создан новый пользователь с ID: {user_id}")
        
        await message.answer(
            text="👋 Привет! 🤖 Я бот для просмотра расписания БТК.\n\n⚙️ Вы можете изменить свою роль в меню настроек.",
            reply_markup=get_start_keyboard(user_id)
        )
        
    except Exception as e:
        error_msg = f"Ошибка при обработке команды start: {str(e)}"
        logger.error(error_msg)