import asyncio
import signal
import sys
from aiogram import Bot, Dispatcher
from bot.config import config, logger
from bot.handlers import main_router, register_handlers
from bot.services.scheduler import start_scheduler
from bot.middleware.rate_limit import RateLimitMiddleware
from bot.middleware.spam_protection import SpamProtection
from bot.middleware.performance import PerformanceMiddleware
from bot.services.monitoring import monitor
from bot.services.parser import ScheduleParser
from bot.utils.recovery import create_recovery_manager
from bot.utils.notifications import AdminNotifier
import os

class BotApp:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dp = Dispatcher()
        self.tasks = []
        self.is_running = True
        self.notifier = AdminNotifier(self.bot)

    async def setup(self):
        """Настройка бота и middleware"""
        # Подключаем middleware
        self.dp.message.middleware(RateLimitMiddleware())
        self.dp.message.middleware(SpamProtection())
        self.dp.message.middleware(PerformanceMiddleware())
        
        # Регистрация обработчиков
        register_handlers(self.dp)
        
        # Уведомляем о запуске
        await self.notifier.notify_startup()

    async def start(self):
        """Запуск всех сервисов бота"""
        await self.setup()
        
        # Создаем и запускаем планировщик в отдельной задаче
        scheduler_task = asyncio.create_task(start_scheduler(self.bot))
        self.tasks.extend([
            asyncio.create_task(self.metrics_collector()),
            scheduler_task
        ])
        
        logger.info("Bot services started")
        self.notifier.log_to_file("Сервисы бота запущены", "INFO")

    async def stop(self):
        """Корректное завершение работы бота"""
        logger.info("Shutting down bot...")
        self.is_running = False
        
        # Отменяем все фоновые задачи
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Уведомляем о завершении
        await self.notifier.send_admin_message("Бот завершает работу", "INFO")
        
        # Закрываем сессию бота
        await self.bot.session.close()
        logger.info("Bot shutdown complete")
        self.notifier.log_to_file("Бот остановлен", "INFO")

    async def metrics_collector(self):
        """Периодический сбор метрик"""
        while self.is_running:
            try:
                await monitor.collect_metrics()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collector: {e}")
                await asyncio.sleep(5)

async def main():
    """Основная функция запуска бота"""
    app = BotApp()
    notifier = app.notifier
    
    try:
        # Создание менеджера восстановления
        async def restart_bot():
            logger.info("🔄 Перезапуск бота...")
            await app.bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(5)
            os.execv(sys.executable, ['python'] + sys.argv)
            
        recovery_manager = create_recovery_manager(restart_bot, notifier)
        
        # Загрузка предыдущего состояния
        previous_state = await recovery_manager.load_state()
        if previous_state and not previous_state.get('was_clean_shutdown'):
            warning_msg = "⚠️ Обнаружено некорректное завершение бота"
            logger.warning(warning_msg)
            await notifier.send_admin_message(warning_msg, "WARNING")

        try:
            # Запуск бота
            await app.start()
            await app.dp.start_polling(app.bot)
        except Exception as e:
            await recovery_manager.handle_error(e)
            raise

    except Exception as e:
        error_msg = f"❌ Критическая ошибка: {e}"
        logger.error(error_msg)
        await notifier.notify_critical_error(e, "Запуск бота")
        sys.exit(1)

    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)