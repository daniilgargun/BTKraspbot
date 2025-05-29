import locale
from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv
import logging
from datetime import datetime
from pathlib import Path

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Словарь для дней недели
WEEKDAYS = {
    'monday': 'понедельник',
    'tuesday': 'вторник',
    'wednesday': 'среда',
    'thursday': 'четверг',
    'friday': 'пятница',
    'saturday': 'суббота',
    'sunday': 'воскресенье'
}

# Словарь для месяцев
MONTHS = {
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
    'май': 5, 'мая': 5, 'июн': 6, 'июнь': 6, 'июня': 6,
    'июл': 7, 'июль': 7, 'июля': 7, 'авг': 8, 'августа': 8,
    'сен': 9, 'сентябрь': 9, 'сентября': 9, 'окт': 10, 'октября': 10, 'октябрь': 10,
    'нояб': 11, 'ноябрь': 11, 'ноября': 11, 'дек': 12, 'декабрь': 12, 'декабря': 12,
    # Полные названия месяцев (именительный падеж)
    'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4,
    'июнь': 6, 'июль': 7, 'август': 8,
    'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12,
    # Родительный падеж
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}

MONTHS_FULL = {
    1: 'января',
    2: 'февраля',
    3: 'марта',
    4: 'апреля',
    5: 'мая',
    6: 'июня',
    7: 'июля',
    8: 'августа',
    9: 'сентября',
    10: 'октября',
    11: 'ноября',
    12: 'декабря'
}

# Функция форматирования даты
def format_date(date):
    """
    Форматирование даты с учетом русской локали
    
    Args:
        date: datetime объект или строка в формате 'YYYY-MM-DD', 'DD.MM.YYYY' или 'DD-МММ'
    """
    try:
        # Если передана строка, преобразуем её в datetime
        if isinstance(date, str):
            try:
                # Пробуем формат '26-нояб' или '26-ноябрь'
                if '-' in date:
                    day, month = date.split('-')
                    month_lower = month.lower()
                    
                    # Пробуем найти месяц в словаре (полное название или сокращение)
                    month_num = MONTHS.get(month_lower)
                    
                    # Если не нашли, пробуем использовать первые 3 буквы
                    if not month_num and len(month_lower) > 3:
                        month_short = month_lower[:3]
                        month_num = MONTHS.get(month_short)
                        if month_num:
                            logger.info(f"Использую сокращение месяца: {month} -> {month_short}")
                    
                    if month_num:
                        date = datetime(datetime.now().year, month_num, int(day))
                    else:
                        logger.error(f"Месяц '{month}' не найден в словаре MONTHS")
                        return date
                else:
                    try:
                        date = datetime.strptime(date, '%Y-%m-%d')
                    except ValueError:
                        date = datetime.strptime(date, '%d.%m.%Y')
            except ValueError as e:
                logger.error(f"Не удалось распарсить дату: {date}, ошибка: {e}")
                return date

        # Теперь у нас точно datetime объект
        return f"{date.day} {MONTHS_FULL[date.month]} {date.year}"
    except Exception as e:
        logger.error(f"Ошибка форматирования даты: {e}")
        # Если что-то пошло не так, возвращаем дату в исходном виде
        return str(date)

# Попытка установить русскую локаль
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU')
    except locale.Error:
        logger.warning("Не удалось установить русскую локаль")

# Загрузка переменных окружения
load_dotenv()

@dataclass
class Config:
    #BOT_TOKEN: str = ("8191187316:AAFvss-pBtCUy90nNehQJ-4S8My1Vs7oQzo")
    BOT_TOKEN: str = getenv("BOT_TOKEN")
    # Основной ID администратора (для обратной совместимости)
    ADMIN_ID: int = int(getenv("ADMIN_ID", 1437368782))
    
    # Список ID администраторов, включая основного
    _ADMIN_IDS: str = getenv("ADMIN_IDS", "")
    
    # Список всех ID администраторов
    ADMIN_IDS: list = None
    
    def __post_init__(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is not set!")
            
        # Инициализация списка администраторов
        self.ADMIN_IDS = []
        
        # Добавляем основного администратора
        if self.ADMIN_ID:
            self.ADMIN_IDS.append(self.ADMIN_ID)
            
        # Добавляем дополнительных администраторов, если они указаны
        if self._ADMIN_IDS:
            try:
                # Парсим строку формата "123456789,987654321,111222333"
                additional_admins = [int(admin_id.strip()) for admin_id in self._ADMIN_IDS.split(",") if admin_id.strip()]
                # Добавляем уникальные ID, исключая дубликаты
                for admin_id in additional_admins:
                    if admin_id not in self.ADMIN_IDS:
                        self.ADMIN_IDS.append(admin_id)
                logger.info(f"Загружено {len(self.ADMIN_IDS)} админов: {self.ADMIN_IDS}")
            except ValueError as e:
                logger.error(f"Ошибка при парсинге ID администраторов: {e}")
        
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id in self.ADMIN_IDS

logger.info("Начало инициализации базы данных")
# Создание экземпляра конфигурации
config = Config()
logger.info("База данных успешно инициализирована")

def get_firestore_db():
    """Заглушка для Firestore"""
    from bot.services.firebase import DummyFirebase
    logger.info("Используется заглушка Firestore (SQLite)")
    return DummyFirebase()