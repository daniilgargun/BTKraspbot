import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from datetime import datetime, timezone, timedelta
from bot.services.parser import ScheduleParser
from bot.services.database import Database
from bot.config import logger
from bot.services.notifications import NotificationManager

class ScheduleUpdater:
    def __init__(self):
        self.parser = ScheduleParser()
        self.db = Database()
        self.last_update = None
        self.update_count = 0
        self.error_count = 0
        self._running = True
        self._executor = ThreadPoolExecutor(max_workers=1)

    def get_moscow_time(self):
        """Получение текущего времени в Москве"""
        moscow_tz = timezone(timedelta(hours=3))
        return datetime.now(moscow_tz)

    async def _run_parser_in_thread(self):
        """Запуск парсера в отдельном потоке"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(asyncio.run, self.parser.parse_schedule())
        )

    async def update_schedule(self):
        """Обновление расписания"""
        try:
            moscow_time = self.get_moscow_time()
            
            if moscow_time.weekday() == 6:
                logger.info("📋 Воскресенье: обновление расписания пропущено")
                return

            current_hour = moscow_time.hour
            if not (7 <= current_hour < 19):
                logger.info(f"⏱️ Время {current_hour}:00 МСК вне диапазона обновления (7:00-19:00)")
                return

            logger.info(f"🔄 Начало планового обновления расписания (время МСК: {moscow_time.strftime('%H:%M')})")
            
            # Запускаем парсер в отдельном потоке
            schedule_data, groups_list, teachers_list, error = await self._run_parser_in_thread()

            if error:
                logger.error(f"❌ Ошибка при плановом обновлении: {error}")
                self.error_count += 1
                return

            if not schedule_data or not groups_list or not teachers_list:
                logger.warning("⚠️ Получены пустые данные при обновлении расписания")
                return

            # Обновляем расписание в базе данных
            groups_count = len(groups_list) if groups_list else 0
            teachers_count = len(teachers_list) if teachers_list else 0
            logger.info(f"📊 Обновление расписания в базе данных (групп: {groups_count}, преподавателей: {teachers_count})")
            
            # Проверка наличия данных в schedule_data
            date_count = len(schedule_data) if schedule_data else 0
            if date_count > 0:
                logger.info(f"📅 Найдено {date_count} дат в новом расписании")
                
                # Обновляем расписание в базе данных
                update_success = await self.db.update_schedule(schedule_data)
                if update_success:
                    logger.info("✅ Расписание успешно обновлено в базе данных")
                else:
                    logger.error("❌ Ошибка при обновлении расписания в базе данных")
                    return
                    
                # Обновляем время кэша
                cache_update_success = await self.db.update_cache_time()
                if cache_update_success:
                    logger.info("✅ Время кэша успешно обновлено")
                else:
                    logger.warning("⚠️ Не удалось обновить время кэша")
            else:
                logger.warning("⚠️ Расписание не содержит дат, обновление пропущено")
                return

            # Устанавливаем флаг обновления для уведомлений
            if hasattr(self, 'notification_manager') and self.notification_manager:
                logger.info("🔔 Запуск проверки новых дат после обновления расписания")
                try:
                    await self.notification_manager.check_schedule_updates()
                    logger.info("✅ Проверка и отправка уведомлений успешно выполнены")
                except Exception as notif_error:
                    logger.error(f"❌ Ошибка при проверке и отправке уведомлений: {notif_error}")
                    import traceback
                    logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            else:
                logger.warning("⚠️ Менеджер уведомлений не настроен, уведомления не отправлены")
            
            self.last_update = moscow_time
            self.update_count += 1
            
            logger.info(
                f"✅ Плановое обновление завершено успешно в {moscow_time.strftime('%H:%M МСК')}. "
                f"Групп: {groups_count}, "
                f"Преподавателей: {teachers_count}"
            )

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при плановом обновлении расписания: {e}")
            import traceback
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            self.error_count += 1

    async def start_scheduling(self):
        """Запуск планировщика"""
        logger.info("🚀 Запуск планировщика обновления расписания")
        while self._running:
            try:
                await self.update_schedule()
                logger.info("⏱️ Ожидание 5 минут до следующего обновления...")
                await asyncio.sleep(300)  # 5 минут
            except asyncio.CancelledError:
                logger.info("🛑 Планировщик был отменен")
                break
            except Exception as e:
                logger.error(f"❌ Критическая ошибка в планировщике: {e}")
                import traceback
                logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
                logger.info("⏱️ Ожидание 5 секунд до повторной попытки...")
                await asyncio.sleep(5)

    async def stop(self):
        """Остановка планировщика"""
        logger.info("🛑 Остановка планировщика обновления расписания")
        self._running = False
        self._executor.shutdown(wait=True)
        logger.info("✅ Планировщик успешно остановлен")

async def start_scheduler(bot):
    """Запуск планировщика"""
    notification_manager = NotificationManager(bot)
    updater = ScheduleUpdater()
    updater.notification_manager = notification_manager  # Передаем менеджер уведомлений
    
    try:
        # Запускаем задачи
        update_task = asyncio.create_task(updater.start_scheduling())
        notification_task = asyncio.create_task(notification_manager.start_notifications())
        
        # Ждем выполнения задач
        await asyncio.gather(update_task, notification_task)
        
    except asyncio.CancelledError:
        await updater.stop()
        await notification_manager.stop()
        logger.info("Планировщик и система уведомлений остановлены")