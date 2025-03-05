import logging
from datetime import datetime

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Создаем форматтер для логов
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [SECURITY] %(message)s'
        )
        
        # Файловый handler для логов безопасности
        file_handler = logging.FileHandler('security.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
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
        
    def log_admin_action(self, admin_id: int, action: str, details: str = None):
        """Логирование действий администратора"""
        message = f"Admin action: admin_id={admin_id}, action={action}"
        if details:
            message += f", details={details}"
        self.logger.info(message)

# Создаем глобальный экземпляр логгера безопасности
security_logger = SecurityLogger() 