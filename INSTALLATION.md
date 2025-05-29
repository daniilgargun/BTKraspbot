# 🛠 Руководство по Установке

## 📋 Системные Требования

### Минимальные Требования
- **Операционная система:** Windows 10/11, Ubuntu 18.04+, CentOS 7+, macOS 10.14+
- **Python:** 3.8 или выше
- **RAM:** 512 MB свободной памяти
- **Дисковое пространство:** 100 MB
- **Интернет:** Стабильное подключение для работы с Telegram API

### Рекомендуемые Требования
- **Python:** 3.11+
- **RAM:** 1 GB
- **Дисковое пространство:** 500 MB
- **Процессор:** 2 ядра 1.5 GHz+

## 🔧 Предварительная Подготовка

### 1. Установка Python

#### Windows
1. Скачайте Python с [официального сайта](https://www.python.org/downloads/)
2. Запустите установщик
3. ✅ Обязательно отметьте "Add Python to PATH"
4. Выберите "Install Now"

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

#### CentOS/RHEL
```bash
sudo yum install python3 python3-pip
# или для CentOS 8+
sudo dnf install python3 python3-pip
```

#### macOS
```bash
# Используя Homebrew
brew install python3

# Или скачайте с официального сайта
```

### 2. Проверка Установки Python
```bash
python --version
# или
python3 --version

# Должно показать версию 3.8 или выше
```

### 3. Создание Telegram Бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен (например: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Получите ваш Telegram ID:
   - Найдите [@userinfobot](https://t.me/userinfobot)
   - Отправьте команду `/start`
   - Сохраните ваш ID (например: `123456789`)

## 📥 Установка Проекта

### Способ 1: Автоматическая Установка (Рекомендуется)

1. **Скачайте проект** (получите от автора)
2. **Распакуйте архив** в желаемую папку
3. **Откройте командную строку** в папке проекта
4. **Запустите автоматическую установку:**

```bash
python setup.py
```

Скрипт автоматически:
- ✅ Проверит версию Python
- ✅ Создаст виртуальное окружение
- ✅ Установит все зависимости
- ✅ Создаст файл конфигурации
- ✅ Инициализирует базу данных

### Способ 2: Ручная Установка

#### Шаг 1: Клонирование/Скачивание
```bash
# Если у вас есть доступ к репозиторию
git clone <repository-url>
cd TelegramBot

# Или распакуйте скачанный архив
```

#### Шаг 2: Создание Виртуального Окружения
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

#### Шаг 3: Установка Зависимостей
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Шаг 4: Создание Файла Конфигурации
Создайте файл `.env` в корневой папке проекта:

```env
# Токен вашего Telegram бота
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Ваш Telegram ID (основной администратор)
ADMIN_ID=123456789

# Дополнительные администраторы (через запятую)
ADMIN_IDS=123456789,987654321,555666777

# Настройки базы данных (опционально)
DATABASE_URL=sqlite:///bot/database/bot.db

# Настройки логирования (опционально)
LOG_LEVEL=INFO
```

#### Шаг 5: Инициализация Базы Данных
```bash
python -c "from bot.database import db; db.init_db()"
```

## ⚙️ Настройка

### Основные Настройки

#### Файл .env
```env
# ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ
BOT_TOKEN=ваш_токен_бота_здесь
ADMIN_ID=ваш_telegram_id

# ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ
ADMIN_IDS=список_id_админов_через_запятую
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///bot/database/bot.db
```

#### Настройка Администраторов
```env
# Один администратор
ADMIN_ID=123456789

# Несколько администраторов
ADMIN_IDS=123456789,987654321,555666777
```

### Дополнительные Настройки

#### Настройки Парсера
```env
PARSER_TIMEOUT=30
PARSER_RETRY_COUNT=3
PARSER_DELAY=1
```

#### Настройки Уведомлений
```env
NOTIFICATION_BATCH_SIZE=50
NOTIFICATION_DELAY=1
MAX_NOTIFICATIONS_PER_MINUTE=20
```

#### Настройки Логирования
```env
LOG_LEVEL=INFO
LOG_FILE=bot.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5
```

## 🚀 Запуск

### Windows

#### Способ 1: Батник (Рекомендуется)
```bash
start_bot.bat
```

#### Способ 2: Командная строка
```cmd
# Активация виртуального окружения
venv\Scripts\activate

# Запуск бота
python bot\main.py
```

#### Способ 3: Автозапуск
Для автоматического запуска при включении компьютера:
```cmd
# Запуск в фоновом режиме
autostart.vbs
```

### Linux/macOS

#### Способ 1: Прямой запуск
```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск бота
python bot/main.py
```

#### Способ 2: Создание скрипта запуска
```bash
#!/bin/bash
cd /path/to/TelegramBot
source venv/bin/activate
python bot/main.py
```

#### Способ 3: Systemd Service
Создайте файл `/etc/systemd/system/telegram-bot.service`:
```ini
[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/TelegramBot
ExecStart=/path/to/TelegramBot/venv/bin/python bot/main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/path/to/TelegramBot

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## 🔍 Проверка Работы

### 1. Проверка Запуска
После запуска вы должны увидеть в логах:
```
INFO - 🚀 Бот запущен и готов к работе
INFO - ✅ Планировщик обновления расписания запущен успешно
```

### 2. Тестирование Бота
1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Бот должен ответить приветственным сообщением

### 3. Проверка Административных Функций
1. Отправьте команду `/admin` (только для администраторов)
2. Должна открыться административная панель

## 🚨 Устранение Проблем

### Частые Ошибки

#### 1. "BOT_TOKEN environment variable is not set!"
**Решение:**
- Проверьте наличие файла `.env`
- Убедитесь, что токен указан правильно
- Перезапустите бота

#### 2. "Unauthorized" или "Invalid token"
**Решение:**
- Проверьте правильность токена
- Убедитесь, что бот не заблокирован
- Создайте нового бота через @BotFather

#### 3. Ошибки установки зависимостей
**Решение:**
```bash
# Обновите pip
pip install --upgrade pip

# Установите зависимости по одной
pip install aiogram==3.16.0
pip install aiohttp==3.9.5
# и т.д.
```

#### 4. Проблемы с базой данных
**Решение:**
```bash
# Удалите старую базу данных
rm bot/database/bot.db

# Переинициализируйте
python -c "from bot.database import db; db.init_db()"
```

#### 5. Проблемы с правами доступа (Linux)
**Решение:**
```bash
# Дайте права на выполнение
chmod +x start_bot.sh

# Проверьте владельца файлов
chown -R $USER:$USER /path/to/TelegramBot
```

### Диагностика

#### Проверка Логов
```bash
# Просмотр логов в реальном времени
tail -f bot.log

# Просмотр последних записей
tail -n 50 bot.log

# Поиск ошибок
grep ERROR bot.log
```

#### Проверка Процессов
```bash
# Linux/macOS
ps aux | grep python

# Windows
tasklist | findstr python
```

#### Проверка Портов и Соединений
```bash
# Проверка интернет-соединения
ping api.telegram.org

# Проверка DNS
nslookup api.telegram.org
```

## 🔄 Обновление

### Процедура Обновления
1. **Остановите бота**
2. **Создайте резервную копию:**
   ```bash
   cp -r TelegramBot TelegramBot_backup
   ```
3. **Скачайте новую версию**
4. **Замените файлы** (сохраните `.env` и базу данных)
5. **Обновите зависимости:**
   ```bash
   pip install -r requirements.txt --upgrade
   ```
6. **Запустите бота**

### Автоматическое Обновление
```bash
# Создайте скрипт update.sh
#!/bin/bash
echo "Остановка бота..."
pkill -f "python bot/main.py"

echo "Создание резервной копии..."
cp -r . ../backup_$(date +%Y%m%d_%H%M%S)

echo "Обновление зависимостей..."
source venv/bin/activate
pip install -r requirements.txt --upgrade

echo "Запуск бота..."
python bot/main.py &
```

## 📞 Получение Поддержки

Если у вас возникли проблемы с установкой или настройкой:

### Контакты Автора
- **Telegram:** [@Daniilgargun](https://t.me/Daniilgargun)
- **Email:** daniilgorgun38@gmail.com
- **Телефон:** +375299545338

### Информация для Поддержки
При обращении за помощью укажите:
1. Операционную систему и версию
2. Версию Python
3. Текст ошибки (если есть)
4. Логи бота
5. Шаги, которые привели к проблеме

### Платная Поддержка
- Удаленная установка и настройка
- Персональное обучение
- Кастомизация под ваши нужды
- Техническая поддержка 24/7

---

**© 2024 Данил Гаргун. Все права защищены.** 