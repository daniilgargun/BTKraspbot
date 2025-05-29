from datetime import datetime
from typing import List, Dict
from aiogram import Bot
from bot.config import config, logger,WEEKDAYS, MONTHS
from bot.database.db_adapter import db_adapter as db
from bot.middlewares.schedule_formatter import ScheduleFormatter
from bot.utils.academic_reset import AcademicYearReset
import asyncio
import time

class NotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.formatter = ScheduleFormatter()
        self._running = True
        self._initialize_tables()
        self.academic_reset = AcademicYearReset(bot)

    def _initialize_tables(self):
        """Инициализация необходимых таблиц"""
        try:
            # Создаем таблицу для хранения последних проверенных дат
            query = """
            CREATE TABLE IF NOT EXISTS last_checked_dates (
                id INTEGER PRIMARY KEY,
                dates TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            db.db.execute_query(query)
            logger.info("Таблица last_checked_dates успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации таблиц: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")

    async def start_notifications(self):
        """Запуск проверки уведомлений"""
        logger.info("🔔 Запуск системы мониторинга")
        while self._running:
            try:
                # Проверяем новый учебный год
                await self._check_academic_year_reset()
                
                # Проверяем существующие данные при старте
                logger.info("⏱️ Работа системы мониторинга. Ожидание обновлений расписания...")
                await asyncio.sleep(300)  # Ждем 5 минут
            except Exception as e:
                logger.error(f"❌ Критическая ошибка в системе мониторинга: {e}")
                await asyncio.sleep(5)

    async def _check_academic_year_reset(self):
        """Проверка необходимости сброса данных для нового учебного года"""
        try:
            # Проверяем, нужно ли выполнить сброс для нового учебного года
            reset_performed = await self.academic_reset.check_and_reset()
            
            if reset_performed:
                logger.info("🎓 Выполнен сброс данных для нового учебного года")
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке необходимости сброса учебного года: {e}")

    async def stop(self):
        """Остановка проверки уведомлений"""
        logger.info("🛑 Остановка системы мониторинга")
        self._running = False

    async def check_schedule_updates(self):
        """Проверка обновлений расписания (вызывается от парсера)"""
        logger.info("🔍 Проверка новых дат в расписании после обновления...")
        result = await self.check_and_send_notifications()
        if result:
            logger.info("✅ Проверка и отправка уведомлений завершены успешно")
        else:
            logger.warning("⚠️ Проверка и отправка уведомлений завершены с предупреждениями")
        
    async def check_and_send_notifications(self):
        """
        Проверка и отправка уведомлений о новых датах в расписании.
        Возвращает True, если проверка прошла без ошибок (даже если новых дат нет).
        """
        success = False
        try:
            logger.info("📊 Начало проверки новых дат в расписании")
            
            # Получаем текущее расписание
            schedule = await db.get_schedule()
            if not schedule:
                logger.info("❌ Расписание пусто, нет данных для проверки уведомлений")
                return False

            logger.info(f"📋 Получено расписание с {len(schedule)} датами")
            
            # Получаем даты из расписания
            current_dates = set()
            invalid_dates = []
            
            # Словарь для преобразования месяцев
            month_mapping = {
                'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04',
                'мая': '05', 'май': '05', 'июн': '06', 'июл': '07', 'авг': '08',
                'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12',
            }
            
            for date_str in schedule.keys():
                try:
                    # Попытка распознать формат DD.MM.YYYY
                    if '.' in date_str:
                        datetime.strptime(date_str, "%d.%m.%Y")
                        current_dates.add(date_str)
                    # Попытка распознать формат DD-MMM
                    elif '-' in date_str:
                        day, month_abbr = date_str.split('-')
                        day = day.strip()
                        month_abbr = month_abbr.strip().lower()[:3]  # Берем только первые 3 буквы
                        
                        if month_abbr in month_mapping:
                            month_num = month_mapping[month_abbr]
                            year = datetime.now().year
                            
                            # Формируем дату в формате DD.MM.YYYY
                            formatted_date = f"{day.zfill(2)}.{month_num}.{year}"
                            
                            # Проверяем, что дата валидна
                            datetime.strptime(formatted_date, "%d.%m.%Y")
                            
                            logger.info(f"🔄 Преобразована дата: {date_str} -> {formatted_date}")
                            current_dates.add(formatted_date)
                        else:
                            logger.warning(f"⚠️ Неизвестное сокращение месяца: {month_abbr} в дате {date_str}")
                            invalid_dates.append(date_str)
                    else:
                        invalid_dates.append(date_str)
                        logger.warning(f"⚠️ Некорректный формат даты: {date_str}")
                except ValueError as e:
                    invalid_dates.append(date_str)
                    logger.warning(f"⚠️ Ошибка при обработке даты {date_str}: {e}")
                    continue
            
            if invalid_dates:
                logger.warning(f"⚠️ Обнаружено {len(invalid_dates)} дат с некорректным форматом")
            
            logger.info(f"📅 Найдено {len(current_dates)} валидных дат в текущем расписании")
            if current_dates:
                logger.info(f"📅 Примеры дат: {sorted(list(current_dates))[:5]}...")
            
            # Получаем последние проверенные даты
            last_checked = await db.get_last_checked_dates()
            
            if not isinstance(last_checked, list):
                logger.error(f"⚠️ Неверный формат последних проверенных дат: {type(last_checked)}. Ожидался список.")
                last_checked = []
                
            # Логируем полученные даты для отладки
            if last_checked:
                logger.info(f"🔍 Получены проверенные даты: {last_checked[:5]}... (всего: {len(last_checked)})")
            else:
                logger.info("🔍 Список последних проверенных дат пуст")
            
            if not last_checked:
                # Если это первая проверка, сохраняем текущие даты
                logger.info("🆕 Первичная инициализация проверенных дат")
                
                # Преобразуем набор в список для сохранения
                current_dates_list = list(current_dates)
                
                if not current_dates_list:
                    logger.warning("⚠️ Нет валидных дат для сохранения")
                    return False
                    
                logger.info(f"📋 Сохраняем {len(current_dates_list)} текущих дат")
                
                success = await db.update_last_checked_dates(current_dates_list)
                if success:
                    logger.info(f"✅ Сохранено {len(current_dates_list)} дат при первичной инициализации")
                    return True
                else:
                    logger.error("❌ Ошибка при сохранении дат первичной инициализации")
                    return False

            # Преобразуем last_checked в набор для сравнения
            last_checked_set = set(last_checked)
            logger.info(f"🔄 Сравниваем {len(current_dates)} текущих дат с {len(last_checked_set)} проверенными")
            
            # Находим новые даты
            new_dates = current_dates - last_checked_set
            
            if new_dates:
                logger.info(f"🔔 Найдены новые даты: {sorted(list(new_dates))} (всего: {len(new_dates)})")
                
                # Форматируем даты для удобного отображения
                formatted_dates = []
                for date_str in sorted(new_dates):
                    try:
                        date = datetime.strptime(date_str, "%d.%m.%Y")
                        
                        # Получаем день недели
                        weekday_num = date.weekday()  # 0 - понедельник, 6 - воскресенье
                        weekday_names = {
                            0: "понедельник",
                            1: "вторник",
                            2: "среда",
                            3: "четверг",
                            4: "пятница",
                            5: "суббота",
                            6: "воскресенье"
                        }
                        weekday = weekday_names.get(weekday_num, "")
                        
                        # Получаем месяц и форматируем его
                        month_num = date.month
                        months = {
                            1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель',
                            5: 'май', 6: 'июнь', 7: 'июль', 8: 'август',
                            9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
                        }
                        month_name = months.get(month_num, "")
                        
                        # Форматируем дату в нужном формате
                        formatted_date = f"{date.day} {month_name} ({weekday})"
                        formatted_dates.append(formatted_date)
                    except Exception as e:
                        logger.error(f"❌ Ошибка форматирования даты {date_str}: {e}")
                        formatted_dates.append(date_str)
                
                # Создаем текст уведомления
                if formatted_dates:
                    # Отправка уведомлений только пользователям, без администраторов
                    logger.info("📧 Отправка уведомлений только пользователям, администраторы пропущены")
                    
                    # Получаем пользователей с включенными уведомлениями
                    users_with_notifications = await db.get_users_with_notifications()
                    logger.info(f"📊 Найдено {len(users_with_notifications)} пользователей с включенными уведомлениями")
                    
                    if users_with_notifications:
                        # Отправляем уведомления пользователям
                        user_notification_text = (
                            "📅 <b>Новые даты:</b>\n"
                            f"{chr(10).join('• ' + date for date in formatted_dates)}\n\n"
                            "Проверьте расписание, чтобы узнать подробности."
                        )
                        
                        sent_count = 0
                        failed_count = 0
                        start_time = time.time()
                        
                        for user_id in users_with_notifications:
                            try:
                                await self.bot.send_message(
                                    user_id,
                                    user_notification_text,
                                    parse_mode="HTML"
                                )
                                sent_count += 1
                                if sent_count % 10 == 0:  # Логируем каждые 10 отправок
                                    logger.info(f"📤 Отправлено {sent_count}/{len(users_with_notifications)} уведомлений")
                            except Exception as e:
                                failed_count += 1
                                logger.error(f"❌ Ошибка при отправке уведомления пользователю {user_id}: {e}")
                                if failed_count % 10 == 0:  # Логируем каждые 10 ошибок
                                    logger.error(f"⚠️ Накоплено {failed_count} ошибок отправки")
                        
                        duration = time.time() - start_time
                        logger.info(
                            f"📊 Итоги рассылки: {sent_count}/{len(users_with_notifications)} успешно, "
                            f"{failed_count} с ошибками, время: {duration:.2f} сек"
                        )
                    else:
                        logger.info("⚠️ Нет пользователей с включенными уведомлениями")
                else:
                    logger.warning("⚠️ Новые даты найдены, но не удалось отформатировать ни одну из них")
            else:
                logger.info("ℹ️ Новых дат не обнаружено, уведомления не требуются")
                success = True  # Отсутствие новых дат - это нормальная ситуация

            # Обновляем список проверенных дат (всегда обновляем, даже если новых дат нет)
            update_success = await db.update_last_checked_dates(list(current_dates))
            if update_success:
                logger.info(f"✅ Список проверенных дат обновлен ({len(current_dates)} дат)")
                success = True
            else:
                logger.error("❌ Ошибка при обновлении списка проверенных дат")
                success = False

            return success

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при проверке уведомлений: {e}")
            import traceback
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            return False
            
        finally:
            logger.info("📋 Завершена проверка и отправка уведомлений")

    async def check_and_send_notifications_old(self):
        """Проверка и отправка уведомлений о новых датах в расписании"""
        try:
            # Словарь для дней недели по номеру (0 - понедельник, 6 - воскресенье)
            weekday_names = {
                0: "понедельник",
                1: "вторник",
                2: "среда",
                3: "четверг",
                4: "пятница",
                5: "суббота",
                6: "воскресенье"
            }
            
            # Получаем текущее расписание
            schedule = await db.get_schedule()
            if not schedule:
                logger.info("Расписание пусто, нет данных для проверки уведомлений")
                return

            # Получаем даты из расписания
            current_dates = set()
            for date, lessons in schedule.items():
                if lessons:  # Проверяем, что список занятий не пуст
                    current_dates.add(date)
            
            logger.info(f"Текущие даты в расписании: {current_dates}")

            # Получаем последние проверенные даты
            last_checked_dates = await db.get_last_checked_dates()
            last_checked_dates_set = set(last_checked_dates)
            
            logger.info(f"Последние проверенные даты: {last_checked_dates_set}")

            # Находим новые даты
            new_dates = current_dates - last_checked_dates_set
            
            if new_dates:
                logger.info(f"Найдены новые даты в расписании: {new_dates}")
                
                # Форматируем список новых дат с днями недели
                formatted_dates = []
                for date in new_dates:
                    try:
                        # Преобразуем дату в объект datetime
                        if '-' in date:
                            day, month = date.split('-')
                            # Пробуем найти месяц в словаре (полное название или сокращение)
                            month_lower = month.lower()
                            month_num = MONTHS.get(month_lower)
                            
                            # Если не нашли, пробуем использовать первые 3 буквы
                            if not month_num and len(month_lower) > 3:
                                month_short = month_lower[:3]
                                month_num = MONTHS.get(month_short)
                                if month_num:
                                    logger.info(f"Использую сокращение месяца: {month} -> {month_short}")
                            
                            if month_num:
                                date_obj = datetime(datetime.now().year, month_num, int(day))
                                # Получаем номер дня недели (0 - понедельник, 6 - воскресенье)
                                weekday_num = date_obj.weekday()
                                # Получаем название дня недели
                                weekday = weekday_names.get(weekday_num, "")
                                logger.info(f"День недели для {date}: {weekday_num} -> {weekday}")
                                
                                # Используем сокращенную форму месяца (первые 3 буквы)
                                short_month = month[:3] if len(month) > 3 else month
                                
                                # Убираем дефис при форматировании
                                formatted_dates.append(f"{day} {short_month} ({weekday})")
                            else:
                                logger.error(f"Месяц '{month}' не найден в словаре MONTHS")
                                formatted_dates.append(date)
                        else:
                            logger.error(f"Неверный формат даты: {date}")
                            formatted_dates.append(date)
                    except Exception as e:
                        logger.error(f"Ошибка форматирования даты {date}: {e}")
                        formatted_dates.append(date)
                
                logger.info(f"Форматированные даты: {formatted_dates}")
                
                # Получаем пользователей с включенными уведомлениями (notifications_enabled=True)
                users_with_notifications = await db.get_users_with_notifications()
                
                # Формируем текст уведомления для администратора
                admin_notification_text = (
                    "📅 <b>Новые даты:</b>\n"
                    f"{chr(10).join('• ' + date for date in formatted_dates)}\n\n"
                    f"👥 Пользователей с уведомлениями: {len(users_with_notifications)}\n"
                )
                
                # Отправляем уведомление администраторам
                try:
                    for admin_id in config.ADMIN_IDS:
                        try:
                            await self.bot.send_message(
                                admin_id,
                                admin_notification_text
                            )
                            logger.info(f"Уведомление успешно отправлено администратору (ID: {admin_id})")
                        except Exception as e:
                            logger.error(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомлений администраторам: {e}")
                
                # Обновляем список проверенных дат
                await db.update_last_checked_dates(list(current_dates))
                logger.info("Список проверенных дат обновлен")
            else:
                logger.info("Новых дат в расписании не обнаружено")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке и отправке уведомлений: {e}") 