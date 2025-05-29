"""
Copyright (c) 2023-2024 Gargun Daniil
Telegram: @Daniilgargun (https://t.me/Daniilgargun)
Contact ID: 1437368782
All rights reserved.

Несанкционированное использование, копирование или распространение 
данного программного обеспечения запрещено.
"""

from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.user import user_router
from bot.handlers.admin import admin_router

# Создаем главный роутер
main_router = Router()

# Регистрируем все роутеры
main_router.include_router(start_router)
main_router.include_router(user_router)
main_router.include_router(admin_router)

def register_handlers(dp):
    """Регистрация всех обработчиков"""
    dp.include_router(main_router)
    
    # Заменяем Firebase на SQLite
    from bot.services.database import Database
    from bot.database.db_adapter import db_adapter
    
    # Заменяем экземпляр Database на наш адаптер
    Database._instance = db_adapter
    
    return dp

# Экспортируем все необходимые компоненты
__all__ = ['main_router', 'register_handlers']

