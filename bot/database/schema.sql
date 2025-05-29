-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    role TEXT DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы настроек пользователей
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    selected_group TEXT,
    selected_teacher TEXT,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Создание таблицы групп
CREATE TABLE IF NOT EXISTS groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT UNIQUE NOT NULL,
    course INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы преподавателей
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы расписания
CREATE TABLE IF NOT EXISTS schedule (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    group_name TEXT,
    teacher_name TEXT,
    lesson_number INTEGER,
    discipline TEXT NOT NULL,
    classroom TEXT,
    subgroup TEXT DEFAULT '0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_name) REFERENCES groups(group_name),
    FOREIGN KEY (teacher_name) REFERENCES teachers(full_name)
);

-- Создание таблицы обновлений расписания
CREATE TABLE IF NOT EXISTS schedule_updates (
    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule(date);
CREATE INDEX IF NOT EXISTS idx_schedule_group ON schedule(group_name);
CREATE INDEX IF NOT EXISTS idx_schedule_teacher ON schedule(teacher_name);

-- Создание триггера для обновления updated_at в таблице schedule
CREATE TRIGGER IF NOT EXISTS update_schedule_timestamp 
    AFTER UPDATE ON schedule
BEGIN
    UPDATE schedule SET updated_at = CURRENT_TIMESTAMP
    WHERE schedule_id = NEW.schedule_id;
END; 