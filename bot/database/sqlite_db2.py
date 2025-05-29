"""
Copyright (c) 2023-2024 Gargun Daniil
Telegram: @Daniilgargun (https://t.me/Daniilgargun)
Contact ID: 1437368782
All rights reserved.

Несанкционированное использование, копирование или распространение 
данного программного обеспечения запрещено.
"""

import sqlite3
import logging
import os
import threading
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Глобальная блокировка для всех операций с БД
DB_LOCK = threading.RLock()

class SQLiteDatabase:
    _instance = None
    
    @classmethod
    def get_instance(cls, db_path=None):
        """Реализация паттерна Singleton для доступа к БД"""
        with DB_LOCK:
            if cls._instance is None:
                # Используем значение по умолчанию, если путь не указан
                if db_path is None:
                    db_path = "bot/database/bot_new.db"
                cls._instance = cls(db_path)
            return cls._instance
    
    def __init__(self, db_path: str = "bot/database/bot_new.db"):
        """Инициализация базы данных SQLite"""
        self.db_path = db_path
        self.conn = None
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self) -> None:
        """Создание директории для базы данных, если она не существует"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _init_db(self) -> None:
        """Инициализация базы данных и создание таблиц"""
        with DB_LOCK:
            try:
                # Путь к схеме базы данных
                schema_path = Path(__file__).parent / "schema.sql"
                if not schema_path.exists():
                    raise FileNotFoundError(f"Файл схемы БД не найден: {schema_path}")
                
                # Проверяем существование старой базы данных и копируем ее при необходимости
                old_db_path = "bot/database/bot.db"
                if os.path.exists(old_db_path) and not os.path.exists(self.db_path):
                    try:
                        shutil.copy2(old_db_path, self.db_path)
                        logger.info(f"Скопирована существующая база данных: {old_db_path} -> {self.db_path}")
                    except Exception as e:
                        logger.warning(f"Не удалось скопировать старую БД: {e}")
                
                # Подключение к базе данных
                self.conn = sqlite3.connect(
                    self.db_path, 
                    timeout=60.0,
                    check_same_thread=False,
                    isolation_level=None  # Автоматические транзакции
                )
                self.conn.row_factory = sqlite3.Row
                
                # Оптимизация параметров базы данных
                self.conn.execute("PRAGMA journal_mode=DELETE")  # Отключаем WAL для избежания блокировок
                self.conn.execute("PRAGMA synchronous=NORMAL")
                self.conn.execute("PRAGMA cache_size=10000")
                self.conn.execute("PRAGMA busy_timeout=30000")
                
                # Проверяем существование таблиц
                table_exists = self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                ).fetchone()
                
                # Создаем таблицы, если они не существуют
                if not table_exists:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        self.conn.executescript(f.read())
                    logger.info("Созданы новые таблицы в базе данных")
                
                logger.info("База данных SQLite успешно инициализирована")
                
            except Exception as e:
                logger.error(f"Ошибка при инициализации базы данных: {e}")
                if self.conn:
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None
                raise
    
    def _ensure_connection(self):
        """Проверяет и восстанавливает соединение при необходимости"""
        with DB_LOCK:
            if self.conn is None:
                self._init_db()
                return
                
            try:
                # Проверяем соединение простым запросом
                self.conn.execute("SELECT 1").fetchone()
            except (sqlite3.Error, AttributeError):
                logger.warning("Соединение с базой данных утеряно. Восстанавливаем...")
                try:
                    if self.conn:
                        self.conn.close()
                except:
                    pass
                self.conn = None
                self._init_db()

    def close(self) -> None:
        """Закрытие соединения с базой данных"""
        with DB_LOCK:
            if self.conn:
                try:
                    self.conn.close()
                    logger.info("Соединение с базой данных закрыто")
                except Exception as e:
                    logger.error(f"Ошибка при закрытии соединения с БД: {e}")
                finally:
                    self.conn = None

    def create_backup(self) -> None:
        """Создание резервной копии базы данных"""
        with DB_LOCK:
            self._ensure_connection()
            try:
                # Создаем директорию для резервных копий
                backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
                os.makedirs(backup_dir, exist_ok=True)
                
                # Имя файла с текущей датой и временем
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"bot_{timestamp}.db")
                
                # Закрываем соединение перед копированием
                self.conn.execute("PRAGMA wal_checkpoint(FULL)")
                
                # Простое копирование файла
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"Резервная копия базы данных создана: {backup_path}")
                
                # Очистка старых резервных копий (оставляем последние 5)
                backup_files = sorted([
                    os.path.join(backup_dir, f) 
                    for f in os.listdir(backup_dir) 
                    if f.endswith('.db')
                ])
                
                if len(backup_files) > 5:
                    for old_file in backup_files[:-5]:
                        os.remove(old_file)
                        logger.info(f"Удалена устаревшая резервная копия: {old_file}")
                        
            except Exception as e:
                logger.error(f"Ошибка при создании резервной копии: {e}")

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict[str, Any]]]:
        """Выполнение SQL-запроса с повторными попытками при блокировке"""
        retry_count = 0
        max_retries = 5
        base_delay = 0.5
        result = None
        
        while retry_count <= max_retries:
            try:
                with DB_LOCK:
                    self._ensure_connection()
                    
                    cursor = self.conn.cursor()
                    cursor.execute("BEGIN IMMEDIATE")
                    
                    cursor.execute(query, params)
                    
                    if query.strip().upper().startswith('SELECT'):
                        rows = cursor.fetchall()
                        if rows and cursor.description:
                            columns = [column[0] for column in cursor.description]
                            result = [dict(zip(columns, row)) for row in rows]
                    
                    self.conn.execute("COMMIT")
                    
                return result
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                
                # Попытка отката транзакции
                try:
                    self.conn.execute("ROLLBACK")
                except:
                    pass
                
                if "database is locked" in error_msg and retry_count < max_retries:
                    retry_count += 1
                    delay = base_delay * (2 ** retry_count)  # Экспоненциальная задержка
                    logger.warning(f"База данных заблокирована, повторная попытка {retry_count}/{max_retries} через {delay:.2f} сек")
                    time.sleep(delay)
                else:
                    logger.error(f"Ошибка при выполнении запроса: {e}")
                    raise
                    
            except Exception as e:
                # Попытка отката транзакции
                try:
                    self.conn.execute("ROLLBACK")
                except:
                    pass
                    
                logger.error(f"Ошибка при выполнении запроса: {e}")
                raise
                
        # Если все попытки исчерпаны
        raise sqlite3.OperationalError("Не удалось выполнить запрос из-за блокировки базы данных")

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Выполнение множества SQL-запросов с одинаковой структурой"""
        if not params_list:
            return
            
        retry_count = 0
        max_retries = 5
        base_delay = 0.5
        
        while retry_count <= max_retries:
            try:
                with DB_LOCK:
                    self._ensure_connection()
                    
                    cursor = self.conn.cursor()
                    cursor.execute("BEGIN IMMEDIATE")
                    
                    cursor.executemany(query, params_list)
                    
                    self.conn.execute("COMMIT")
                    
                return
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                
                # Попытка отката транзакции
                try:
                    self.conn.execute("ROLLBACK")
                except:
                    pass
                
                if "database is locked" in error_msg and retry_count < max_retries:
                    retry_count += 1
                    delay = base_delay * (2 ** retry_count)  # Экспоненциальная задержка
                    logger.warning(f"База данных заблокирована, повторная попытка {retry_count}/{max_retries} через {delay:.2f} сек")
                    time.sleep(delay)
                else:
                    logger.error(f"Ошибка при выполнении множества запросов: {e}")
                    raise
                    
            except Exception as e:
                # Попытка отката транзакции
                try:
                    self.conn.execute("ROLLBACK")
                except:
                    pass
                    
                logger.error(f"Ошибка при выполнении множества запросов: {e}")
                raise
                
        # Если все попытки исчерпаны
        raise sqlite3.OperationalError("Не удалось выполнить запросы из-за блокировки базы данных")

    # Методы для работы с пользователями
    def create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None, role: str = 'student') -> None:
        """Создание нового пользователя"""
        query = """
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, role)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute_query(query, (user_id, username, first_name, last_name, role))
        
        # Создаем настройки пользователя
        query = """
        INSERT OR IGNORE INTO user_settings (user_id)
        VALUES (?)
        """
        self.execute_query(query, (user_id,))
        logger.info(f"Пользователь {user_id} создан")

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        query = """
        SELECT u.*, us.selected_group, us.selected_teacher, us.notifications_enabled
        FROM users u
        LEFT JOIN user_settings us ON u.user_id = us.user_id
        WHERE u.user_id = ?
        """
        result = self.execute_query(query, (user_id,))
        return result[0] if result else None

    def update_user(self, user_id: int, **kwargs) -> None:
        """Обновление данных пользователя"""
        valid_fields = {'username', 'first_name', 'last_name', 'role'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return

        query = f"""
        UPDATE users
        SET {', '.join(f'{k} = ?' for k in update_fields)}
        WHERE user_id = ?
        """
        params = tuple(update_fields.values()) + (user_id,)
        self.execute_query(query, params)
        logger.info(f"Данные пользователя {user_id} обновлены")

    def update_user_settings(self, user_id: int, **kwargs) -> None:
        """Обновление настроек пользователя"""
        valid_fields = {'selected_group', 'selected_teacher', 'notifications_enabled'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return

        query = f"""
        UPDATE user_settings
        SET {', '.join(f'{k} = ?' for k in update_fields)}
        WHERE user_id = ?
        """
        params = tuple(update_fields.values()) + (user_id,)
        self.execute_query(query, params)
        logger.info(f"Настройки пользователя {user_id} обновлены")

    def delete_user(self, user_id: int) -> None:
        """Удаление пользователя"""
        query = "DELETE FROM users WHERE user_id = ?"
        self.execute_query(query, (user_id,))
        logger.info(f"Пользователь {user_id} удален")

    # Методы для работы с расписанием
    def add_schedule(self, date: str, group_name: str, teacher_name: str, 
                    lesson_number: int, discipline: str, classroom: str, 
                    subgroup: str = '0') -> None:
        """Добавление записи в расписание"""
        # Проверяем/добавляем группу
        self.execute_query(
            "INSERT OR IGNORE INTO groups (group_name) VALUES (?)",
            (group_name,)
        )
        
        # Проверяем/добавляем преподавателя
        self.execute_query(
            "INSERT OR IGNORE INTO teachers (full_name) VALUES (?)",
            (teacher_name,)
        )
        
        # Добавляем запись в расписание
        query = """
        INSERT INTO schedule 
        (date, group_name, teacher_name, lesson_number, discipline, classroom, subgroup)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_query(query, (
            date, group_name, teacher_name, lesson_number, 
            discipline, classroom, subgroup
        ))
        logger.info(f"Добавлено расписание для группы {group_name} на {date}")

    def get_schedule_by_group(self, group_name: str, date: str = None) -> List[Dict[str, Any]]:
        """Получение расписания для группы"""
        query = """
        SELECT *
        FROM schedule
        WHERE group_name = ?
        """
        params = [group_name]
        
        if date:
            query += " AND date = ?"
            params.append(date)
            
        query += " ORDER BY date, lesson_number"
        return self.execute_query(query, tuple(params)) or []

    def get_schedule_by_teacher(self, teacher_name: str, date: str = None) -> List[Dict[str, Any]]:
        """Получение расписания для преподавателя"""
        query = """
        SELECT *
        FROM schedule
        WHERE teacher_name = ?
        """
        params = [teacher_name]
        
        if date:
            query += " AND date = ?"
            params.append(date)
            
        query += " ORDER BY date, lesson_number"
        return self.execute_query(query, tuple(params)) or []

    def update_schedule(self, schedule_id: int, **kwargs) -> None:
        """Обновление записи в расписании"""
        valid_fields = {'date', 'group_name', 'teacher_name', 'lesson_number', 
                       'discipline', 'classroom', 'subgroup'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return

        query = f"""
        UPDATE schedule
        SET {', '.join(f'{k} = ?' for k in update_fields)}
        WHERE schedule_id = ?
        """
        params = tuple(update_fields.values()) + (schedule_id,)
        self.execute_query(query, params)
        logger.info(f"Расписание с ID {schedule_id} обновлено")

    def delete_schedule(self, schedule_id: int) -> None:
        """Удаление записи из расписания"""
        query = "DELETE FROM schedule WHERE schedule_id = ?"
        self.execute_query(query, (schedule_id,))
        logger.info(f"Расписание с ID {schedule_id} удалено")

    def clear_schedule(self, date: str = None) -> None:
        """Очистка всего расписания или на конкретную дату"""
        if date:
            query = "DELETE FROM schedule WHERE date = ?"
            self.execute_query(query, (date,))
            logger.info(f"Расписание на {date} очищено")
        else:
            query = "DELETE FROM schedule"
            self.execute_query(query)
            logger.info("Все расписание очищено")

    def save_groups(self, groups: List[str]) -> None:
        """Сохранение списка групп в базу данных"""
        try:
            # Очищаем текущий список групп
            self.execute_query("DELETE FROM groups")
            
            # Добавляем новые группы
            query = "INSERT INTO groups (group_name) VALUES (?)"
            self.execute_many(query, [(group,) for group in groups])
            logger.info(f"Сохранено {len(groups)} групп в SQLite")
        except Exception as e:
            logger.error(f"Ошибка при сохранении групп: {e}")
            raise

    def save_teachers(self, teachers: List[str]) -> None:
        """Сохранение списка преподавателей в базу данных"""
        try:
            # Очищаем текущий список преподавателей
            self.execute_query("DELETE FROM teachers")
            
            # Добавляем новых преподавателей
            query = "INSERT INTO teachers (full_name) VALUES (?)"
            self.execute_many(query, [(teacher,) for teacher in teachers])
            logger.info(f"Сохранено {len(teachers)} преподавателей в SQLite")
        except Exception as e:
            logger.error(f"Ошибка при сохранении преподавателей: {e}")
            raise

    def save_schedule(self, schedule_data: Dict[str, Dict[str, List[Dict]]]) -> None:
        """Сохранение расписания в базу данных"""
        try:
            # Очищаем текущее расписание
            self.execute_query("DELETE FROM schedule")
            
            # Подготавливаем данные для вставки
            schedule_records = []
            for date, groups in schedule_data.items():
                for group_name, lessons in groups.items():
                    for lesson in lessons:
                        record = (
                            date,
                            group_name,
                            lesson.get('teacher', ''),
                            lesson.get('number', 0),
                            lesson.get('discipline', ''),
                            lesson.get('classroom', ''),
                            lesson.get('subgroup', '0')
                        )
                        schedule_records.append(record)
            
            # Вставляем записи
            query = """
            INSERT INTO schedule 
            (date, group_name, teacher_name, lesson_number, discipline, classroom, subgroup)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_many(query, schedule_records)
            logger.info(f"Сохранено {len(schedule_records)} записей расписания в SQLite")
        except Exception as e:
            logger.error(f"Ошибка при сохранении расписания: {e}")
            raise

    def get_all_groups(self) -> List[str]:
        """Получение списка всех групп"""
        query = "SELECT group_name FROM groups ORDER BY group_name"
        result = self.execute_query(query)
        return [row['group_name'] for row in result] if result else []

    def get_all_teachers(self) -> List[str]:
        """Получение списка всех преподавателей"""
        query = "SELECT full_name FROM teachers ORDER BY full_name"
        result = self.execute_query(query)
        return [row['full_name'] for row in result] if result else []
    
    async def get_last_checked_dates(self):
        """Получение списка последних проверенных дат в формате списка"""
        try:
            # Проверяем, существует ли таблица old_last_checked_dates (старая версия)
            old_table_exists = self.execute_query(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='last_checked_dates' AND sql LIKE '%date TEXT PRIMARY KEY%'
                """
            )
            
            if old_table_exists:
                logger.warning("🔄 Обнаружена старая версия таблицы last_checked_dates. Выполняется миграция...")
                # Получаем данные из старой таблицы
                old_dates = self.execute_query("SELECT date FROM last_checked_dates")
                old_dates_list = [row['date'] for row in old_dates] if old_dates else []
                
                # Переименовываем старую таблицу
                self.execute_query("ALTER TABLE last_checked_dates RENAME TO old_last_checked_dates")
                
                # Создаем новую таблицу
                self.execute_query(
                    """
                    CREATE TABLE IF NOT EXISTS last_checked_dates (
                        id INTEGER PRIMARY KEY,
                        dates TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                
                # Переносим данные в новую таблицу, если они есть
                if old_dates_list:
                    dates_str = ','.join(old_dates_list)
                    self.execute_query(
                        """
                        INSERT INTO last_checked_dates (dates, updated_at)
                        VALUES (?, CURRENT_TIMESTAMP)
                        """,
                        (dates_str,)
                    )
                    
                logger.info(f"✅ Миграция таблицы last_checked_dates успешно выполнена. Перенесено {len(old_dates_list)} дат")
            
            # Проверяем, существует ли таблица новой версии
            table_exists = self.execute_query(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='last_checked_dates'
                """
            )
            
            if not table_exists:
                # Создаем таблицу, если она не существует
                self.execute_query(
                    """
                    CREATE TABLE IF NOT EXISTS last_checked_dates (
                        id INTEGER PRIMARY KEY,
                        dates TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                logger.info("🏗️ Создана таблица last_checked_dates")
                return []
            
            # Пробуем получить данные по новой схеме
            result = self.execute_query(
                """
                SELECT dates FROM last_checked_dates
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
            
            if result and result[0] and 'dates' in result[0] and result[0]['dates']:
                # Преобразуем строку с датами в список
                dates_str = result[0]['dates']
                dates_list = dates_str.split(',')
                logger.info(f"✅ Получено {len(dates_list)} последних проверенных дат")
                return dates_list
            
            logger.info("⚠️ Не найдены ранее проверенные даты")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка SQLite при получении последних проверенных дат: {e}")
            import traceback
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            return []

    async def update_last_checked_dates(self, dates_str):
        """
        Обновление списка последних проверенных дат
        
        Args:
            dates_str (str): Строка дат, разделенных запятыми
            
        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            # Проверяем, существует ли таблица last_checked_dates
            table_exists = self.execute_query(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='last_checked_dates'
                """
            )
            
            if not table_exists:
                # Создаем таблицу, если она не существует
                self.execute_query(
                    """
                    CREATE TABLE IF NOT EXISTS last_checked_dates (
                        id INTEGER PRIMARY KEY,
                        dates TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                logger.info("🏗️ Создана таблица last_checked_dates")
            
            # Вставляем новую запись
            self.execute_query(
                """
                INSERT INTO last_checked_dates (dates, updated_at)
                VALUES (?, CURRENT_TIMESTAMP)
                """,
                (dates_str,)
            )
            
            # Оставляем только последние 5 записей для экономии места
            self.execute_query(
                """
                DELETE FROM last_checked_dates
                WHERE id NOT IN (
                    SELECT id FROM last_checked_dates
                    ORDER BY updated_at DESC
                    LIMIT 5
                )
                """
            )
            
            logger.info(f"✅ Успешно обновлен список последних проверенных дат")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка SQLite при обновлении последних проверенных дат: {e}")
            return False

    def get_users_with_notifications(self) -> List[int]:
        """Получение списка ID пользователей с включенными уведомлениями"""
        try:
            # Получаем пользователей с включенными уведомлениями
            result = self.execute_query(
                """
                SELECT u.user_id
                FROM users u
                JOIN user_settings us ON u.user_id = us.user_id
                WHERE us.notifications_enabled = 1
                """
            )
            
            user_ids = [row['user_id'] for row in result] if result else []
                
            logger.info(f"Получен список пользователей с уведомлениями: {len(user_ids)} пользователей")
            return user_ids
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей с уведомлениями: {e}")
            return []

# Создание экземпляра базы данных
db = SQLiteDatabase.get_instance() 