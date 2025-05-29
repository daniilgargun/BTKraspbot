# 📚 Техническая Документация

## 🏗 Архитектура Системы

### Общая Архитектура
Telegram бот построен на основе модульной архитектуры с четким разделением ответственности между компонентами.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram API  │◄──►│   Bot Handler   │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Services      │
                    │  - Parser       │
                    │  - Scheduler    │
                    │  - Notifications│
                    └─────────────────┘
```

### Основные Компоненты

#### 1. Bot Handler (bot/main.py)
- **Назначение:** Основная точка входа приложения
- **Ответственность:** 
  - Инициализация бота
  - Управление жизненным циклом
  - Обработка сигналов системы
  - Координация между компонентами

#### 2. Handlers (bot/handlers/)
- **admin.py** - Административные команды
- **user.py** - Пользовательские команды  
- **start.py** - Команда запуска
- **common.py** - Общие обработчики
- **holiday_greetings.py** - Праздничные поздравления

#### 3. Services (bot/services/)
- **parser.py** - Парсинг расписания с веб-сайтов
- **notifications.py** - Система уведомлений
- **scheduler.py** - Планировщик задач
- **database.py** - Сервис работы с БД
- **monitoring.py** - Мониторинг системы

#### 4. Database (bot/database/)
- **sqlite_db2.py** - SQLite адаптер
- **db_adapter.py** - Универсальный адаптер БД
- **schema.sql** - Схема базы данных

## 🗄 База Данных

### Схема Базы Данных

```sql
-- Пользователи системы
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    role TEXT DEFAULT 'student',
    group_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Учебные группы
