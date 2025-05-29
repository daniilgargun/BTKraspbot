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

class ScheduleParser:
    def __init__(self):
        self.url = "https://bartc.by/index.php/obuchayushchemusya/dnevnoe-otdelenie/tekushchee-raspisanie"
        self.db = Database()
        
        # Добавляем словарь для месяцев
        self.MONTH_MAP = {
            'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
            'мая': 5, 'июн': 6, 'июл': 7, 'авг': 8,
            'сен': 9, 'окт': 10, 'нояб': 11, 'дек': 12
        }
        
        # Определяем операционную систему
        self.is_windows = platform.system() == 'Windows'
        
        # Настройка Chrome options
        self.chrome_options = Options()
        if self.is_windows:
            self.chrome_options.add_argument("--headless=new")
        else:
            # Настройки для Linux на Heroku
            self.chrome_options.binary_location = "/app/.chrome-for-testing/chrome-linux64/chrome"
            self.chrome_options.add_argument("--headless=new")
            self.chrome_options.add_argument("--disable-dev-shm-usage")
            self.chrome_options.add_argument("--no-sandbox")
        
        # Общие настройки
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--remote-debugging-port=9222")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-setuid-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-using")
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
            
            if self.is_windows:
                service = Service()
            else:
                # Для Heroku используем системный ChromeDriver
                service = Service(executable_path="/app/.chrome-for-testing/chromedriver-linux64/chromedriver")
            
            driver = webdriver.Chrome(
                service=service,
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
                    await self.db.cache_groups_and_teachers(groups_list, teachers_list)
                    logger.info(f"Списки сохранены в базу: {len(groups_list)} групп и {len(teachers_list)} преподавателей")
                except Exception as e:
                    logger.error(f"Ошибка сохранения в базу данных: {e}")
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
            # Пробуем формат '24-дек'
            if '-' in date_str:
                day, month = date_str.split('-')
                month = self.MONTH_MAP.get(month.lower())
                if not month:
                    raise ValueError(f"Неизвестный месяц: {month}")
                year = datetime.now().year
                return datetime.strptime(f"{day}-{month}-{year}", "%d-%m-%Y")
            # Пробуем формат '24.12.2023'
            else:
                return datetime.strptime(date_str, '%d.%m.%Y')
        except Exception as e:
            logger.error(f"Ошибка при обработке даты {date_str}: {e}")
            return None
    async def get_schedule_for_day(self, day: str, user_data: dict) -> Union[List[Dict], str]:
        """Получение расписания на конкретный день"""
        try:
            schedule_data = await self.db.get_schedule()
            if not schedule_data:
                logger.warning("Расписание не загружено в базу данных")
                return ("ℹ️ Информация о расписании\n\n"
                       "В данный момент расписание обновляется на сайте БТК.\n"
                       "Пожалуйста, повторите запрос через несколько минут.")

            day = day.lower()
            filtered_schedule = []
            found_any_schedule = False
            found_day_schedule = False

            for date, lessons in schedule_data.items():
                try:
                    if date.lower() == 'дата':
                        continue

                    if not lessons:
                        continue

                    found_any_schedule = True

                    # Преобразуем дату и проверяем день недели
                    if isinstance(date, str):
                        try:
                            if '-' in date:
                                day_num, month = date.split('-')
                                # Проверяем полное название месяца
                                month_mapping = {
                                    'март': 'мар',
                                    'май': 'май',
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
                                month = month_mapping.get(month.lower(), month.lower())
                                month_num = self.MONTH_MAP.get(month.lower())
                                if not month_num:
                                    continue
                                current_date = datetime(datetime.now().year, int(month_num), int(day_num))
                        except ValueError:
                            continue
                        
                    current_day = current_date.strftime('%A').lower()
                    weekday_mapping = {
                        'monday': 'понедельник',
                        'tuesday': 'вторник',
                        'wednesday': 'среда',
                        'thursday': 'четверг',
                        'friday': 'пятница',
                        'saturday': 'суббота',
                        'sunday': 'воскресенье'
                    }
                    current_day = weekday_mapping.get(current_day)
                    
                    if current_day == day:
                        found_day_schedule = True
                        
                        if user_data.get('role') == 'Преподаватель':
                            teacher = user_data.get('selected_teacher')
                            for group_lessons in lessons.values():
                                for lesson in group_lessons:
                                    if lesson.get('teacher') == teacher:
                                        filtered_schedule.append(lesson)
                        else:
                            group = user_data.get('selected_group')
                            if group in lessons:
                                filtered_schedule.extend(lessons[group])

                except Exception as e:
                    logger.error(f"Ошибка при обработке дня {date}: {e}")
                    continue

            if not found_any_schedule:
                return ("ℹ️ Информация о расписании\n\n"
                       "В данный момент на сайте БТК идет обновление расписания.\n"
                       "Пожалуйста, повторите запрос позже.")

            if filtered_schedule:
                return sorted(filtered_schedule, key=lambda x: int(x['number']))
            
            # Если не нашли расписание на этот день вообще
            if not found_day_schedule:
                return (f"ℹ️ Расписание на {day}\n\n"
                       "Расписание на этот день не загружено на сайте БТК.")
            
            # Если есть расписание на этот день, но у конкретной группы/преподавателя нет пар
            if user_data.get('role') == 'Студент':
                return (
                    f"ℹ️ Расписание на {day}\n\n"
                    f"Для группы {user_data.get('selected_group')} занятия в этот день не запланированы.\n\n"
                    "💡 Вы можете:\n"
                    "• Проверить расписание на другой день\n"
                    "• Посмотреть полное расписание на неделю"
                )
            else:
                return (
                    f"ℹ️ Расписание на {day}\n\n"
                    f"Для преподавателя {user_data.get('selected_teacher')} занятия в этот день не запланированы.\n\n"
                    "💡 Вы можете:\n"
                    "• Проверить расписание на другой день\n"
                    "• Посмотреть полное расписание на неделю"
                )

        except Exception as e:
            logger.error(f"Ошибка при получении расписания на день: {e}")
            return ("⚠️ Технические неполадки\n\n"
                    "Произошла временная ошибка при получении расписания.\n"
                    "Пожалуйста, повторите запрос через несколько минут.")

    async def get_full_schedule(self, user_data: dict) -> dict:
        """Получение полного расписания на неделю"""
        try:
            schedule_data = await self.db.get_schedule()
            if not schedule_data:
                return {}

            # Преобразуем даты в нужный формат
            formatted_schedule = {}
            for date, data in schedule_data.items():
                try:
                    if '.' in date:
                        date_obj = datetime.strptime(date, '%d.%m.%Y')
                        new_date = date_obj.strftime('%d-%b').lower()
                    else:
                        new_date = date
                    formatted_schedule[new_date] = data
                except:
                    formatted_schedule[date] = data

            # Для преподавателя
            if user_data.get('role') == 'Преподаватель':
                teacher = user_data.get('selected_teacher')
                if not teacher:
                    return {}

                filtered_schedule = {}
                for date, groups in formatted_schedule.items():
                    filtered_schedule[date] = []
                    for group_name, group_schedule in groups.items():
                        for lesson in group_schedule:
                            if lesson.get('teacher') == teacher:
                                # Копируем урок и добавляем информацию о группе
                                lesson_with_group = lesson.copy()
                                lesson_with_group['group'] = group_name
                                filtered_schedule[date].append(lesson_with_group)
                    
                    # Если на этот день нет пар, удаляем дату
                    if not filtered_schedule[date]:
                        del filtered_schedule[date]
                
                return filtered_schedule

            # Для студента
            else:
                group = user_data.get('selected_group')
                if not group:
                    return {}

                filtered_schedule = {}
                for date, groups in formatted_schedule.items():
                    if group in groups:
                        filtered_schedule[date] = groups[group]
                
                return filtered_schedule

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
    schedule, groups, error = await parser.parse_schedule()
    if error:
        logger.error(error)
    else:
        logger.info("Расписание успешно обновлено")

if __name__ == "__main__":
    asyncio.run(main())