#!/usr/bin/env python3
"""
Скрипт для оптимизации и обслуживания базы данных SQLite.
Запускается периодически для очистки временных файлов, оптимизации индексов и вакуумирования БД.
"""

import os
import sqlite3
import logging
import time
import sys
import shutil
from pathlib import Path
import importlib.util

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('optimize_db.log')
    ]
)
logger = logging.getLogger(__name__)

def import_sqlite_db():
    """Попытка импортировать класс SQLiteDatabase из бота"""
    try:
        # Путь к модулю sqlite_db.py
        module_path = os.path.join("bot", "database", "sqlite_db2.py")
        
        # Если файл существует, импортируем его
        if os.path.exists(module_path):
            spec = importlib.util.spec_from_file_location("sqlite_db2", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Возвращаем экземпляр SQLiteDatabase
            if hasattr(module, 'db') and hasattr(module, 'SQLiteDatabase'):
                logger.info("Модуль sqlite_db2.py успешно импортирован")
                return module.db
                
    except Exception as e:
        logger.error(f"Ошибка при импорте модуля sqlite_db2: {e}")
    
    return None

def get_db_path():
    """Получение пути к файлу базы данных"""
    # Пытаемся получить экземпляр SQLiteDatabase из бота
    db_instance = import_sqlite_db()
    if db_instance:
        logger.info(f"Использую путь к БД из экземпляра SQLiteDatabase: {db_instance.db_path}")
        return db_instance.db_path
    
    # Если не удалось, проверяем стандартные пути
    db_paths = [
        os.path.join("bot", "database", "bot_new.db"),
        os.path.join("bot", "database", "bot.db"),
        "bot.db"
    ]
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            logger.info(f"База данных найдена по пути: {db_path}")
            return db_path
    
    logger.error(f"База данных не найдена ни по одному из путей: {db_paths}")
    return None

def stop_running_bot():
    """Проверка и остановка запущенного бота для безопасной оптимизации"""
    try:
        # Проверяем наличие процесса python.exe
        import subprocess
        result = subprocess.run(["tasklist", "/fi", "imagename eq python.exe", "/fo", "csv"], 
                               capture_output=True, text=True)
        
        if "python.exe" in result.stdout:
            logger.warning("Обнаружен запущенный процесс Python. Рекомендуется остановить бота перед оптимизацией.")
            user_input = input("Остановить запущенный бот перед оптимизацией? (y/n): ")
            
            if user_input.lower() == 'y':
                subprocess.run(["taskkill", "/f", "/im", "python.exe"])
                logger.info("Процесс Python остановлен.")
                time.sleep(2)  # Ждем, пока процесс полностью завершится
                return True
            else:
                logger.warning("Оптимизация продолжается без остановки бота. Возможны ошибки блокировки БД.")
        else:
            logger.info("Запущенные процессы Python не обнаружены.")
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке/остановке процессов: {e}")
        return False

def create_backup(db_path):
    """Создание резервной копии базы данных"""
    try:
        # Создаем директорию для резервных копий, если её нет
        backup_dir = os.path.join("bot", "database", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Имя файла резервной копии с датой и временем
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"bot_{timestamp}.db")
        
        # Копируем файл базы данных
        shutil.copy2(db_path, backup_file)
        logger.info(f"Резервная копия создана: {backup_file}")
        
        # Очистка старых резервных копий (оставляем только 5 последних)
        backup_files = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.db')])
        if len(backup_files) > 5:
            for old_file in backup_files[:-5]:
                os.remove(old_file)
                logger.info(f"Удалена старая резервная копия: {old_file}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии: {e}")
        return False

def optimize_database(db_path):
    """Оптимизация базы данных через прямое соединение с SQLite"""
    try:
        # Подключаемся к БД
        conn = sqlite3.connect(db_path, timeout=60.0)
        
        # Анализ и оптимизация индексов
        logger.info("Запуск анализа и оптимизации индексов...")
        conn.execute("ANALYZE")
        
        # Проверка целостности базы данных
        logger.info("Проверка целостности базы данных...")
        integrity_check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity_check == "ok":
            logger.info("Проверка целостности базы данных: OK")
        else:
            logger.warning(f"Проверка целостности базы данных: {integrity_check}")
        
        # Вакуумирование базы данных для оптимизации размера и производительности
        logger.info("Запуск VACUUM для оптимизации размера и производительности...")
        conn.execute("VACUUM")
        
        # Добавляем заново оптимальные настройки
        conn.execute("PRAGMA journal_mode=DELETE")  # Отключаем WAL для избежания блокировок
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA busy_timeout=30000")
        
        # Фиксируем изменения и закрываем соединение
        conn.commit()
        conn.close()
        
        logger.info("Оптимизация базы данных успешно завершена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при оптимизации базы данных: {e}")
        return False

def main():
    """Основная функция оптимизации"""
    logger.info("Запуск процесса оптимизации базы данных")
    
    # Проверяем и останавливаем бота при необходимости
    if not stop_running_bot():
        logger.warning("Не удалось корректно проверить запущенные процессы. Продолжаем оптимизацию.")
    
    # Получаем путь к базе данных
    db_path = get_db_path()
    if not db_path:
        return False
    
    # Создаем резервную копию перед оптимизацией
    if not create_backup(db_path):
        logger.warning("Не удалось создать резервную копию, но процесс оптимизации будет продолжен")
    
    # Проверяем, не используется ли база данных в данный момент
    try:
        # Пробуем подключиться с коротким таймаутом
        conn = sqlite3.connect(db_path, timeout=1.0)
        conn.close()
    except sqlite3.OperationalError:
        logger.error("База данных занята и используется другим процессом. Попробуйте еще раз после остановки бота.")
        return False
    
    # Оптимизируем базу данных
    if optimize_database(db_path):
        logger.info("Процесс оптимизации базы данных успешно завершен")
        return True
    else:
        logger.error("Процесс оптимизации базы данных завершился с ошибками")
        return False

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1) 