CREATE TABLE groups (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    course INTEGER,
    specialty TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Расписание занятий
CREATE TABLE schedule (
    id INTEGER PRIMARY KEY,
    group_name TEXT NOT NULL,
    date TEXT NOT NULL,
    time_start TEXT,
    time_end TEXT,
    subject TEXT,
    teacher TEXT,
    classroom TEXT,
    lesson_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- История уведомлений
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    message TEXT,
    type TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',
    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
);

-- Настройки системы
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Индексы для Оптимизации

```sql
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_schedule_group_date ON schedule(group_name, date);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_sent_at ON notifications(sent_at);
```

## 🔧 API Документация

### Основные Классы

#### BotApp (bot/main.py)
```python
class BotApp:
    """Основной класс приложения бота"""
    
    def __init__(self):
        """Инициализация компонентов бота"""
        
    async def setup(self):
        """Настройка обработчиков и команд"""
        
    async def start(self):
        """Запуск бота"""
        
    async def stop(self):
        """Остановка бота с корректным завершением"""
```

#### Config (bot/config.py)
```python
@dataclass
class Config:
    """Конфигурация бота"""
    BOT_TOKEN: str
    ADMIN_ID: int
    ADMIN_IDS: list
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
```

#### DatabaseAdapter (bot/database/db_adapter.py)
```python
class DatabaseAdapter:
    """Адаптер для работы с базой данных"""
    
    async def get_user(self, telegram_id: int) -> dict:
        """Получение пользователя по Telegram ID"""
        
    async def save_user(self, user_data: dict) -> bool:
        """Сохранение данных пользователя"""
        
    async def get_schedule(self, group: str, date: str) -> list:
        """Получение расписания для группы на дату"""
```

### Обработчики Команд

#### Пользовательские Команды
```python
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start - начало работы с ботом"""

@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Команда /schedule - просмотр расписания"""

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Команда /profile - профиль пользователя"""
```

#### Административные Команды
```python
@router.message(Command("admin"))
@admin_required
async def cmd_admin(message: Message):
    """Панель администратора"""

@router.message(Command("stats"))
@admin_required
async def cmd_stats(message: Message):
    """Статистика использования"""

@router.message(Command("broadcast"))
@admin_required
async def cmd_broadcast(message: Message):
    """Массовая рассылка"""
```

## 🔄 Система Уведомлений

### NotificationManager (bot/services/notifications.py)
```python
class NotificationManager:
    """Менеджер уведомлений"""
    
    async def send_notification(self, user_id: int, message: str, type: str):
        """Отправка уведомления пользователю"""
        
    async def broadcast_message(self, message: str, user_filter: dict = None):
        """Массовая рассылка сообщений"""
        
    async def schedule_notification(self, user_id: int, message: str, 
                                  send_time: datetime):
        """Планирование отправки уведомления"""
```

### Типы Уведомлений
- `schedule_change` - Изменения в расписании
- `holiday_greeting` - Праздничные поздравления
- `system_notification` - Системные уведомления
- `admin_broadcast` - Административные сообщения

## 📅 Планировщик Задач

### Scheduler (bot/services/scheduler.py)
```python
class Scheduler:
    """Планировщик автоматических задач"""
    
    async def start(self):
        """Запуск планировщика"""
        
    async def add_job(self, func, trigger, **kwargs):
        """Добавление задачи в планировщик"""
        
    async def remove_job(self, job_id: str):
        """Удаление задачи из планировщика"""
```

### Автоматические Задачи
- **Обновление расписания** - каждые 30 минут
- **Отправка уведомлений** - по расписанию
- **Резервное копирование** - ежедневно в 02:00
- **Очистка логов** - еженедельно
- **Мониторинг системы** - каждые 5 минут

## 🔍 Парсинг Данных

### Parser (bot/services/parser.py)
```python
class ScheduleParser:
    """Парсер расписания с веб-сайтов"""
    
    async def parse_schedule(self, group: str, date: str) -> list:
        """Парсинг расписания для группы"""
        
    async def get_groups_list(self) -> list:
        """Получение списка групп"""
        
    async def check_schedule_updates(self) -> dict:
        """Проверка обновлений расписания"""
```

### Технологии Парсинга
- **Selenium WebDriver** - для динамических сайтов
- **BeautifulSoup4** - для парсинга HTML
- **Requests** - для HTTP запросов
- **lxml** - для быстрого парсинга XML/HTML

## 🛡 Безопасность

### Аутентификация и Авторизация
```python
def admin_required(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(message: Message, *args, **kwargs):
        if not config.is_admin(message.from_user.id):
            await message.answer("❌ Недостаточно прав доступа")
            return
        return await func(message, *args, **kwargs)
    return wrapper
```

### Защита Данных
- Шифрование конфиденциальных данных
- Валидация входных данных
- Защита от SQL-инъекций
- Ограничение частоты запросов
- Логирование всех действий

## 📊 Мониторинг и Логирование

### Система Логирования
```python
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
```

### Метрики Мониторинга
- Количество активных пользователей
- Частота использования команд
- Время отклика системы
- Ошибки и исключения
- Использование ресурсов

## 🔧 Конфигурация

### Переменные Окружения (.env)
```env
# Основные настройки
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_id
ADMIN_IDS=comma_separated_admin_ids

# База данных
DATABASE_URL=sqlite:///bot/database/bot.db

# Логирование
LOG_LEVEL=INFO
LOG_FILE=bot.log

# Парсер
PARSER_TIMEOUT=30
PARSER_RETRY_COUNT=3

# Уведомления
NOTIFICATION_BATCH_SIZE=50
NOTIFICATION_DELAY=1
```

### Настройки Конфигурации (bot/config.py)
```python
# Временные настройки
WEEKDAYS = {
    'monday': 'понедельник',
    'tuesday': 'вторник',
    # ...
}

MONTHS = {
    'янв': 1, 'фев': 2, 'мар': 3,
    # ...
}

# Форматирование даты
def format_date(date):
    """Форматирование даты с учетом русской локали"""
```

## 🚀 Развертывание

### Требования к Серверу
- **ОС:** Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- **Python:** 3.8+
- **RAM:** 1GB+
- **Диск:** 5GB+
- **Сеть:** Стабильное интернет-соединение

### Docker Развертывание
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "bot/main.py"]
```

### Systemd Service (Linux)
```ini
[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/telegram-bot
ExecStart=/opt/telegram-bot/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🧪 Тестирование

### Структура Тестов
```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_database.py
│   └── test_parser.py
├── integration/
│   ├── test_handlers.py
│   └── test_notifications.py
└── fixtures/
    ├── sample_data.json
    └── test_schedule.html
```

### Запуск Тестов
```bash
# Все тесты
python -m pytest tests/

# Только unit тесты
python -m pytest tests/unit/

# С покрытием кода
python -m pytest --cov=bot tests/
```

## 📈 Производительность

### Оптимизация Базы Данных
- Использование индексов для частых запросов
- Пагинация для больших результатов
- Кэширование часто запрашиваемых данных
- Регулярная очистка старых записей

### Оптимизация Памяти
- Использование генераторов для больших данных
- Освобождение ресурсов после использования
- Ограничение размера кэша
- Мониторинг утечек памяти

## 🔄 Обновления и Миграции

### Миграции Базы Данных
```python
class Migration:
    """Базовый класс для миграций"""
    
    def up(self):
        """Применение миграции"""
        pass
        
    def down(self):
        """Откат миграции"""
        pass
```

### Процедура Обновления
1. Создание резервной копии
2. Остановка бота
3. Обновление кода
4. Применение миграций
5. Запуск бота
6. Проверка работоспособности

---

**© 2024 Данил Гаргун. Все права защищены.** 