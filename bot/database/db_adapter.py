"""
Copyright (c) 2023-2024 Gargun Daniil
Telegram: @Daniilgargun (https://t.me/Daniilgargun)
Contact ID: 1437368782
All rights reserved.

Несанкционированное использование, копирование или распространение 
данного программного обеспечения запрещено.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from bot.database import db as sqlite_db
from bot.config import logger
from datetime import datetime

class DatabaseAdapter:
    """
    Адаптер для работы с базой данных SQLite.
    Предоставляет тот же интерфейс, что и Firebase, но использует SQLite.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            logger.info("Начало инициализации адаптера базы данных")
            self.db = sqlite_db
            self._initialize_copyright_protection()
            self._initialize_tables()
            self._initialized = True
            logger.info("Адаптер базы данных успешно инициализирован")
            
    def _initialize_copyright_protection(self):
        """Скрытая функция для защиты авторских прав"""
        try:
            # Создаем таблицу для защиты авторских прав, если ее нет
            query = """
            CREATE TABLE IF NOT EXISTS copyright_info (
                id INTEGER PRIMARY KEY,
                author TEXT NOT NULL,
                launch_time TEXT NOT NULL,
                env_info TEXT NOT NULL,
                instance_id TEXT NOT NULL
            )
            """
            self.db.execute_query(query)
            
            # Добавляем запись о запуске
            import os
            import uuid
            import platform
            
            author_info = "Gargun Daniil - @Daniilgargun"
            launch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Собираем информацию об окружении
            env_info = {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python": platform.python_version(),
                "user": os.environ.get("USERNAME", "unknown"),
                "hostname": platform.node()
            }
            
            # Генерируем уникальный ID для этого экземпляра
            instance_id = str(uuid.uuid4())
            
            # Записываем информацию в базу данных
            insert_query = """
            INSERT INTO copyright_info (author, launch_time, env_info, instance_id)
            VALUES (?, ?, ?, ?)
            """
            self.db.execute_query(
                insert_query,
                (author_info, launch_time, str(env_info), instance_id)
            )
            
            logger.debug("Copyright protection system initialized")
        except Exception as e:
            # Скрываем любые ошибки, чтобы не прерывать работу бота
            logger.debug(f"Copyright protection initialization: {str(e)}")

    def _initialize_tables(self):
        """Инициализация необходимых таблиц"""
        try:
            # Создаем таблицу для хранения графика учебного процесса
            query = """
            CREATE TABLE IF NOT EXISTS schedule_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
            """
            self.db.execute_query(query)
            logger.info("Таблица schedule_photos успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации таблиц: {e}")

    async def create_user(self, user_id: int) -> bool:
        """Создание нового пользователя с дефолтными значениями"""
        try:
            # Проверяем, существует ли пользователь
            user_data = sqlite_db.get_user(user_id)
            if user_data:
                logger.info(f"Пользователь {user_id} уже существует")
                return True
                
            # Создаем пользователя в SQLite
            sqlite_db.create_user(
                user_id=user_id,
                username=None,
                first_name=None,
                last_name=None,
                role='Студент'  # По умолчанию роль - студент
            )
            logger.info(f"Пользователь {user_id} успешно создан")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        try:
            # Получаем пользователя из SQLite
            user_data = sqlite_db.get_user(user_id)
            if user_data:
                # Преобразуем данные в формат, ожидаемый приложением
                result = {
                    'user_id': user_data['user_id'],
                    'username': user_data['username'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'role': user_data['role'],
                    'selected_group': user_data['selected_group'],
                    'selected_teacher': user_data['selected_teacher'],
                    'notifications_enabled': user_data['notifications_enabled']
                }
                logger.info(f"Получены данные пользователя {user_id}")
                return result
            logger.warning(f"Пользователь {user_id} не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
            return None

    async def user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        try:
            user_data = sqlite_db.get_user(user_id)
            exists = user_data is not None
            
            # Если пользователь не существует, создаем его
            if not exists:
                logger.info(f"Пользователь {user_id} не найден, создаем нового пользователя")
                sqlite_db.create_user(
                    user_id=user_id,
                    username=None,
                    first_name=None,
                    last_name=None,
                    role='Студент'  # По умолчанию роль - студент
                )
                exists = True
                
            logger.info(f"Проверка существования пользователя {user_id}: {'существует' if exists else 'не существует'}")
            return exists
        except Exception as e:
            logger.error(f"Ошибка при проверке существования пользователя {user_id}: {e}")
            return False

    async def update_user_role(self, user_id: int, role: str) -> bool:
        """Обновление роли пользователя"""
        try:
            sqlite_db.update_user(user_id, role=role)
            logger.info(f"Роль пользователя {user_id} обновлена на {role}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении роли пользователя {user_id}: {e}")
            return False

    async def update_selected_teacher(self, user_id: int, teacher: str) -> bool:
        """Обновление выбранного преподавателя"""
        try:
            sqlite_db.update_user_settings(user_id, selected_teacher=teacher)
            logger.info(f"Выбранный преподаватель пользователя {user_id} обновлен на {teacher}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении преподавателя для пользователя {user_id}: {e}")
            return False

    async def update_selected_group(self, user_id: int, group: str) -> bool:
        """Обновление выбранной группы"""
        try:
            sqlite_db.update_user_settings(user_id, selected_group=group)
            logger.info(f"Выбранная группа пользователя {user_id} обновлена на {group}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении группы для пользователя {user_id}: {e}")
            return False

    async def get_groups(self) -> List[str]:
        """Получение списка всех групп"""
        try:
            groups = sqlite_db.get_all_groups()
            logger.info(f"Получен список групп: {len(groups)} групп")
            return groups
        except Exception as e:
            logger.error(f"Ошибка при получении списка групп: {e}")
            return []

    async def get_teachers(self) -> List[str]:
        """Получение списка всех преподавателей"""
        try:
            teachers = sqlite_db.get_all_teachers()
            logger.info(f"Получен список преподавателей: {len(teachers)} преподавателей")
            return teachers
        except Exception as e:
            logger.error(f"Ошибка при получении списка преподавателей: {e}")
            return []

    async def get_users_with_notifications(self) -> List[int]:
        """Получение списка ID пользователей с включенными уведомлениями"""
        try:
            # Получаем пользователей с включенными уведомлениями
            users = sqlite_db.execute_query(
                """
                SELECT u.user_id
                FROM users u
                JOIN user_settings us ON u.user_id = us.user_id
                WHERE us.notifications_enabled = 1
                """
            )
            
            result = [user['user_id'] for user in users] if users else []
                
            logger.info(f"Получен список пользователей с уведомлениями: {len(result)} пользователей")
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей с уведомлениями: {e}")
            return []

    async def toggle_notifications(self, user_id: int, enabled: bool) -> bool:
        """Включение/выключение уведомлений для пользователя"""
        try:
            sqlite_db.update_user_settings(user_id, notifications_enabled=enabled)
            status = "включены" if enabled else "выключены"
            logger.info(f"Уведомления для пользователя {user_id} {status}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при изменении статуса уведомлений для пользователя {user_id}: {e}")
            return False

    async def get_schedule(self) -> Optional[Dict[str, Any]]:
        """Получение текущего расписания"""
        try:
            # Получаем все расписание из SQLite
            all_groups = sqlite_db.get_all_groups()
            all_schedule = {}
            
            for group in all_groups:
                group_schedule = sqlite_db.get_schedule_by_group(group)
                if group_schedule:
                    # Группируем расписание по датам
                    for lesson in group_schedule:
                        date = lesson['date']
                        if date not in all_schedule:
                            all_schedule[date] = {}
                        if group not in all_schedule[date]:
                            all_schedule[date][group] = []
                        all_schedule[date][group].append({
                            'number': lesson['lesson_number'],
                            'discipline': lesson['discipline'],
                            'teacher': lesson['teacher_name'],
                            'classroom': lesson['classroom'],
                            'subgroup': lesson.get('subgroup', '0')
                        })
            
            logger.info(f"Получено расписание для  {len(all_groups)} групп")
            return all_schedule
        except Exception as e:
            logger.error(f"Ошибка при получении расписания: {e}")
            return None

    async def update_schedule(self, schedule_data: Dict[str, Any]) -> bool:
        """Обновление расписания"""
        try:
            # Расписание уже сохранено в SQLite в методе parse_schedule
            logger.info("Расписание успешно обновлено в SQLite")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении расписания: {e}")
            return False

    async def get_cached_groups(self) -> List[str]:
        """Получение кэшированного списка групп"""
        try:
            groups = sqlite_db.get_all_groups()
            logger.info(f"Получен кэшированный список групп: {len(groups)} групп")
            return groups
        except Exception as e:
            logger.error(f"Ошибка при получении кэшированных групп: {e}")
            return []

    async def get_cached_teachers(self) -> List[str]:
        """Получение кэшированного списка преподавателей"""
        try:
            teachers = sqlite_db.get_all_teachers()
            logger.info(f"Получен кэшированный список преподавателей: {len(teachers)} преподавателей")
            return teachers
        except Exception as e:
            logger.error(f"Ошибка при получении кэшированных преподавателей: {e}")
            return []

    async def save_schedule_image(self, collection_name: str, image_data: dict) -> bool:
        """Сохранение данных изображения расписания"""
        try:
            # Проверяем существование таблицы
            table_exists = self.db.execute_query(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schedule_images'
                """
            )
            
            if not table_exists:
                # Создаем таблицу, если она не существует
                query = """
                CREATE TABLE IF NOT EXISTS schedule_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    file_unique_id TEXT NOT NULL,
                    caption TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
                """
                self.db.execute_query(query)
                logger.info("Создана таблица schedule_images")
            
            # Деактивируем все предыдущие изображения этого типа
            query = "UPDATE schedule_images SET is_active = 0 WHERE type = ?"
            self.db.execute_query(query, (collection_name,))
            
            # Сохраняем новое изображение
            query = """
            INSERT INTO schedule_images (type, file_id, file_unique_id, caption, uploaded_at, is_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            """
            self.db.execute_query(
                query, 
                (
                    collection_name, 
                    image_data.get('file_id', ''),
                    image_data.get('file_unique_id', ''),
                    image_data.get('caption', '')
                )
            )
            
            # Проверяем, что изображение сохранилось
            verify_query = """
            SELECT file_id FROM schedule_images 
            WHERE type = ? AND is_active = 1 
            ORDER BY uploaded_at DESC LIMIT 1
            """
            result = self.db.execute_query(verify_query, (collection_name,))
            
            if result and len(result) > 0:
                logger.info(f"Изображение для {collection_name} успешно сохранено")
                return True
            else:
                logger.error(f"Изображение для {collection_name} не было сохранено в базе данных")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения для {collection_name}: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            return False

    async def get_schedule_image(self, collection_name: str) -> Optional[Dict]:
        """Получение данных изображения расписания"""
        try:
            # Проверяем существование таблицы
            table_exists = self.db.execute_query(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schedule_images'
                """
            )
            
            if not table_exists:
                logger.warning(f"Таблица schedule_images не существует")
                return None
            
            # Получаем активное изображение указанного типа
            query = """
            SELECT file_id, file_unique_id, caption 
            FROM schedule_images 
            WHERE type = ? AND is_active = 1 
            ORDER BY uploaded_at DESC LIMIT 1
            """
            result = self.db.execute_query(query, (collection_name,))
            
            if not result or len(result) == 0:
                logger.warning(f"Активное изображение для {collection_name} не найдено")
                return None
                
            # Формируем словарь с результатами
            image_data = {
                'file_id': result[0]['file_id'],
                'file_unique_id': result[0]['file_unique_id'],
                'caption': result[0]['caption']
            }
            
            logger.info(f"Найдено изображение для {collection_name}: {image_data['file_id'][:20]}...")
            return image_data
        except Exception as e:
            logger.error(f"Ошибка при получении изображения для {collection_name}: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            return None

    async def get_all_users(self) -> list:
        """Получение списка всех пользователей"""
        try:
            # Получаем всех пользователей из SQLite
            query = """
            SELECT u.*, us.selected_group, us.selected_teacher, us.notifications_enabled
            FROM users u
            LEFT JOIN user_settings us ON u.user_id = us.user_id
            """
            users = sqlite_db.execute_query(query)
            result = []
            for user in users:
                user_dict = dict(user)
                result.append(user_dict)
            
            logger.info(f"Получено {len(result)} пользователей из базы данных")
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []

    async def get_last_update_time(self) -> str:
        """Заглушка для получения времени последнего обновления кэша"""
        return datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    async def update_cache_time(self):
        """Заглушка для обновления времени последнего обновления кэша"""
        return True

    def get_admin_id(self) -> int:
        """Получение ID основного администратора из конфига"""
        try:
            from bot.config import config
            return config.ADMIN_ID
        except Exception as e:
            logger.error(f"Ошибка при получении ID администратора: {e}")
            return None
            
    def get_admin_ids(self) -> list:
        """Получение списка ID всех администраторов"""
        try:
            from bot.config import config
            return config.ADMIN_IDS
        except Exception as e:
            logger.error(f"Ошибка при получении списка ID администраторов: {e}")
            return [self.get_admin_id()] if self.get_admin_id() else []
            
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        try:
            from bot.config import config
            return config.is_admin(user_id)
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора: {e}")
            admin_id = self.get_admin_id()
            return user_id == admin_id if admin_id else False

    async def get_last_checked_dates(self):
        """
        Получение списка последних проверенных дат.
        Возвращает список дат в формате ['dd.mm.yyyy', ...] или пустой список.
        """
        try:
            logger.info("🔄 Получение списка последних проверенных дат")
            result = await self.db.get_last_checked_dates()
            
            if not result:
                logger.info("ℹ️ Список последних проверенных дат пуст")
                return []
                
            if isinstance(result, str):
                dates = result.split(',')
                logger.info(f"✅ Получено {len(dates)} последних проверенных дат")
                return dates
            elif isinstance(result, list):
                logger.info(f"✅ Получено {len(result)} последних проверенных дат")
                return result
            else:
                logger.warning(f"⚠️ Неожиданный формат списка дат: {type(result)}")
                return []
        except Exception as e:
            logger.error(f"❌ Ошибка при получении последних проверенных дат: {e}")
            return []

    async def update_last_checked_dates(self, dates):
        """
        Обновление списка последних проверенных дат.
        Параметр dates - список дат в формате ['dd.mm.yyyy', ...].
        Возвращает True при успешном обновлении.
        """
        if not dates:
            logger.warning("⚠️ Попытка обновить пустой список дат")
            return False
            
        try:
            logger.info(f"🔄 Обновление списка последних проверенных дат (всего {len(dates)})")
            
            # Проверка формата дат и преобразование списка в строку
            valid_dates = []
            for date_str in dates:
                try:
                    # Проверяем, соответствует ли дата формату dd.mm.yyyy
                    datetime.strptime(date_str, "%d.%m.%Y")
                    valid_dates.append(date_str)
                except ValueError:
                    logger.warning(f"⚠️ Дата '{date_str}' имеет неверный формат и будет пропущена")
            
            if not valid_dates:
                logger.error("❌ Нет валидных дат для обновления")
                return False
                
            logger.info(f"ℹ️ После проверки осталось {len(valid_dates)} валидных дат")
            
            # Сортируем даты для удобства отладки
            valid_dates.sort()
            
            # Преобразуем список в строку, разделенную запятыми
            dates_str = ','.join(valid_dates)
            
            # Обновляем в базе данных
            result = await self.db.update_last_checked_dates(dates_str)
            
            if result:
                logger.info("✅ Список последних проверенных дат успешно обновлен")
                return True
            else:
                logger.error("❌ Не удалось обновить список последних проверенных дат")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении списка последних проверенных дат: {e}")
            import traceback
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            return False

    async def cache_groups_and_teachers(self, groups: list, teachers: list) -> bool:
        """Заглушка для кэширования списков групп и преподавателей"""
        return True

    async def get_banned_users(self) -> list:
        """Получение списка забаненных пользователей"""
        try:
            # Проверяем наличие колонки is_banned в таблице users
            table_info = sqlite_db.execute_query("PRAGMA table_info(users)")
            has_ban_column = any(row['name'] == 'is_banned' for row in table_info)
            
            if not has_ban_column:
                # Добавляем колонку is_banned, если её нет
                sqlite_db.execute_query("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0")
                sqlite_db.execute_query("ALTER TABLE users ADD COLUMN ban_reason TEXT")
                sqlite_db.execute_query("ALTER TABLE users ADD COLUMN ban_date TIMESTAMP")
                logger.info("Добавлены колонки для бана пользователей")
            
            # Получаем список забаненных пользователей
            banned_users = sqlite_db.execute_query(
                """
                SELECT u.*, us.selected_group, us.selected_teacher 
                FROM users u
                LEFT JOIN user_settings us ON u.user_id = us.user_id
                WHERE u.is_banned = 1
                """
            )
            
            result = []
            for user in banned_users:
                user_dict = dict(user)
                result.append(user_dict)
                
            logger.info(f"Получен список забаненных пользователей: {len(result)} чел.")
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении списка забаненных пользователей: {e}")
            return []

    async def ban_user(self, user_id: int, reason: str = "Нарушение правил") -> bool:
        """Бан пользователя"""
        try:
            # Проверяем наличие колонки is_banned в таблице users
            table_info = sqlite_db.execute_query("PRAGMA table_info(users)")
            has_ban_column = any(row['name'] == 'is_banned' for row in table_info)
            
            if not has_ban_column:
                # Добавляем колонку is_banned, если её нет
                sqlite_db.execute_query("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0")
                sqlite_db.execute_query("ALTER TABLE users ADD COLUMN ban_reason TEXT")
                sqlite_db.execute_query("ALTER TABLE users ADD COLUMN ban_date TIMESTAMP")
                logger.info("Добавлены колонки для бана пользователей")
            
            # Баним пользователя
            sqlite_db.execute_query(
                """
                UPDATE users 
                SET is_banned = 1, ban_reason = ?, ban_date = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (reason, user_id)
            )
            
            logger.info(f"Пользователь {user_id} забанен. Причина: {reason}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при бане пользователя {user_id}: {e}")
            return False

    async def unban_user(self, user_id: int) -> bool:
        """Разбан пользователя"""
        try:
            # Разбаниваем пользователя
            sqlite_db.execute_query(
                """
                UPDATE users 
                SET is_banned = 0, ban_reason = NULL
                WHERE user_id = ?
                """,
                (user_id,)
            )
            
            logger.info(f"Пользователь {user_id} разбанен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при разбане пользователя {user_id}: {e}")
            return False

    async def is_user_banned(self, user_id: int) -> tuple:
        """Проверка бана пользователя с возвратом статуса и причины"""
        try:
            # Проверяем наличие колонки is_banned в таблице users
            table_info = sqlite_db.execute_query("PRAGMA table_info(users)")
            has_ban_column = any(row['name'] == 'is_banned' for row in table_info)
            
            if not has_ban_column:
                return False, None
            
            # Проверяем статус бана
            result = sqlite_db.execute_query(
                """
                SELECT is_banned, ban_reason, ban_date 
                FROM users 
                WHERE user_id = ?
                """,
                (user_id,)
            )
            
            if not result or not result[0]['is_banned']:
                return False, None
                
            return True, result[0]['ban_reason']
        except Exception as e:
            logger.error(f"Ошибка при проверке бана пользователя {user_id}: {e}")
            return False, None

    async def save_schedule_photo(self, photo_id: str, file_id: str) -> bool:
        """Сохранение информации о графике учебного процесса"""
        try:
            # Деактивируем все предыдущие фото
            query = "UPDATE schedule_photos SET is_active = 0"
            self.db.execute_query(query)
            
            # Сохраняем новое фото
            query = """
            INSERT INTO schedule_photos (photo_id, file_id, uploaded_at, is_active)
            VALUES (?, ?, CURRENT_TIMESTAMP, 1)
            """
            self.db.execute_query(query, (photo_id, file_id))
            
            # Проверяем, что фото действительно сохранилось
            verify_query = """
            SELECT photo_id, file_id FROM schedule_photos 
            WHERE photo_id = ? ORDER BY uploaded_at DESC LIMIT 1
            """
            result = self.db.execute_query(verify_query, (photo_id,))
            
            if result and len(result) > 0:
                logger.info(f"График учебного процесса успешно сохранен: {photo_id}")
                return True
            else:
                logger.error(f"График не был сохранен в базе данных")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении графика: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            return False

    async def get_active_schedule_photo(self) -> Optional[Dict[str, str]]:
        """Получение активного графика учебного процесса"""
        try:
            query = """
            SELECT photo_id, file_id 
            FROM schedule_photos 
            WHERE is_active = 1 
            ORDER BY uploaded_at DESC 
            LIMIT 1
            """
            result = self.db.execute_query(query)
            
            if not result or len(result) == 0:
                logger.warning("Активный график учебного процесса не найден в базе данных")
                return None
                
            # Получаем первую запись из результата
            photo_data = result[0]
            
            logger.info(f"Найден активный график: {photo_data}")
            
            # Создаем словарь с результатами
            return {
                "photo_id": photo_data["photo_id"],
                "file_id": photo_data["file_id"]
            }
        except Exception as e:
            logger.error(f"Ошибка при получении активного графика: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            return None

# Создаем экземпляр адаптера
db_adapter = DatabaseAdapter() 