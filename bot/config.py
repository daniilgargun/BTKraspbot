import locale
from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv
import logging
from datetime import datetime

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
    'май': 5, 'июн': 6, 'июл': 7, 'авг': 8,
    'сен': 9, 'окт': 10, 'нояб': 11, 'дек': 12
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
                # Пробуем формат '26-нояб'
                if '-' in date:
                    day, month = date.split('-')
                    if month.lower() in MONTHS:
                        month_num = MONTHS[month.lower()]
                        date = datetime(datetime.now().year, month_num, int(day))
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
    BOT_TOKEN: str = getenv("BOT_TOKEN")
    ADMIN_ID: int = int(getenv("ADMIN_ID", 1437368782))

    def __post_init__(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is not set!")

logger.info("Начало инициализации базы данных")
# Создание экземпляра конфигурации
config = Config()
logger.info("База данных успешно инициализирована")