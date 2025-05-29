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
                logger.info("Воскресенье: обновление расписания пропущено")
                return

            current_hour = moscow_time.hour
            if not (7 <= current_hour < 19):
                logger.info(f"Время {current_hour}:00 МСК вне диапазона обновления (7:00-19:00)")
                return

            logger.info(f"Начало планового обновления расписания (время МСК: {moscow_time.strftime('%H:%M')})")
            
            # Запускаем парсер в отдельном потоке
            schedule_data, groups_list, teachers_list, error = await self._run_parser_in_thread()

            if error:
                logger.error(f"Ошибка при плановом обновлении: {error}")
                self.error_count += 1
                return

            if not schedule_data or not groups_list or not teachers_list:
                logger.warning("Получены пустые данные при обновлении расписания")
                return

            await self.db.update_schedule(schedule_data)
            await self.db.update_cache_time()
            
            self.last_update = moscow_time
            self.update_count += 1
            
            logger.info(
                f"Плановое обновление завершено успешно в {moscow_time.strftime('%H:%M МСК')}. "
                f"Групп: {len(groups_list)}, "
                f"Преподавателей: {len(teachers_list)}"
            )

        except Exception as e:
            logger.error(f"Ошибка при плановом обновлении расписания: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.error_count += 1

    async def start_scheduling(self):
        """Запуск планировщика"""
        while self._running:
            try:
                await self.update_schedule()
                await asyncio.sleep(300)  # 5 минут
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Остановка планировщика"""
        self._running = False
        self._executor.shutdown(wait=True)

async def start_scheduler(bot):
    """Запуск планировщика"""
    updater = ScheduleUpdater()
    notification_manager = NotificationManager(bot)
    
    try:
        # Запускаем задачи
        update_task = asyncio.create_task(updater.start_scheduling())
        notification_task = asyncio.create_task(notification_manager.start_notifications())
        
        # Ждем выполнения задач
        await asyncio.gather(update_task, notification_task)
        
    except asyncio.CancelledError:
        await updater.stop()
        logger.info("Планировщик остановлен")