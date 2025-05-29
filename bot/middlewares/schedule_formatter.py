import locale
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from bot.config import format_date, WEEKDAYS, MONTHS, logger

logger = logging.getLogger(__name__)

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU')
    except locale.Error:
        logger.warning("Не удалось установить русскую локаль")

def _translate_day(day: str) -> str:
    """Перевод дня недели с русского на английский и обратно"""
    ru_to_en = {
        'понедельник': 'monday',
        'вторник': 'tuesday', 
        'среда': 'wednesday',
        'четверг': 'thursday',
        'пятница': 'friday',
        'суббота': 'saturday',
        'воскресенье': 'sunday'
    }
    
    en_to_ru = {
        'monday': 'понедельник',
        'tuesday': 'вторник',
        'wednesday': 'среда', 
        'thursday': 'четверг',
        'friday': 'пятница',
        'saturday': 'суббота',
        'sunday': 'воскресенье'
    }

    day = day.lower()
    if day in ru_to_en:
        return ru_to_en[day]
    elif day in en_to_ru:
        return en_to_ru[day]
    return day

def format_date(date_str: str) -> str:
    """Форматирование даты в формат '23-дек (понедельник)'"""
    try:
        # Парсим дату формата "23-дек" или "01-март"
        if '-' in date_str:
            day, month = date_str.split('-')
            
            # Преобразуем русские названия месяцев в сокращенные
            month_mapping = {
                'март': 'мар',
                'май': 'мая',
                'июнь': 'июн',
                'июль': 'июл',
                'август': 'авг',
                'сентябрь': 'сен',
                'октябрь': 'окт',
                'ноябрь': 'нояб',
                'декабрь': 'дек',
                'январь': 'янв',
                'февраль': 'фев',
                'апрель': 'апр'
            }
            
            # Если месяц полный - преобразуем в сокращенный
            month = month_mapping.get(month.lower(), month.lower())
            
            # Создаем объект datetime
            current_year = datetime.now().year
            try:
                date_obj = datetime.strptime(f"{day}-{month}-{current_year}", "%d-%b-%Y")
            except ValueError:
                # Если не получилось, пробуем другой формат
                month_num = MONTHS.get(month, None)
                if month_num:
                    date_obj = datetime(current_year, month_num, int(day))
                else:
                    return date_str
            
            # Получаем день недели
            weekday_ru = {
                'Monday': 'понедельник',
                'Tuesday': 'вторник',
                'Wednesday': 'среда',
                'Thursday': 'четверг',
                'Friday': 'пятница',
                'Saturday': 'суббота',
                'Sunday': 'воскресенье'
            }
            weekday = weekday_ru[date_obj.strftime('%A')]
            
            # Форматируем дату в нужный формат
            return f"{day}-{month} ({weekday})"
        return date_str
    except Exception as e:
        logger.error(f"Ошибка форматирования даты {date_str}: {e}")
        return date_str

