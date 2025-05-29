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
import sys
import os
import signal
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from bot.config import config
from bot.handlers import register_handlers
from bot.utils.bot_commands import setup_commands
from bot.utils.notifications import AdminNotifier
from bot.database import db as sqlite_db
from bot.services.scheduler import start_scheduler
from bot.services.notifications import NotificationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotApp:
    def __init__(self):
        self.bot = Bot(
            token=config.BOT_TOKEN, 
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher(storage=MemoryStorage())
        self.admin_notifier = AdminNotifier(self.bot)
        self.notification_manager = NotificationManager(self.bot)
        self.scheduler_task = None
        self.notification_task = None
        self.is_stopping = False
        self.stop_reason = "Штатное завершение работы"
        
    async def setup(self):
        """Настройка бота и регистрация обработчиков"""
        logger.info("Настройка бота")
        
        # Регистрация обработчиков
        register_handlers(self.dp)
        
        # Настройка команд бота
        await setup_commands(self.bot)
        
        logger.info("Настройка бота завершена")

    async def start(self):
        """Запуск бота"""
        logger.info("▶️ Начало процесса запуска бота")
        
        # Информация о системе
        import platform
        system_info = f"ОС: {platform.system()} {platform.version()}"
        python_info = f"Python: {platform.python_version()}"
        logger.info(f"📊 Системная информация: {system_info}, {python_info}")
        
        # Настройка обработчика сигналов для корректного завершения работы
        self._setup_signal_handlers()
        
        logger.info("⚙️ Настройка обработчиков и команд")
        await self.setup()
        
        # Уведомление администраторов о запуске
        logger.info("📧 Отправка уведомлений администраторам о запуске")
        await self.admin_notifier.notify_startup()
        
        # Запуск планировщика и системы уведомлений
        logger.info("🔄 Запуск системы уведомлений и планировщика")
        self.scheduler_task = asyncio.create_task(start_scheduler(self.bot))
        logger.info("✅ Планировщик обновления расписания запущен успешно")
        
        # Запуск поллинга
        logger.info("🚀 Бот запущен и готов к работе")
        await self.dp.start_polling(self.bot)
        
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для корректного завершения работы"""
        try:
            # Для систем, поддерживающих сигналы (Linux, macOS)
            if hasattr(signal, 'SIGINT'):
                asyncio.get_event_loop().add_signal_handler(
                    signal.SIGINT, 
                    lambda: asyncio.create_task(self._handle_stop_signal("Получен сигнал прерывания (SIGINT/Ctrl+C)"))
                )
            if hasattr(signal, 'SIGTERM'):
                asyncio.get_event_loop().add_signal_handler(
                    signal.SIGTERM, 
                    lambda: asyncio.create_task(self._handle_stop_signal("Получен сигнал завершения (SIGTERM)"))
                )
        
            logger.info("✅ Обработчики сигналов настроены")
        except (NotImplementedError, RuntimeError) as e:
            # Для Windows или если нет доступа к добавлению обработчиков сигналов
            logger.warning(f"⚠️ Не удалось настроить обработчики сигналов: {e}")
    
    async def _handle_stop_signal(self, reason: str):
        """Обработка сигнала остановки"""
        if not self.is_stopping:
            self.is_stopping = True
            self.stop_reason = reason
            logger.info(f"⚠️ {reason}")
            
            # Остановка бота через исключение
            if self.dp and hasattr(self.dp, "stop_polling"):
                await self.dp.stop_polling()
            else:
                # Если нет метода stop_polling, вызываем остановку напрямую
                await self.stop()

    async def stop(self):
        """Остановка бота"""
        if self.is_stopping:
            logger.info(f"⏹️ Остановка бота уже выполняется: {self.stop_reason}")
            return
            
        self.is_stopping = True
        logger.info(f"⏹️ Начало процесса остановки бота: {self.stop_reason}")
        
        # Уведомление администратора о завершении работы
        try:
            logger.info("📧 Отправка уведомлений администраторам о завершении работы")
            await self.admin_notifier.notify_shutdown(self.stop_reason)
            logger.info("✅ Уведомления о завершении работы отправлены")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке уведомления о завершении работы: {e}")
        
        # Останавливаем планировщик и систему уведомлений
        if self.scheduler_task:
            try:
                logger.info("🔄 Остановка планировщика и системы уведомлений")
                self.scheduler_task.cancel()
                logger.info("✅ Планировщик и система уведомлений успешно остановлены")
            except Exception as e:
                logger.error(f"❌ Ошибка при остановке планировщика: {e}")
        
        # Закрытие соединения с базой данных
        try:
            logger.info("🔄 Закрытие соединения с базой данных")
            sqlite_db.close()
            logger.info("✅ Соединение с базой данных успешно закрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии соединения с БД: {e}")
        
        # Закрытие сессии бота
        try:
            logger.info("🔄 Закрытие сессии бота")
            await self.bot.session.close()
            logger.info("✅ Сессия бота успешно закрыта")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии сессии бота: {e}")
            
        logger.info(f"👋 Бот успешно остановлен. Причина: {self.stop_reason}")

async def main():
    """Основная функция для запуска бота"""
    logger.info("🔄 Инициализация бота")
    bot_app = BotApp()
    
    try:
        logger.info("▶️ Запуск основного процесса бота")
        await bot_app.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("⚠️ Получен сигнал завершения работы (KeyboardInterrupt/SystemExit)")
        # Задаем причину завершения
        bot_app.stop_reason = "Получен сигнал завершения от пользователя (Ctrl+C)"
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        # Задаем причину завершения
        bot_app.stop_reason = f"Критическая ошибка: {str(e)}"
        try:
            await bot_app.admin_notifier.notify_critical_error(e, "main")
        except Exception as notif_error:
            logger.error(f"❌ Не удалось отправить уведомление о критической ошибке: {notif_error}")
    finally:
        logger.info(f"🔄 Выполнение процедуры остановки бота. Причина: {bot_app.stop_reason}")
        await bot_app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")
    finally:
        # Дополнительная попытка освобождения соединения с БД при аварийном завершении
        try:
            sqlite_db.close()
        except:
            pass
        logger.info("Процесс завершен")