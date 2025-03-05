from aiogram import Bot
import logging
from datetime import datetime
import os
from typing import Optional
from bot.config import config

logger = logging.getLogger(__name__)

class AdminNotifier:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.admin_id = config.ADMIN_ID  # ID администратора из конфига
        self.log_file = "bot_logs.txt"
        
        # Настройка логирования в файл
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
    async def send_admin_message(self, message: str, level: str = "INFO") -> None:
        """Отправка сообщения администратору"""
        try:
            # Форматируем сообщение
            formatted_message = (
                f"🤖 *Уведомление от бота*\n"
                f"*Уровень*: {level}\n"
                f"*Время*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"*Сообщение*: {message}\n"
            )
            
            # Отправляем сообщение администратору
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=formatted_message,
                parse_mode="Markdown"
            )
            
            # Логируем отправку
            logger.info(f"✅ Уведомление отправлено администратору: {message}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке уведомления администратору: {e}")
            
    async def notify_critical_error(self, error: Exception, context: Optional[str] = None) -> None:
        """Уведомление о критической ошибке"""
        error_message = (
            f"❗️ *Критическая ошибка*\n"
            f"*Тип*: {type(error).__name__}\n"
            f"*Описание*: {str(error)}\n"
        )
        if context:
            error_message += f"*Контекст*: {context}\n"
            
        await self.send_admin_message(error_message, "ERROR")
        
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
        
    async def notify_startup(self) -> None:
        """Уведомление о запуске бота"""
        startup_message = "✅ Бот успешно запущен и готов к работе"
        await self.send_admin_message(startup_message, "INFO")
        
    def log_to_file(self, message: str, level: str = "INFO") -> None:
        """Запись сообщения в лог-файл"""
        log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {level} - {message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    async def get_last_logs(self, lines: int = 50) -> str:
        """Получение последних строк лога"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
                return ''.join(logs[-lines:])
        except Exception as e:
            return f"Ошибка при чтении логов: {e}" 