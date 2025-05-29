from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

async def setup_commands(bot: Bot):
    """
    Регистрация команд бота, которые будут отображаться в интерфейсе Telegram
    """
    commands = [
        BotCommand(command='/start', description='Перезапустить бота'),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault()) 