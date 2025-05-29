"""
Модуль для первоапрельских шуток в боте.
Включает дополнительные функции, которые будут активны только 1 апреля.
"""

import random
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from bot.config import logger

# Включить или выключить первоапрельские шутки
ENABLED = True

def is_april_fools_day() -> bool:
    """Проверяет, является ли сегодня 1 апреля"""
    today = datetime.now()
    return today.month == 4 and today.day == 1 and ENABLED


def get_survival_stats(schedule_type: str = None) -> str:
    """Возвращает шуточную статистику выживаемости на основе расписания"""
    if not is_april_fools_day():
        return ""
    
    # Базовая вероятность
    base_probability = random.randint(50, 95)
    
    # Модификаторы в зависимости от типа расписания
    modifiers = {
        "exam": -20,            # Экзамены снижают шансы выживания
        "consultation": +10,    # Консультации повышают шансы
        "practice": -5,         # Практика немного снижает шансы
        "lecture": +5,          # Лекции немного повышают шансы
        "weekend": +30,         # Выходные значительно повышают шансы
    }
    
    # Применяем модификатор если применимо
    if schedule_type in modifiers:
        base_probability += modifiers[schedule_type]
    
    # Случайный разброс +/- 5%
    random_factor = random.randint(-5, 5)
    final_probability = max(1, min(99, base_probability + random_factor))
    
    # Случайные дополнительные сообщения
    additional_messages = [
        "Держитесь крепче!",
        "Не забудьте взять запасной мозг!",
        "Рекомендуется иметь при себе энергетик.",
        "Кофеин в крови повысит шансы на 10%.",
        "Шанс уснуть на паре: весьма высокий.",
        "Рекомендуется периодически моргать.",
        "Уровень стресса: космический!",
        "Запас печенек повысит выживаемость на 5%.",
        "Не думайте о котиках во время пары!"
    ]
    
    # Случайный совет
    advice = random.choice(additional_messages)
    
    # Составляем сообщение
    message = f"\n\n📊 <b>Статистика выживаемости</b>\n"
    message += f"Вероятность выживания после этого дня: <b>{final_probability}%</b>\n"
    message += f"💡 <i>{advice}</i>"
    
    return message


def get_mercy_button() -> InlineKeyboardMarkup:
    """Возвращает кнопку 'Просить пощады' для первоапрельской шутки"""
    if not is_april_fools_day():
        return None
    
    # Создаем кнопку
    mercy_button = InlineKeyboardButton(text="🙏 Просить пощады", callback_data="april_fools_mercy")
    
    # Создаем клавиатуру с правильной структурой для aiogram 3.x
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[mercy_button]])
    
    return keyboard


async def handle_mercy_request(message: Message) -> str:
    """Обрабатывает нажатие на кнопку 'Просить пощады'"""
    if not is_april_fools_day():
        return "Эта функция доступна только 1 апреля!"
    
    # Случайные отказы в пощаде
    mercy_denied_messages = [
        "Запрос отклонен. Расписание неумолимо.",
        "Расписание рассмотрело вашу просьбу и... отказало!",
        "Хм... Нет. Просто нет.",
        "ERROR 404: Пощада не найдена.",
        "Расписание смеется над вашей слабостью!",
        "Пожалуйста, подождите... Ответ: нет.",
        "Сегодня не день пощады!",
        "Кнопка пощады оказалась декоративной.",
        "Повторите запрос через... никогда!",
        "Вычисляю вероятность пощады... 0%."
    ]
    
    return random.choice(mercy_denied_messages) 