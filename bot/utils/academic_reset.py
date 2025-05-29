"""
Copyright (c) 2023-2024 Gargun Daniil
Telegram: @Daniilgargun (https://t.me/Daniilgargun)
Contact ID: 1437368782
All rights reserved.

Несанкционированное использование, копирование или распространение 
данного программного обеспечения запрещено.
"""

import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from bot.database.db_adapter import db_adapter as db
from bot.utils.notifications import AdminNotifier
from bot.config import logger

class AcademicYearReset:
    """Класс для сброса данных пользователей в начале нового учебного года"""
    
    def __init__(self, bot: Bot = None):
        self.bot = bot
        self.admin_notifier = AdminNotifier(bot) if bot else None
    
    async def check_and_reset(self) -> bool:
        """
        Проверяет текущую дату и сбрасывает данные пользователей, 
        если это 1 августа нового учебного года
        """
        current_date = datetime.now()
        
        # Проверяем, 1 августа ли сегодня
        if current_date.month == 8 and current_date.day == 1:
            logger.info("🔄 Обнаружен первый день нового учебного года (1 августа)")
            return await self.reset_users()
        
        return False
    
    async def reset_users(self) -> bool:
        """Сбрасывает данные всех пользователей для нового учебного года"""
        try:
            logger.info("🔄 Начало процесса сброса пользователей для нового учебного года")
            
            # Получаем количество пользователей перед сбросом
            try:
                all_users = await db.get_all_users()
                users_count = len(all_users)
                logger.info(f"📊 Количество пользователей перед сбросом: {users_count}")
            except Exception as e:
                logger.error(f"❌ Ошибка при получении списка пользователей: {e}")
                users_count = "неизвестно"
            
            # Выполняем резервное копирование таблицы пользователей
            backup_result = await self._backup_users_table()
            if not backup_result:
                logger.error("❌ Ошибка при создании резервной копии. Сброс отменен.")
                if self.admin_notifier:
                    await self.admin_notifier.notify_critical_error(
                        "Не удалось создать резервную копию таблицы пользователей",
                        "Сброс пользователей (новый учебный год)"
                    )
                return False
            
            # Сброс выбранных групп и преподавателей
            try:
                logger.info("🔄 Сброс выбранных групп и преподавателей")
                query = """
                UPDATE user_settings 
                SET selected_group = NULL, selected_teacher = NULL
                """
                db.db.execute_query(query)
                logger.info("✅ Выбранные группы и преподаватели успешно сброшены")
            except Exception as e:
                logger.error(f"❌ Ошибка при сбросе групп и преподавателей: {e}")
                if self.admin_notifier:
                    await self.admin_notifier.notify_critical_error(
                        f"Ошибка при сбросе групп и преподавателей: {e}",
                        "Сброс пользователей (новый учебный год)"
                    )
                return False
            
            # Удаляем неактивных пользователей
            try:
                # В будущем можно добавить логику удаления неактивных пользователей
                # по времени последней активности
                logger.info("ℹ️ Очистка неактивных пользователей пропущена")
            except Exception as e:
                logger.error(f"❌ Ошибка при удалении неактивных пользователей: {e}")
            
            # Уведомление администраторов
            if self.admin_notifier:
                reset_message = (
                    "🔄 <b>Сброс данных для нового учебного года</b>\n\n"
                    f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                    f"👥 Пользователей до сброса: {users_count}\n"
                    "✅ Выбранные группы и преподаватели сброшены\n"
                    "💾 Резервная копия создана\n\n"
                    "<i>Новый учебный год успешно начат!</i>"
                )
                await self.admin_notifier.send_to_all_admins(reset_message)
            
            logger.info("✅ Сброс пользователей для нового учебного года успешно завершен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при сбросе пользователей: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            
            if self.admin_notifier:
                await self.admin_notifier.notify_critical_error(
                    f"Критическая ошибка при сбросе пользователей: {e}",
                    "Сброс пользователей (новый учебный год)"
                )
            return False
    
    async def _backup_users_table(self) -> bool:
        """Создает резервную копию таблицы пользователей"""
        try:
            logger.info("🔄 Создание резервной копии таблицы пользователей")
            
            # Получаем текущую дату для имени резервной копии
            backup_date = datetime.now().strftime("%Y%m%d")
            
            # Создаем резервную копию таблицы пользователей
            user_tables_backup = f"""
            CREATE TABLE IF NOT EXISTS users_backup_{backup_date} AS 
                SELECT * FROM users;
            CREATE TABLE IF NOT EXISTS user_settings_backup_{backup_date} AS 
                SELECT * FROM user_settings;
            """
            db.db.execute_query(user_tables_backup)
            
            # Проверяем, что резервные копии созданы
            tables = db.db.execute_query(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND 
                (name=? OR name=?)
                """, 
                (f"users_backup_{backup_date}", f"user_settings_backup_{backup_date}")
            )
            
            if len(tables) == 2:
                logger.info(f"✅ Резервные копии таблиц успешно созданы (суффикс: {backup_date})")
                return True
            else:
                logger.error(f"❌ Ошибка при создании резервных копий. Создано {len(tables)} из 2 таблиц.")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при создании резервной копии: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            return False


# Функция для ручного запуска сброса данных
async def manual_reset(bot: Bot = None) -> bool:
    """Ручной запуск сброса данных пользователей"""
    reset_manager = AcademicYearReset(bot)
    return await reset_manager.reset_users()


# Если скрипт запущен напрямую
if __name__ == "__main__":
    async def test_reset():
        """Тестовый запуск сброса данных"""
        logger.info("🧪 Запуск тестового сброса данных пользователей")
        reset_result = await manual_reset()
        logger.info(f"✅ Результат сброса: {'успешно' if reset_result else 'ошибка'}")
    
    # Запускаем тестовый сброс
    asyncio.run(test_reset()) 