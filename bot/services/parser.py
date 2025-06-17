import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from bot.services.database import Database
from bot.config import logger, WEEKDAYS, format_date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from threading import Lock
from webdriver_manager.chrome import ChromeDriverManager
import requests.exceptions
from typing import List, Dict, Union
import locale
from bot.utils.date_helpers import format_russian_date, parse_russian_date
import platform

user_lock = Lock()

# Устанавливаем русскую локаль
if platform.system() == 'Windows':
    locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')
else:
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

class ScheduleParser:
    def __init__(self):
        self.url = "https://bartc.by/index.php/obuchayushchemusya/dnevnoe-otdelenie/tekushchee-raspisanie"
        self.db = Database()
        
        # Добавляем словарь для месяцев
        self.MONTH_MAP = {
            'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
            'май': 5, 'мая': 5, 'июн': 6, 'июл': 7, 'авг': 8,
            'сен': 9, 'окт': 10, 'нояб': 11, 'дек': 12
        }
        
        # Добавляем словарь для дней недели с номерами
        self.WEEKDAY_MAP = {
            'понедельник': 0,
            'вторник': 1,
            'среда': 2,
            'четверг': 3,
            'пятница': 4,
            'суббота': 5,
            'воскресенье': 6
        }
        
        # Обратный словарь для дней недели
        self.WEEKDAY_REVERSE = {
            0: 'понедельник',
            1: 'вторник',
            2: 'среда',
            3: 'четверг',
            4: 'пятница',
            5: 'суббота',
            6: 'воскресенье'
        }
        
        # Настройка Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless=new")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--remote-debugging-port=9222")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-setuid-sandbox")
        self.chrome_options.add_argument("--disable-accelerated-2d-canvas")
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--start-maximized")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_argument("--memory-pressure-off")
        self.chrome_options.add_argument("--single-process")
        self.chrome_options.add_argument("--ignore-certificate-errors")

    async def parse_schedule(self) -> tuple:
        """Парсинг расписания"""
        driver = None
        try:
            logger.info("Начало парсинга расписания")
            
            # Используем ChromeDriverManager для автоматической установки и управления ChromeDriver
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.chrome_options
            )
            
            # Увеличиваем таймауты
            driver.set_page_load_timeout(45)
            driver.implicitly_wait(30)
            
            driver.get(self.url)
            logger.info("Страница загружена")
            
            # Увеличиваем время ожидания таблицы
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Даем дополнительное время на загрузку JavaScript
            await asyncio.sleep(3)
            
            schedule_data = {}
            group_set = set()
            teacher_set = set()

            while True:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                schedule_tables = soup.find_all('table')

                if not schedule_tables:
                    return None, None, "❌ Расписание не найдено"

                current_day = ""

                for table in schedule_tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if not cells:
                            continue

                        date_cell = cells[0].get_text(strip=True)
                        if len(date_cell) > 0:
                            try:
                                # Пропускаем заголовок таблицы
                                if date_cell.lower() == 'дата':
                                    continue
                                    
                                current_day = date_cell.strip('()')
                                if current_day not in schedule_data:
                                    schedule_data[current_day] = {}

                                group_cell = row.find('td', class_='ari-tbl-col-1')
                                if group_cell:
                                    group = group_cell.get_text(strip=True)
                                    group_set.add(group)

                                    lesson_data = self._extract_lesson_data(row)
                                    if lesson_data:
                                        if group not in schedule_data[current_day]:
                                            schedule_data[current_day][group] = []
                                        schedule_data[current_day][group].append(lesson_data)
                                        
                                        # Добавляем преподавателя в множество, если он есть
                                        if lesson_data['teacher']:
                                            teacher_set.add(lesson_data['teacher'])

                            except ValueError as ve:
                                logger.warning(f"Ошибка обработки даты: {ve}")
                                continue

                if not self._go_to_next_page(driver):
                    break

            # Сортируем и сохраняем списки
            groups_list = sorted(list(group_set))
            teachers_list = sorted(list(teacher_set))

            logger.info(f"Найдено групп: {len(groups_list)}")
            logger.info(f"Найдено преподавателей: {len(teachers_list)}")
            
            # Сохраняем списки в базу данных
            if len(groups_list) > 0 or len(teachers_list) > 0:
                try:
                    # Сохраняем в SQLite
                    from bot.database import db as sqlite_db
                    sqlite_db.save_groups(groups_list)
                    sqlite_db.save_teachers(teachers_list)
                    logger.info(f"Списки сохранены в SQLite: {len(groups_list)} групп и {len(teachers_list)} преподавателей")
                    
                    # Сохраняем расписание
                    if schedule_data:
                        # Сохраняем в SQLite
                        sqlite_db.save_schedule(schedule_data)
                        logger.info("Расписание сохранено в SQLite")
                    else:
                        logger.error("Расписание пусто!")
                        return None, [], [], "❌ Не удалось получить расписание"
                    
                except Exception as e:
                    logger.error(f"Ошибка сохранения в базы данных: {e}")
                    return None, [], [], "❌ Ошибка сохранения данных"
            else:
                logger.error("Списки групп и преподавателей пусты!")
                return None, [], [], "❌ Не удалось получить данные"

            return schedule_data, groups_list, teachers_list, None

        except Exception as e:
            logger.error(f"Ошибка парсинга: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, [], [], f"❌ Ошибка при получении расписания. Попробуйте позже."
            
        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info("Драйвер Chrome закрыт")
                except Exception as e:
                    logger.error(f"Ошибка при закрытии драйвера: {e}")

    def _extract_lesson_data(self, row):
        """Извлечение данных о паре из строки таблицы"""
        number = row.find('td', class_='ari-tbl-col-2')
        discipline = row.find('td', class_='ari-tbl-col-3')
        teacher = row.find('td', class_='ari-tbl-col-4')
        classroom = row.find('td', class_='ari-tbl-col-5')
        subgroup = row.find('td', class_='ari-tbl-col-6')

        if any([number, discipline, teacher, classroom]):
            return {
                'number': int(number.get_text(strip=True)) if number and number.get_text(strip=True).isdigit() else 0,
                'discipline': discipline.get_text(strip=True) if discipline else '',
                'teacher': teacher.get_text(strip=True) if teacher else '',
                'classroom': classroom.get_text(strip=True) if classroom else '',
                'subgroup': subgroup.get_text(strip=True) if subgroup else '0',
                'group': ''  # Добавляем пустое поле для группы
            }
        return None

    def _go_to_next_page(self, driver):
        """Переход на следующую страницу"""
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "div.dataTables_paginate .fg-button[id$='_next']")
            if "ui-state-disabled" in next_button.get_attribute("class"):
                return False

            old_content = driver.find_element(By.TAG_NAME, "table").text
            driver.execute_script("arguments[0].click();", next_button)
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.TAG_NAME, "table").text != old_content
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при переключении страницы: {e}")
            return False

    def _setup_chrome_options(self):
        """Настройка опций Chrome для Heroku"""
        chrome_options = Options()
        
        # Основные настройки для headless режима
        chrome_options.add_argument('--headless=new')  # Обновленный синтаксис для headless режима
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        
        # Дополнительные настройки для стабильности
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-software-rasterizer')
        
        return chrome_options

    def _parse_date(self, date_str: str) -> datetime:
        """Парсинг даты из различных форматов"""
        try:
            # Очищаем строку от скобок и пробелов
            date_str = date_str.strip('()').strip()
            
            # Пропускаем заголовок таблицы
            if date_str.lower() == 'дата':
                return None
            
            # Пробуем формат '05-март'
            if '-' in date_str:
                day, month = date_str.split('-')
                day = day.strip()
                month = month.strip().lower()
                
                # Проверяем, является ли day числом
                if not day.isdigit():
                    raise ValueError(f"Некорректный день: {day}")
                
                # Добавляем специальную обработку для "мая"
                if month == "мая":
                    month_num = 5
                else:
                    # Пробуем сначала полное название месяца
                    month_num = self.MONTH_MAP.get(month)
                    
                    # Затем пробуем первые 3 буквы, если полное название не найдено
                    if not month_num and len(month) > 3:
                        month_short = month[:3]
                        month_num = self.MONTH_MAP.get(month_short)
                
                if not month_num:
                    raise ValueError(f"Неизвестный месяц: {month}")
                
                # Получаем текущий год и месяц
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                # Если месяц меньше текущего, значит это следующий год
                year = current_year if month_num >= current_month else current_year + 1
                
                return datetime.strptime(f"{day.zfill(2)}-{month_num}-{year}", "%d-%m-%Y")
            
            # Пробуем формат '24.12.2023'
            else:
                return datetime.strptime(date_str, '%d.%m.%Y')
                
        except Exception as e:
            logger.error(f"Ошибка при обработке даты {date_str}: {e}")
            return None

    def _format_date_with_weekday(self, date_str: str) -> str:
        """Форматирует дату с днем недели на русском"""
        try:
            parsed_date = self._parse_date(date_str)
            if not parsed_date:
                logger.error(f"Не удалось распарсить дату: {date_str}")
                return date_str
            
            # Получаем номер дня недели (0-6, где 0 - понедельник)
            weekday = parsed_date.weekday()
            logger.info(f"Получен номер дня недели: {weekday} для даты {date_str}")
            
            # Получаем русское название дня недели
            rus_weekday = self.WEEKDAY_REVERSE.get(weekday)
            if rus_weekday:
                formatted_date = f"{date_str} ({rus_weekday})"
                logger.info(f"Отформатированная дата: {formatted_date}")
                return formatted_date
            
            logger.warning(f"Не найден русский день недели для номера {weekday}")
            return date_str
            
        except Exception as e:
            logger.error(f"Ошибка форматирования даты {date_str}: {e}")
            return date_str

    async def get_schedule_for_day(self, day: str, user_data: dict) -> Union[Dict[str, List[Dict]], str]:
        """Получение расписания на конкретный день"""
        try:
            from bot.database import db as sqlite_db

            role = user_data.get('role')
            if role == 'Студент':
                target = user_data.get('selected_group')
                if not target:
                    return "❌ Не выбрана группа"
                schedule = sqlite_db.get_schedule_by_group(target)
            else:
                target = user_data.get('selected_teacher')
                if not target:
                    return "❌ Не выбран преподаватель"
                schedule = sqlite_db.get_schedule_by_teacher(target)

            if not schedule:
                return ("ℹ️ Информация о расписании\n\n"
                       "В данный момент расписание обновляется на сайте БТК.\n"
                       "Пожалуйста, повторите запрос через несколько минут.")

            target_weekday_num = self.WEEKDAY_MAP.get(day.lower())
            if target_weekday_num is None:
                return f"❌ Некорректный день недели: {day}"

            grouped_schedule: Dict[str, List[Dict]] = {}
            
            # Фильтруем расписание по дню недели и группируем по датам
            for lesson in schedule:
                try:
                    date_str = lesson['date']
                    parsed_date = self._parse_date(date_str)
                    
                    if parsed_date and parsed_date.weekday() == target_weekday_num:
                        formatted_date_with_weekday = self._format_date_with_weekday(date_str)
                        if formatted_date_with_weekday not in grouped_schedule:
                            grouped_schedule[formatted_date_with_weekday] = []
                        grouped_schedule[formatted_date_with_weekday].append(lesson)
                except Exception as e:
                    logger.error(f"Ошибка при обработке даты {date_str}: {e}")
                    continue

            if not grouped_schedule:
                return f"ℹ️ Расписание на {day}\n\nРасписание на этот день не загружено на сайте БТК или занятий нет."

            # Сортируем пары по номеру для каждой даты
            for date_key in grouped_schedule:
                grouped_schedule[date_key].sort(key=lambda x: x['lesson_number'])
            
            return grouped_schedule

        except Exception as e:
            logger.error(f"Ошибка при получении расписания на день: {e}")
            return "❌ Произошла ошибка при получении расписания"

    async def get_full_schedule(self, user_data: dict) -> dict:
        """Получение полного расписания на неделю"""
        try:
            from bot.database import db as sqlite_db

            # Для преподавателя
            if user_data.get('role') == 'Преподаватель':
                teacher = user_data.get('selected_teacher')
                if not teacher:
                    return {}
                schedule = sqlite_db.get_schedule_by_teacher(teacher)
            # Для студента
            else:
                group = user_data.get('selected_group')
                if not group:
                    return {}
                schedule = sqlite_db.get_schedule_by_group(group)

            if not schedule:
                return {}

            # Группируем расписание по датам
            formatted_schedule = {}
            for lesson in schedule:
                date = lesson['date']
                formatted_date = self._format_date_with_weekday(date)
                if formatted_date not in formatted_schedule:
                    formatted_schedule[formatted_date] = []
                formatted_schedule[formatted_date].append(lesson)

            # Сортируем пары по номеру для каждой даты
            for date in formatted_schedule:
                formatted_schedule[date].sort(key=lambda x: x['lesson_number'])

            return formatted_schedule

        except Exception as e:
            logger.error(f"Ошибка при получении полного расписания: {e}")
            return {}

    async def cleanup(self):
        """Очистка ресурсов после парсинга"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass

async def main():
    parser = ScheduleParser()
    schedule, groups, teachers, error = await parser.parse_schedule()
    if error:
        logger.error(error)
    else:
        logger.info("Расписание успешно обновлено")

if __name__ == "__main__":
    asyncio.run(main())