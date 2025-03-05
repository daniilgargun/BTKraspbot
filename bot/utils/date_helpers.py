import locale
from datetime import datetime
from typing import Optional

# Установка локали
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'ru_RU')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

def format_russian_date(date: datetime) -> str:
    """Форматирование даты на русском языке"""
    return date.strftime('%d %B %Y')

def get_russian_weekday(date: datetime) -> str:
    """Получение дня недели на русском"""
    return date.strftime('%A')

def parse_russian_date(date_str: str) -> Optional[datetime]:
    """Парсинг даты из русского формата"""
    try:
        return datetime.strptime(date_str, '%d %B %Y')
    except ValueError:
        return None 