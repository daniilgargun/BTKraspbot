import asyncio
import firebase_admin
from firebase_admin import credentials
import logging
import os

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Firebase
def initialize_firebase():
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cred_path = os.path.join(project_root, 'tests', 'botbtk-8ac0a-firebase-adminsdk-n5pjf-54392c0500.json')
        if not os.path.exists(cred_path):
            raise ValueError(f"Файл с учетными данными не найден: {cred_path}")
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        
        from bot.services.parser import ScheduleParser
        from bot.services.database import Database
        
        return ScheduleParser(), Database()
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации Firebase: {e}")
        raise

async def update_database():
    try:
        logger.info("Начало обновления базы данных")
        
        # Инициализируем парсер и базу данных
        parser, db = initialize_firebase()
        
        logger.info("Запуск парсинга расписания...")
        schedule_data, groups_list, teachers_list, error = await parser.parse_schedule()
        
        if error:
            logger.error(f"Ошибка при парсинге: {error}")
            return
            
        if not schedule_data or not groups_list or not teachers_list:
            logger.error("Получены пустые данные")
            return
            
        # Обновляем данные в базе
        logger.info("Обновление расписания в базе данных...")
        await db.update_schedule(schedule_data)
        
        logger.info("Кэширование списков групп и преподавателей...")
        await db.cache_groups_and_teachers(groups_list, teachers_list)
        
        # Обновляем время последнего обновления
        await db.update_cache_time()
        
        logger.info(f"Обновление завершено успешно!")
        logger.info(f"Загружено групп: {len(groups_list)}")
        logger.info(f"Загружено преподавателей: {len(teachers_list)}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    try:
        # Запускаем обновление
        asyncio.run(update_database())
    except KeyboardInterrupt:
        logger.info("Обновление остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}") 