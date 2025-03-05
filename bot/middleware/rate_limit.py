from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache
from datetime import datetime
from bot.config import logger

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=5):  # 5 сообщений в секунду
        self.cache = TTLCache(maxsize=10000, ttl=60.0)  # Хранить 60 секунд
        self.rate_limit = rate_limit
        
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        
        # Получаем текущее время
        now = datetime.now()
        
        # Получаем историю запросов пользователя
        user_requests = self.cache.get(user_id, [])
        
        # Очищаем старые запросы (старше 1 секунды)
        user_requests = [req for req in user_requests if (now - req).total_seconds() <= 1]
        
        if len(user_requests) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            await event.answer("⚠️ Слишком много запросов. Пожалуйста, подождите.")
            return
        
        # Добавляем текущий запрос
        user_requests.append(now)
        self.cache[user_id] = user_requests
        
        return await handler(event, data) 