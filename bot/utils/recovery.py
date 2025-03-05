import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from functools import partial
from typing import Optional, Callable
import json
import aiofiles
import psutil
from .notifications import AdminNotifier

logger = logging.getLogger(__name__)

class BotRecoveryManager:
    def __init__(self, restart_callback: Callable, notifier: AdminNotifier):
        self.restart_callback = restart_callback
        self.notifier = notifier
        self.state_file = "bot_state.json"
        self.max_restart_attempts = 3
        self.restart_cooldown = 60  # секунд между попытками перезапуска
        self.last_restart_time = None
        self.restart_count = 0
        self.is_shutting_down = False

        # Пороги для системных предупреждений
        self.cpu_threshold = 90
        self.memory_threshold = 90
        self.disk_threshold = 90

    async def save_state(self, state: dict):
        """Сохранение состояния бота"""
        try:
            async with aiofiles.open(self.state_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(state, ensure_ascii=False, indent=2))
            logger.info("✅ Состояние бота сохранено")
            self.notifier.log_to_file("Состояние бота сохранено", "INFO")
        except Exception as e:
            error_msg = f"❌ Ошибка при сохранении состояния: {e}"
            logger.error(error_msg)
            self.notifier.log_to_file(error_msg, "ERROR")

    async def load_state(self) -> Optional[dict]:
        """Загрузка состояния бота"""
        try:
            if os.path.exists(self.state_file):
                async with aiofiles.open(self.state_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке состояния: {e}")
            return None

    async def handle_shutdown(self, signal_name: str):
        """Обработка сигналов завершения"""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        shutdown_msg = f"⚠️ Получен сигнал {signal_name}, начинаем корректное завершение..."
        logger.info(shutdown_msg)
        self.notifier.log_to_file(shutdown_msg, "INFO")
        
        # Уведомляем администратора
        await self.notifier.send_admin_message(f"Бот завершает работу: {signal_name}", "INFO")
        
        # Сохраняем текущее состояние
        state = {
            "shutdown_time": datetime.now().isoformat(),
            "shutdown_reason": signal_name,
            "was_clean_shutdown": True
        }
        await self.save_state(state)
        
        # Даем время на завершение текущих операций
        await asyncio.sleep(2)
        sys.exit(0)

    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGBREAK):
            signal.signal(sig, lambda s, f: asyncio.create_task(
                self.handle_shutdown(signal.Signals(s).name)
            ))

    async def check_system_resources(self) -> bool:
        """Проверка системных ресурсов"""
        try:
            # Проверка CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.cpu_threshold:
                await self.notifier.notify_system_warning("CPU", cpu_percent, self.cpu_threshold)

            # Проверка памяти
            memory = psutil.virtual_memory()
            if memory.percent > self.memory_threshold:
                await self.notifier.notify_system_warning("Память", memory.percent, self.memory_threshold)

            # Проверка диска
            disk = psutil.disk_usage('/')
            if disk.percent > self.disk_threshold:
                await self.notifier.notify_system_warning("Диск", disk.percent, self.disk_threshold)

            return True
        except Exception as e:
            error_msg = f"❌ Ошибка при проверке системных ресурсов: {e}"
            logger.error(error_msg)
            self.notifier.log_to_file(error_msg, "ERROR")
            await self.notifier.notify_critical_error(e, "Проверка системных ресурсов")
            return False

    async def monitor_bot_health(self):
        """Мониторинг здоровья бота"""
        while not self.is_shutting_down:
            await self.check_system_resources()
            await asyncio.sleep(300)  # Проверка каждые 5 минут

    async def attempt_restart(self):
        """Попытка перезапуска бота"""
        if self.restart_count >= self.max_restart_attempts:
            error_msg = "❌ Достигнуто максимальное количество попыток перезапуска"
            logger.error(error_msg)
            self.notifier.log_to_file(error_msg, "ERROR")
            await self.notifier.send_admin_message(error_msg, "ERROR")
            return False

        current_time = datetime.now()
        if (self.last_restart_time and 
            (current_time - self.last_restart_time).seconds < self.restart_cooldown):
            await asyncio.sleep(self.restart_cooldown)

        self.restart_count += 1
        self.last_restart_time = current_time

        try:
            await self.notifier.notify_bot_restart(f"Попытка {self.restart_count} из {self.max_restart_attempts}")
            await self.restart_callback()
            self.restart_count = 0  # Сбрасываем счетчик при успешном перезапуске
            return True
        except Exception as e:
            error_msg = f"❌ Ошибка при перезапуске: {e}"
            logger.error(error_msg)
            self.notifier.log_to_file(error_msg, "ERROR")
            await self.notifier.notify_critical_error(e, "Перезапуск бота")
            return False

    async def handle_error(self, error: Exception):
        """Обработка ошибок во время работы бота"""
        error_msg = f"❌ Произошла ошибка: {str(error)}"
        logger.error(error_msg)
        self.notifier.log_to_file(error_msg, "ERROR")
        
        # Уведомляем администратора
        await self.notifier.notify_critical_error(error)
        
        # Сохраняем информацию об ошибке
        state = {
            "error_time": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "was_clean_shutdown": False
        }
        await self.save_state(state)
        
        # Пытаемся перезапустить бота
        if not self.is_shutting_down:
            await self.attempt_restart()

def create_recovery_manager(restart_callback: Callable, notifier: AdminNotifier) -> BotRecoveryManager:
    """Создание менеджера восстановления"""
    manager = BotRecoveryManager(restart_callback, notifier)
    manager.setup_signal_handlers()
    return manager 