class ScheduleFormatter:
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Преобразование строки даты в объект datetime"""
        try:
            if '-' in date_str:
                day, month = date_str.split('-')
                month_num = MONTHS.get(month.lower())
                if month_num:
                    return datetime(datetime.now().year, month_num, int(day))
            return datetime.now()  # Возвращаем текущую дату если парсинг не удался
        except Exception as e:
            logger.error(f"Ошибка парсинга даты {date_str}: {e}")
            return datetime.now()

    @staticmethod
    def format_schedule(schedule_data: str | List[Dict] | None, day: str, user_data: dict) -> str:
        """Форматирование расписания на день"""
        # Если получили None - расписание не загружено
        if schedule_data is None:
            return f"❌ Расписание на {day.lower()} не загружено"

        # Если получили строку (сообщение об ошибке), возвращаем её
        if isinstance(schedule_data, str):
            return schedule_data

        # Если расписание пустое для выбранной группы/преподавателя, но есть для других
        if not schedule_data and isinstance(schedule_data, list):
            if user_data.get('role') == 'Студент':
                return f"📅 {day.capitalize()}\n═════════════════════\n\nУ группы {user_data.get('selected_group')} в этот день нет занятий"
            else:
                return f"📅 {day.capitalize()}\n═════════════════════\n\nУ преподавателя {user_data.get('selected_teacher')} в этот день нет занятий"

        # Формируем заголовок
        header = "📚 Расписание "
        if user_data.get('role') == 'Студент':
            header += f"группы {user_data.get('selected_group')}\n\n"
        else:
            header += f"преподавателя {user_data.get('selected_teacher')}\n\n"

        # Форматируем дату
        try:
            if '-' in day:
                # Для даты вида "13-янв"
                day_num, month = day.split('-')
                month_num = MONTHS.get(month.lower())
                if month_num:
                    date_obj = datetime(datetime.now().year, month_num, int(day_num))
                    weekday = WEEKDAYS.get(date_obj.strftime('%A').lower())
                    formatted_date = f"📅 {day_num} {month} ({weekday})"
                else:
                    formatted_date = f"📅 {day}"
            else:
                # Для дня недели (например, "Понедельник")
                # Находим ближайшую дату для этого дня недели
                current_date = datetime.now()
                day_lower = day.lower()
                
                # Получаем номер дня недели (0 = понедельник, 6 = воскресенье)
                target_weekday = list(WEEKDAYS.values()).index(day_lower)
                current_weekday = current_date.weekday()
                
                # Вычисляем разницу дней
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # Если день уже прошел, берем следующую неделю
                    days_ahead += 7
                    
                target_date = current_date + timedelta(days=days_ahead)
                
                # Форматируем дату
                day_num = target_date.day
                month = list(MONTHS.keys())[target_date.month - 1]  # Получаем сокращение месяца
                formatted_date = f"📅 {day_num} {month} ({day_lower})"

        except Exception as e:
            logger.error(f"Ошибка форматирования даты: {e}")
            formatted_date = f"📅 {day}"

        response = [
            header,
            "",  # Добавляем пустую строку после заголовка
            formatted_date,
            "═════════════════════\n"
        ]

        # Группируем пары
        grouped_lessons = []
        current_group = None
        
        for lesson in sorted(schedule_data, key=lambda x: int(x['lesson_number'])):
            if current_group and ScheduleFormatter._can_group_lessons(current_group[-1], lesson):
                current_group.append(lesson)
            else:
                if current_group:
                    grouped_lessons.append(current_group)
                current_group = [lesson]
        
        if current_group:
            grouped_lessons.append(current_group)

        # Форматируем каждую группу пар
        for group in grouped_lessons:
            if len(group) > 1:
                numbers = f"{group[0]['lesson_number']}-{group[-1]['lesson_number']}"
            else:
                numbers = group[0]['lesson_number']

            lesson_block = [
                f"🕐 {numbers} пара",
                f"📚 {group[0]['discipline']}"
            ]

            if user_data.get('role') == 'Студент':
                lesson_block.append(f"👨‍🏫 {group[0]['teacher_name']}")
            else:
                # Для преподавателей показываем группу
                groups = set()
                for lesson in group:
                    if lesson.get('group_name'):
                        groups.add(lesson['group_name'])
                if groups:
                    lesson_block.append(f"👥 Группа: {', '.join(sorted(groups))}")

            lesson_block.append(f"🏢 Кабинет: {group[0]['classroom']}")

            if group[0].get('subgroup') and group[0]['subgroup'] != '0':
                lesson_block.append(f"👥 Подгруппа {group[0]['subgroup']}")

            response.extend(lesson_block)
            response.append("")  # Пустая строка между парами

        return "\n".join(response)

    @staticmethod
    def _can_group_lessons(lesson1: dict, lesson2: dict) -> bool:
        """Проверка возможности группировки пар"""
        return (
            lesson1['discipline'] == lesson2['discipline'] and
            lesson1['teacher_name'] == lesson2['teacher_name'] and
            lesson1['classroom'] == lesson2['classroom'] and
            lesson1.get('subgroup', '0') == lesson2.get('subgroup', '0') and
            int(lesson2['lesson_number']) == int(lesson1['lesson_number']) + 1
        )

    @staticmethod
    def format_full_schedule(schedule_data: dict | None, user_data: dict) -> str:
        """Форматирование полного расписания на неделю"""
        # Если расписание не загружено
        if schedule_data is None:
            return "❌ Расписание не загружено"

        # Если расписание пустое для всех
        if not schedule_data:
            return "📅 Расписание\n═════════════════════\n\nНа этой неделе нет расписания"

        # Формируем заголовок
        header = "📚 Расписание "
        if user_data.get('role') == 'Студент':
            header += f"группы {user_data.get('selected_group')}\n\n"
        else:
            header += f"преподавателя {user_data.get('selected_teacher')}\n\n"

        response = [header]

        # Сортируем даты
        sorted_dates = sorted(schedule_data.items(), key=lambda x: ScheduleFormatter._parse_date(x[0]))

        # Перебираем все даты в расписании
        for date, lessons in sorted_dates:
            if not lessons:  # Пропускаем пустые дни
                continue

            # Добавляем дату
            response.extend([
                "",  # Пустая строка перед новой датой
                f"📅 {date}",
                "═════════════════════\n"
            ])

            # Группируем пары
            grouped_lessons = []
            current_group = None
            
            for lesson in sorted(lessons, key=lambda x: int(x['lesson_number'])):
                if current_group and ScheduleFormatter._can_group_lessons(current_group[-1], lesson):
                    current_group.append(lesson)
                else:
                    if current_group:
                        grouped_lessons.append(current_group)
                    current_group = [lesson]
            
            if current_group:
                grouped_lessons.append(current_group)

            # Форматируем каждую группу пар
            for group in grouped_lessons:
                if len(group) > 1:
                    numbers = f"{group[0]['lesson_number']}-{group[-1]['lesson_number']}"
                else:
                    numbers = group[0]['lesson_number']

                lesson_block = [
                    f"🕐 {numbers} пара",
                    f"📚 {group[0]['discipline']}"
                ]

                if user_data.get('role') == 'Студент':
                    lesson_block.append(f"👨‍🏫 {group[0]['teacher_name']}")
                else:
                    # Для преподавателей показываем группу
                    groups = set()
                    for lesson in group:
                        if lesson.get('group_name'):
                            groups.add(lesson['group_name'])
                    if groups:
                        lesson_block.append(f"👥 Группа: {', '.join(sorted(groups))}")

                lesson_block.append(f"🏢 Кабинет: {group[0]['classroom']}")

                if group[0].get('subgroup') and group[0]['subgroup'] != '0':
                    lesson_block.append(f"👥 Подгруппа {group[0]['subgroup']}")

                response.extend(lesson_block)
                response.append("")  # Пустая строка между парами

        return "\n".join(response) 