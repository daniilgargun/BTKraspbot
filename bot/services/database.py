from typing import Dict, Any, Optional, List
from bot.services.firebase import SERVER_TIMESTAMP
from bot.services.database_config import get_database
from bot.config import logger
from datetime import datetime
import time
import asyncio

db = get_database()

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        logger.info("Начало инициализации базы данных")
        self.db = db
        self.users_collection = self.db.collection('users')
        self.schedule_collection = self.db.collection('schedule')
        self.cache_collection = self.db.collection('cache')
        
        logger.info("База данных успешно инициализирована")
        self._initialized = True
        self._cache = {}
        self._cache_timeout = 300  # 5 минут

    async def create_user(self, user_id: int) -> bool:
        """Создание нового пользователя с дефолтными значениями"""
        try:
            user_data = {
                "user_id": str(user_id),
                "role": None,
                "selected_teacher": None, 
                "selected_group": None,
                "notifications": False,
                "created_at": SERVER_TIMESTAMP
            }
            
            # Оборачиваем синхронный вызов в асинхронный контекст
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).set(user_data))
            
            logger.info(f"Пользователь {user_id} успешно создан")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).get())
            if doc.exists:
                logger.info(f"Получены данные пользователя {user_id}")
                return doc.to_dict()
            logger.warning(f"Пользователь {user_id} не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
            return None

    async def update_user_role(self, user_id: int, role: str) -> bool:
        """Обновление роли пользователя"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).update({"role": role}))
            logger.info(f"Роль пользователя {user_id} обновлена на {role}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении роли пользователя {user_id}: {e}")
            return False

    async def update_selected_teacher(self, user_id: int, teacher: str) -> bool:
        """Обновление выбранного преподавателя"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).update({"selected_teacher": teacher}))
            logger.info(f"Выбранный преподаватель пользователя {user_id} обновлен на {teacher}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении преподавателя для пользователя {user_id}: {e}")
            return False

    async def update_selected_group(self, user_id: int, group: str) -> bool:
        """Обновление выбранной группы"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).update({"selected_group": group}))
            logger.info(f"Выбранная группа пользователя {user_id} обновлена на {group}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении группы для пользователя {user_id}: {e}")
            return False

    async def toggle_notifications(self, user_id: int, enabled: bool) -> bool:
        """Включение/выключение уведомлений"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).update({"notifications": enabled}))
            logger.info(f"Уведомления для пользователя {user_id} {'включены' if enabled else 'выключены'}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении настроек уведомлений для пользователя {user_id}: {e}")
            return False

    async def user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.users_collection.document(str(user_id)).get())
            exists = doc.exists
            
            # Если пользователь не существует, создаем его
            if not exists:
                logger.info(f"Пользователь {user_id} не найден, создаем нового пользователя")
                await self.create_user(user_id)
                exists = True
                
            logger.info(f"Проверка существования пользователя {user_id}: {'существует' if exists else 'не существует'}")
            return exists
        except Exception as e:
            logger.error(f"Ошибка при проверке существования пользователя {user_id}: {e}")
            return False

    async def update_schedule(self, schedule_data: Dict[str, Any]) -> bool:
        """Обновление расписания"""
        try:
            # Сохраняем в Firebase
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.schedule_collection.document('current').set(schedule_data))
            logger.info("Расписание успешно обновлено в Firebase")
            
            # Сохраняем в SQLite
            from bot.database import db as sqlite_db
            await sqlite_db.save_schedule(schedule_data)
            logger.info("Расписание успешно обновлено в SQLite")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении расписания: {e}")
            return False

    async def get_schedule(self) -> Optional[Dict[str, Any]]:
        """Получение текущего расписания"""
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.schedule_collection.document('current').get())
            if doc.exists:
                logger.info("Получено текущее расписание")
                return doc.to_dict()
            logger.warning("Расписание не найдено")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении расписания: {e}")
            return None

    async def get_groups(self) -> list:
        """Получение списка всех групп"""
        try:
            logger.info("Получение списка всех групп")
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.schedule_collection.document('groups').get())
            if doc.exists:
                groups = doc.to_dict().get('groups', [])
                logger.info(f"Получено {len(groups)} групп")
                return groups
            logger.warning("Документ с группами не найден")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении списка групп: {e}")
            return []

    async def get_teachers(self) -> list:
        """Получение списка всех преподавателей"""
        try:
            logger.info("Получение списка всех преподавателей")
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.schedule_collection.document('teachers').get())
            if doc.exists:
                teachers = doc.to_dict().get('teachers', [])
                logger.info(f"Получено {len(teachers)} преподавателей")
                return teachers
            logger.warning("Документ с преподавателями не найден")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении списка преподавателей: {e}")
            return []

    async def cache_groups_and_teachers(self, groups: list, teachers: list) -> bool:
        """Кэширование списков групп и преподавателей"""
        try:
            logger.info("Начало кэширования групп и преподавателей")
            batch = self.db.batch()
            
            # Сохраняем группы
            groups_ref = self.schedule_collection.document('groups')
            batch.set(groups_ref, {'groups': groups, 'updated_at': SERVER_TIMESTAMP})
            
            # Сохраняем преподавателей
            teachers_ref = self.schedule_collection.document('teachers')
            batch.set(teachers_ref, {'teachers': teachers, 'updated_at': SERVER_TIMESTAMP})
            
            # Выполняем транзакцию
            batch.commit()
            
            logger.info(f"Успешно кэшировано {len(groups)} групп и {len(teachers)} преподавателей")
            return True
        except Exception as e:
            logger.error(f"Ошибка при кэшировании групп и преподавателей: {e}")
            return False
    async def get_cached_groups(self) -> list:
        """Получение кэшированного списка групп"""
        try:
            logger.info("Получение кэшированного списка групп")
            doc = self.schedule_collection.document('groups').get()
            if doc.exists:
                groups = doc.to_dict().get('groups', [])
                return groups
            logger.warning("Кэшированные группы не найдены")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении кэшированных групп: {e}")
            return []
    async def get_cached_teachers(self) -> list:
        """Получение кэшированного списка преподавателей"""
        try:
            logger.info("Получение кэшированного списка преподавателей")
            doc = self.schedule_collection.document('teachers').get()
            if doc.exists:
                teachers = doc.to_dict().get('teachers', [])
                if not teachers:
                    logger.warning("Список преподавателей пуст")
                return teachers
            logger.warning("Документ с преподавателями не найден")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении кэшированных преподавателей: {e}")
            return []
        
    # async def test_cache_groups_and_teachers(self):
    #     """Тест кэширования и получения групп и преподавателей"""
    #     try:
    #         # Получаем данные из парсера
    #         from bot.services.parser import ScheduleParser
    #         parser = ScheduleParser()
    #         schedule_data, groups_list, teachers_list, error = await parser.parse_schedule()

    #         if error:
    #             logger.error(f"Ошибка получения данных из парсера: {error}")
    #             return False

    #         logger.info(f"Найдено {len(groups_list)} групп и {len(teachers_list)} преподавателей")

    #         # Тест кэширования
    #         logger.info("Начало тестирования кэширования")
    #         cache_result = await self.cache_groups_and_teachers(groups_list, teachers_list)
    #         assert cache_result == True, "Ошибка кэширования"

    #         # Тест получения групп
    #         cached_groups = await self.get_cached_groups()
    #         assert len(cached_groups) == len(groups_list), "Несоответствие количества групп"
    #         assert all(group in cached_groups for group in groups_list), "Несоответствие данных групп"

    #         # Тест получения преподавателей
    #         cached_teachers = await self.get_cached_teachers()
    #         assert len(cached_teachers) == len(teachers_list), "Несоответствие количества преподавателей"
    #         assert all(teacher in cached_teachers for teacher in teachers_list), "Несоответствие данных преподавателей"

    #         logger.info("Тестирование успешно завершено")
    #         return True
        
    #     except AssertionError as ae:
    #         logger.error(f"Ошибка при тестировании: {ae}")
    #         return False
    #     except Exception as e:
    #         logger.error(f"Непредвиденная ошибка при тестировании: {e}")
    #         import traceback
    #         logger.error(f"Traceback: {traceback.format_exc()}")
    #         return False

    async def save_schedule_image(self, collection_name: str, image_data: dict) -> bool:
        """Сохранение данных изображения расписания"""
        try:
            # Создаем новый документ в соответствующей коллекции
            doc_ref = self.db.collection('schedules').document(collection_name)
            doc_ref.set(image_data)
            logger.info(f"Сохранено изображение для {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения расписания: {e}")
            return False

    async def get_schedule_image(self, collection_name: str) -> Optional[Dict]:
        """Получение данных изображения расписания"""
        try:
            doc_ref = self.db.collection('schedules').document(collection_name)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении изображения расписания: {e}")
            return None

    async def get_all_users(self) -> list:
        """Получение списка всех пользователей"""
        try:
            users = []
            docs = self.users_collection.stream()
            for doc in docs:
                user_data = doc.to_dict()
                users.append(user_data)
            logger.info(f"Получено {len(users)} пользователей из базы данных")
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []

    async def get_last_update_time(self) -> str:
        """Получение времени последнего обновления кэша"""
        try:
            cache_info = self.cache_collection.document('info').get()
            if cache_info.exists:
                last_update = cache_info.get('last_update')
                if last_update:
                    # Преобразуем временную метку Firestore в datetime
                    return last_update.strftime("%d.%m.%Y %H:%M:%S")
            return "Нет данных"
        except Exception as e:
            logger.error(f"Ошибка при получении времени обновления: {e}")
            return "Нет данных"

    async def update_cache_time(self):
        """Обновление времени последнего обновления кэша"""
        try:
            self.cache_collection.document('info').set({
                'last_update': SERVER_TIMESTAMP
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени кэша: {e}")
            return False

    async def get_last_checked_dates(self) -> List[str]:
        """Получение списка последних проверенных дат"""
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.cache_collection.document('last_checked_dates').get())
            if doc.exists:
                return doc.to_dict().get('dates', [])
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении последних проверенных дат: {e}")
            return []

    def get_admin_id(self) -> int:
        """Получение ID администратора из конфига"""
        try:
            from bot.config import config
            return config.ADMIN_ID
        except Exception as e:
            logger.error(f"Ошибка при получении ID администратора: {e}")
            return None

    async def update_last_checked_dates(self, dates: List[str]) -> bool:
        """Обновление списка последних проверенных дат"""
        try:
            self.cache_collection.document('last_checked_dates').set({
                'dates': dates,
                'updated_at': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении последних проверенных дат: {e}")
            return False

    async def get_users_with_notifications(self) -> List[Dict]:
        """Получение списка пользователей с включенными уведомлениями"""
        try:
            users = []
            docs = self.users_collection.where('notifications', '==', True).stream()
            for doc in docs:
                user_data = doc.to_dict()
                user_data['user_id'] = int(doc.id)
                users.append(user_data)
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей с уведомлениями: {e}")
            return []

    async def get_banned_users(self) -> list:
        """Получение списка забаненных пользователей"""
        try:
            banned_users = []
            docs = self.users_collection.where('is_banned', '==', True).stream()
            for doc in docs:
                user_data = doc.to_dict()
                user_data['user_id'] = int(doc.id)
                banned_users.append(user_data)
            return banned_users
        except Exception as e:
            logger.error(f"Ошибка при получении списка забаненных пользователей: {e}")
            return []

    async def unban_user(self, user_id: int) -> bool:
        """Разбан пользователя"""
        try:
            self.users_collection.document(str(user_id)).update({
                'is_banned': False
            })
            logger.info(f"Пользователь {user_id} разбанен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при разбане пользователя {user_id}: {e}")
            return False

# if __name__ == "__main__":
#     import asyncio
#     db = Database()
#     asyncio.run(db.test_cache_groups_and_teachers())
