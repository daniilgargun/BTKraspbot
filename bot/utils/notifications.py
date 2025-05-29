from aiogram import Bot
from bot.config import config, logger
import logging
import os
from datetime import datetime
from typing import Optional, List

class AdminNotifier:
    """Класс для отправки уведомлений администраторам"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        # Для обратной совместимости
        self.admin_id = config.ADMIN_ID
        # Список всех администраторов
        self.admin_ids = config.ADMIN_IDS
        self.log_file = "bot_notifications.log"
        
        # Настройка логирования в файл
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
    async def send_admin_message(self, message: str, level: str = "INFO"):
        """Отправка уведомления основному администратору"""
        return await self.send_to_admin(self.admin_id, message, level)
    
    async def send_to_admin(self, admin_id: int, message: str, level: str = "INFO") -> bool:
        """Отправка уведомления конкретному администратору"""
        try:
            prefix = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🔥"
            }.get(level, "ℹ️")
            
            await self.bot.send_message(
                admin_id, 
                f"{prefix} {message}"
            )
            
            logger.log(
                getattr(logging, level, logging.INFO),
                f"Уведомление отправлено администратору (ID: {admin_id}): {message}"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
            return False
            
    async def send_to_all_admins(self, message: str, level: str = "INFO") -> List[int]:
        """Отправка уведомления всем администраторам с возвратом списка ID, кому успешно отправлено"""
        success_list = []
        
        for admin_id in self.admin_ids:
            try:
                if await self.send_to_admin(admin_id, message, level):
                    success_list.append(admin_id)
            except Exception as e:
                logger.error(f"Ошибка при массовой отправке уведомления администратору {admin_id}: {e}")
                
        return success_list
            
    def log_to_file(self, message: str, level: str = "INFO"):
        """Запись уведомления в лог-файл"""
        try:
            log_level = {
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }.get(level, logging.INFO)
            
            logger.log(log_level, message)
        except Exception as e:
            logger.error(f"Ошибка при записи в лог-файл: {e}")
            
    async def notify_startup(self):
        """Уведомление о запуске бота"""
        startup_message = (
            "🚀 <b>Бот успешно запущен</b>\n\n"
            f"⏰ Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"🔄 Ожидается автоматическое обновление расписания каждые 5 минут\n"
            f"📱 Отправка уведомлений о новых датах включена"
        )
        await self.send_to_all_admins(startup_message)
        
    async def notify_shutdown(self, reason="Штатное завершение работы"):
        """Уведомление о завершении работы бота"""
        shutdown_message = (
            "🛑 <b>Бот завершает работу</b>\n\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"📝 Причина: {reason}\n"
            f"⚠️ Уведомления и автоматическое обновление расписания недоступны до перезапуска"
        )
        await self.send_to_all_admins(shutdown_message, "WARNING")
            
    async def notify_critical_error(self, error, context: str = ""):
        """Уведомление о критической ошибке"""
        error_message = f"🔥 Критическая ошибка"
        if context:
            error_message += f" в {context}"
        error_message += f": {str(error)}"
            
        await self.send_admin_message(error_message, "CRITICAL")
        
    async def notify_system_warning(self, resource: str, value: float, threshold: float) -> None:
        """Уведомление о системных предупреждениях"""
        warning_message = (
            f"⚠️ *Системное предупреждение*\n"
            f"*Ресурс*: {resource}\n"
            f"*Текущее значение*: {value}%\n"
            f"*Порог*: {threshold}%\n"
        )
        await self.send_admin_message(warning_message, "WARNING")
        
    async def notify_bot_restart(self, reason: str) -> None:
        """Уведомление о перезапуске бота"""
        restart_message = (
            f"🔄 *Перезапуск бота*\n"
            f"*Причина*: {reason}\n"
        )
        await self.send_admin_message(restart_message, "INFO")
            
    async def get_last_logs(self, lines: int = 50) -> str:
        """Получение последних строк лога"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
                return ''.join(logs[-lines:])
        except Exception as e:
            return f"Ошибка при чтении логов: {e}" 