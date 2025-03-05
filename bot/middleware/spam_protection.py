from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from cachetools import TTLCache
from datetime import datetime, timedelta
from bot.config import logger, config
import logging

class SpamProtection(BaseMiddleware):
    def __init__(self):
        self.cache = TTLCache(maxsize=10000, ttl=60.0)
        self.message_limit = 20
        self.warning_count = 5
        # Словарь для хранения информации о банах: {user_id: (timestamp_end, reason)}
        self.banned_users = {}
        # Сообщения в обработке для связи с админом
        self.admin_messages = set()
        
    def ban_user(self, user_id: int, duration_minutes: int = 30, reason: str = "спам"):
        """Временный бан пользователя"""
        ban_end = datetime.now() + timedelta(minutes=duration_minutes)
        self.banned_users[user_id] = (ban_end, reason)
        logger.warning(f"User {user_id} banned for {duration_minutes} minutes. Reason: {reason}")

    def unban_user(self, user_id: int) -> bool:
        """Разбан пользователя"""
        if user_id in self.banned_users:
            del self.banned_users[user_id]
            logger.info(f"User {user_id} has been unbanned")
            return True
        return False

    def is_banned(self, user_id: int) -> tuple[bool, str, datetime]:
        """Проверка бана с возвратом статуса, причины и времени окончания"""
        if user_id in self.banned_users:
            ban_end, reason = self.banned_users[user_id]
            if datetime.now() >= ban_end:
                self.unban_user(user_id)
                return False, "", None
            return True, reason, ban_end
        return False, "", None

    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        
        # Пропускаем админов
        if user_id == config.ADMIN_ID:
            return await handler(event, data)

        # Проверяем бан
        is_banned, reason, ban_end = self.is_banned(user_id)
        if is_banned:
            time_left = ban_end - datetime.now()
            minutes_left = int(time_left.total_seconds() / 60)
            
            # Проверяем, является ли сообщение обращением к админу
            if event.text and event.text.startswith("/admin"):
                if user_id not in self.admin_messages:
                    self.admin_messages.add(user_id)
                    # Получаем информацию о пользователе из базы данных
                    user_data = await db.get_user(user_id)
                    username = user_data.get('username', 'Нет username') if user_data else 'Нет данных'
                    
                    admin_message = (
                        f"🚫 Сообщение от забаненного пользователя:\n"
                        f"👤 ID: `{user_id}`\n"
                        f"Username: @{username}\n"
                        f"Причина бана: {reason}\n"
                        f"Осталось: {minutes_left} мин.\n\n"
                        f"📝 Сообщение:\n{event.text[6:].strip()}"  # Убираем /admin из сообщения
                    )
                    
                    # Добавляем кнопку разбана
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="🔓 Разбанить пользователя",
                            callback_data=f"unban_{user_id}"
                        )
                    ]])
                    
                    await event.bot.send_message(
                        config.ADMIN_ID,
                        admin_message,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    
                    await event.answer(
                        "✉️ Ваше сообщение отправлено администратору.\n"
                        "⏳ Пожалуйста, ожидайте ответа."
                    )
                else:
                    await event.answer(
                        "⚠️ Вы уже отправили сообщение администратору.\n"
                        "Пожалуйста, дождитесь ответа."
                    )
                return
            
            await event.answer(
                f"🚫 Вы заблокированы на {minutes_left} минут.\n"
                f"Причина: {reason}\n"
                "Для связи с администратором используйте команду /admin <ваше сообщение>"
            )
            return

        # Получаем счетчик сообщений
        user_data = self.cache.get(user_id, {"count": 0, "warnings": 0})
        user_data["count"] += 1
        
        if user_data["count"] > self.message_limit:
            user_data["warnings"] += 1
            if user_data["warnings"] >= self.warning_count:
                # Временный бан на 30 минут
                self.ban_user(user_id, duration_minutes=30)
                await event.answer(
                    "🚫 Вы заблокированы на 30 минут за спам\n"
                    "Для связи с администратором используйте команду /admin <ваше сообщение>"
                )
                return
            
            logger.warning(f"Spam warning for user {user_id}")
            await event.answer(
                f"⚠️ Предупреждение: слишком много сообщений ({user_data['warnings']}/{self.warning_count})"
            )
            return
            
        self.cache[user_id] = user_data
        return await handler(event, data)

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Файловый handler для безопасности
        security_handler = logging.FileHandler('security.log')
        security_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(security_handler)
        
    def log_access(self, user_id: int, action: str, status: bool):
        """Логирование попыток доступа"""
        self.logger.info(
            f"Access attempt: user={user_id}, action={action}, "
            f"status={'success' if status else 'denied'}"
        )
        
    def log_suspicious(self, user_id: int, reason: str):
        """Логирование подозрительной активности"""
        self.logger.warning(
            f"Suspicious activity: user={user_id}, reason={reason}"
        )
        
    def log_security_event(self, event_type: str, details: dict):
        """Логирование событий безопасности"""
        self.logger.info(
            f"Security event: type={event_type}, details={details}"
        )

security_logger = SecurityLogger()