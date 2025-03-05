from time import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.services.monitoring import monitor

class PerformanceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        start_time = time()
        
        try:
            result = await handler(event, data)
            
            # Измеряем время выполнения
            execution_time = time() - start_time
            
            # Добавляем информацию о запросе
            route = f"{event.text if event.text else 'non-text message'}"
            monitor.add_request_time(route, execution_time)
            
            return result
            
        except Exception as e:
            # Регистрируем ошибку
            monitor.add_error(type(e).__name__, str(e))
            raise 