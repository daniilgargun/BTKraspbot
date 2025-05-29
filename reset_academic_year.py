#!/usr/bin/env python
"""
Скрипт для ручного сброса данных пользователей при начале нового учебного года.
Использует модуль academic_reset.py для выполнения сброса.
"""

import asyncio
import sys
import os
from aiogram import Bot
from bot.utils.academic_reset import manual_reset
from bot.config import config, logger

async def main():
    """Основная функция"""
    logger.info("🎓 Запуск скрипта сброса данных для нового учебного года")
    
    # Создаем экземпляр бота для уведомлений
    bot = Bot(token=config.BOT_TOKEN)
    
    try:
        # Запускаем процесс сброса
        logger.info("🔄 Начало процесса сброса...")
        result = await manual_reset(bot)
        
        if result:
            logger.info("✅ Сброс данных для нового учебного года успешно завершен")
            print("Сброс данных для нового учебного года успешно завершен")
        else:
            logger.error("❌ Сброс данных завершился с ошибками. Проверьте логи.")
            print("Сброс данных завершился с ошибками. Проверьте логи.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при выполнении сброса: {e}")
        print(f"Критическая ошибка при выполнении сброса: {e}")
        sys.exit(1)
    finally:
        # Закрываем сессию бота
        await bot.session.close()
        
    sys.exit(0)

if __name__ == "__main__":
    # Информация о выполнении
    print("="*60)
    print(" 🎓 СБРОС ДАННЫХ ДЛЯ НОВОГО УЧЕБНОГО ГОДА")
    print("-"*60)
    print(" ВНИМАНИЕ! Этот скрипт выполнит следующие действия:")
    print(" - Создаст резервную копию таблиц пользователей")
    print(" - Сбросит выбранные группы и преподавателей у всех пользователей")
    print(" - Отправит уведомление всем администраторам")
    print("-"*60)
    
    # Запрашиваем подтверждение
    confirm = input("Вы хотите продолжить? (y/n): ")
    if confirm.lower() != 'y':
        print("Операция отменена пользователем.")
        sys.exit(0)
    
    # Запускаем скрипт
    print("Выполнение сброса данных...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Операция прервана пользователем.")
        sys.exit(1) 