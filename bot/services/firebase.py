from bot.config import logger
from datetime import datetime

# Заглушка для Firebase SERVER_TIMESTAMP
SERVER_TIMESTAMP = datetime.now()

# Заглушка для Firebase
class DummyFirebase:
    def __init__(self):
        logger.info("Используется заглушка Firebase (SQLite)")
    
    def collection(self, *args, **kwargs):
        return self
    
    def document(self, *args, **kwargs):
        return self
    
    def get(self, *args, **kwargs):
        return self
    
    def set(self, *args, **kwargs):
        return None
    
    def update(self, *args, **kwargs):
        return None
    
    def delete(self, *args, **kwargs):
        return None
    
    def where(self, *args, **kwargs):
        return self
    
    def stream(self, *args, **kwargs):
        return []
    
    def batch(self, *args, **kwargs):
        return self
    
    def commit(self, *args, **kwargs):
        return None
    
    # Добавляем свойство exists для имитации документа
    @property
    def exists(self):
        return False
    
    # Добавляем метод to_dict для имитации документа
    def to_dict(self):
        return {}

# Создаем заглушку вместо реального подключения к Firebase
db = DummyFirebase()
logger.info("Firebase заменен на SQLite")