from datetime import datetime
from typing import List, Dict
from aiogram import Bot
from bot.config import config, logger,WEEKDAYS, MONTHS
from bot.services.database import Database
from bot.middlewares.schedule_formatter import ScheduleFormatter
import asyncio

class NotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.formatter = ScheduleFormatter()
        self._running = True

    async def start_notifications(self):
        """Запуск проверки уведомлений"""
        while self._running:
            try:
                await self.check_and_send_notifications()
                await asyncio.sleep(300)  # 5 минут
            except Exception as e:
                logger.error(f"Ошибка в проверке уведомлений: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Остановка проверки уведомлений"""
        self._running = False

    async def check_and_send_notifications(self):
        """Проверка новых дней в расписании и отправка уведомлений"""
        try:
            # Получаем текущее расписание
            schedule_data = await self.db.get_schedule()
            if not schedule_data:
                return

            # Получаем последнюю проверенную дату
            last_checked_dates = await self.db.get_last_checked_dates()
            
            # Находим новые даты
            new_dates = set(schedule_data.keys()) - set(last_checked_dates)
            if not new_dates:
                return

            # Получаем пользователей с включенными уведомлениями
            users = await self.db.get_users_with_notifications()
            if not users:
                return

            # Форматируем список новых дат с днями недели
            formatted_dates = []
            for date in sorted(new_dates):
                try:
                    # Преобразуем дату в объект datetime
                    if '-' in date:
                        day, month = date.split('-')
                        month_num = MONTHS.get(month.lower())
                        if month_num:
                            date_obj = datetime(datetime.now().year, month_num, int(day))
                            weekday = WEEKDAYS.get(date_obj.strftime('%A').lower())
                            # Убираем дефис при форматировании
                            formatted_dates.append(f"{day} {month} ({weekday})")
                except Exception as e:
                    logger.error(f"Ошибка форматирования даты {date}: {e}")
                    formatted_dates.append(date)

            # Формируем текст уведомления
            notification_text = (
                "🔔 В расписании появились новые даты!\n\n"
                "📅 Новые даты:\n"
                f"{chr(10).join('• ' + date for date in formatted_dates)}\n\n"
                "Используйте меню для просмотра актуального расписания."
            )

            # Отправляем уведомления
            for user in users:
                try:
                    await self.bot.send_message(
                        user['user_id'],
                        notification_text,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Уведомление отправлено пользователю {user['user_id']}")

                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления пользователю {user['user_id']}: {e}")
                    continue

            # Обновляем последние проверенные даты
            await self.db.update_last_checked_dates(list(schedule_data.keys()))
            
        except Exception as e:
            logger.error(f"Ошибка при проверке и отправке уведомлений: {e}") 