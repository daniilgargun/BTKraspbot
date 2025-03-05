import os
import sys
import subprocess
import winreg
import urllib.request
import json
from pathlib import Path
import logging
import shutil

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('setup.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Проверка версии Python"""
    required_version = (3, 12)
    current_version = sys.version_info[:2]
    
    logger.info(f"Текущая версия Python: {current_version[0]}.{current_version[1]}")
    
    if current_version < required_version:
        logger.error(f"❌ Требуется Python версии {required_version[0]}.{required_version[1]} или выше")
        logger.info("📥 Скачайте Python с https://www.python.org/downloads/")
        return False
    return True

def check_chrome_installed():
    """Проверка установки Chrome"""
    try:
        # Проверяем наличие Chrome в реестре Windows
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                          r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
            chrome_path = winreg.QueryValue(key, None)
            logger.info(f"✅ Google Chrome найден: {chrome_path}")
            return True
    except WindowsError:
        logger.error("❌ Google Chrome не установлен")
        logger.info("📥 Скачайте Chrome с https://www.google.com/chrome/")
        return False

def check_and_create_venv():
    """Проверка и создание виртуального окружения"""
    if not os.path.exists('venv'):
        logger.info("🔄 Создание виртуального окружения...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            logger.info("✅ Виртуальное окружение создано")
        except subprocess.CalledProcessError:
            logger.error("❌ Ошибка при создании виртуального окружения")
            return False
    else:
        logger.info("✅ Виртуальное окружение уже существует")
    return True

def install_requirements():
    """Установка зависимостей"""
    venv_python = os.path.join('venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_python):
        logger.error("❌ Виртуальное окружение не найдено")
        return False
    
    logger.info("🔄 Установка зависимостей...")
    try:
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        logger.info("✅ Зависимости установлены")
        return True
    except subprocess.CalledProcessError:
        logger.error("❌ Ошибка при установке зависимостей")
        return False

def copy_config_files():
    """Копирование конфигурационных файлов из директории tests"""
    try:
        # Копируем .env файл
        if os.path.exists('tests/.env') and not os.path.exists('.env'):
            shutil.copy2('tests/.env', '.env')
            logger.info("✅ Файл .env скопирован из директории tests")
        
        # Копируем файл Firebase
        firebase_file = 'botbtk-8ac0a-firebase-adminsdk-n5pjf-54392c0500.json'
        if os.path.exists(f'tests/{firebase_file}') and not os.path.exists(firebase_file):
            shutil.copy2(f'tests/{firebase_file}', firebase_file)
            logger.info("✅ Файл Firebase скопирован из директории tests")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при копировании конфигурационных файлов: {str(e)}")
        return False

def check_env_file():
    """Проверка наличия .env файла"""
    if not os.path.exists('.env'):
        logger.warning("⚠️ Файл .env не найден")
        if os.path.exists('tests/.env'):
            return copy_config_files()
        else:
            create_env = input("Создать файл .env? (y/n): ")
            if create_env.lower() == 'y':
                bot_token = input("Введите BOT_TOKEN: ")
                with open('.env', 'w') as f:
                    f.write(f'BOT_TOKEN={bot_token}\n')
                logger.info("✅ Файл .env создан")
                return True
            return False
    return True

def main():
    """Основная функция настройки"""
    logger.info("🔄 Начало проверки и настройки окружения")
    
    # Проверяем все необходимые компоненты
    checks = [
        ("Python 3.12", check_python_version),
        ("Google Chrome", check_chrome_installed),
        ("Виртуальное окружение", check_and_create_venv),
        ("Зависимости", install_requirements),
        ("Конфигурационные файлы", copy_config_files),
        ("Файл .env", check_env_file)
    ]
    
    all_passed = True
    for name, check in checks:
        logger.info(f"\n🔍 Проверка: {name}")
        if not check():
            all_passed = False
            logger.error(f"❌ Проверка {name} не пройдена")
        else:
            logger.info(f"✅ Проверка {name} успешно пройдена")
    
    if all_passed:
        logger.info("\n✅ Все проверки пройдены успешно! Бот готов к запуску")
        logger.info("📝 Для запуска бота выполните:")
        logger.info("1. venv\\Scripts\\activate")
        logger.info("2. python -m bot.main")
    else:
        logger.error("\n❌ Не все проверки пройдены. Исправьте ошибки и попробуйте снова")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Процесс настройки прерван пользователем")
    except Exception as e:
        logger.error(f"\n❌ Произошла непредвиденная ошибка: {str(e)}") 