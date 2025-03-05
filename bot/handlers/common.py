from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import logger

# Создаем роутер для общих команд
common_router = Router()

@common_router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        await message.answer(
            "👋 Привет! Я бот БТК для просмотра расписания.\n"
            "Используйте меню для навигации."
        )
        logger.info(f"Пользователь {message.from_user.id} запустил бота")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@common_router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    try:
        help_text = (
            "📚 *Доступные команды:*\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/schedule - Посмотреть расписание\n"
            "/today - Расписание на сегодня\n"
            "/tomorrow - Расписание на завтра\n\n"
            "ℹ️ Для получения дополнительной информации обратитесь к администратору."
        )
        await message.answer(help_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.") 