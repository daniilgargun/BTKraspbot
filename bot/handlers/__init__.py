from aiogram import Router
from .admin import admin_router
from .user import user_router
from .common import common_router

# Создаем основной роутер
main_router = Router()

# Подключаем все роутеры к основному
main_router.include_router(admin_router)
main_router.include_router(user_router)
main_router.include_router(common_router)

def register_handlers(dp):
    """Регистрация всех обработчиков"""
    dp.include_router(main_router)

# Экспортируем все необходимые компоненты
__all__ = ['main_router', 'register_handlers']

