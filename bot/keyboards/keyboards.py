from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import config, logger


def get_start_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
    
    kb = [
        [KeyboardButton(text="расписание"), KeyboardButton(text="Сайт колледжа")],
        [KeyboardButton(text="📊 График учебы")], [KeyboardButton(text="⚙️ Настройки")]
    ]
    if user_id is not None and user_id == config.ADMIN_ID:
        logger.info(f"Добавление админ-кнопок для пользователя {user_id}")
        kb.append([KeyboardButton(text="Админ-панель")])
        
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard

def get_admin_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🚫 Баны", callback_data="admin_bans"),
            InlineKeyboardButton(text=" График учебы", callback_data="admin_study_schedule")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить расписание", callback_data="admin_update")
        ],
        [
            InlineKeyboardButton(text="📨 Отправить всем", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="👤 Отправить по ID", callback_data="admin_send_id")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_study_schedule_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🔔 Звонки"), KeyboardButton(text="👥 Спецгруппы")],
        [KeyboardButton(text="📅 График обр процесса")],
        [KeyboardButton(text="Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_role_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Студент"), KeyboardButton(text="Преподаватель")],
        [KeyboardButton(text="Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
def get_groups_keyboard(groups: list) -> ReplyKeyboardMarkup:
    """Создание клавиатуры с группами"""
    kb = []
    try:
        if not groups:
            logger.error("Получен пустой список групп")
            return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Назад")]], resize_keyboard=True)
            
        sorted_groups = sorted(groups)
        logger.info(f"Создание клавиатуры для {len(sorted_groups)} групп")
        
        # Создаем кнопки по две в ряд
        for i in range(0, len(sorted_groups), 2):
            row = [KeyboardButton(text=sorted_groups[i])]
            if i + 1 < len(sorted_groups):
                row.append(KeyboardButton(text=sorted_groups[i + 1]))
            kb.append(row)
        
        # Добавляем кнопку "Назад"
        kb.append([KeyboardButton(text="Назад")])
        
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры групп: {e}")
        kb = [[KeyboardButton(text="Назад")]]
        
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_teachers_keyboard(teachers: list) -> ReplyKeyboardMarkup:
    """Создает клавиатуру со списком преподавателей"""
    if not teachers:
        logger.warning("Получен пустой список преподавателей")
        kb = [[KeyboardButton(text="Назад")]]
    else:
        try:
            sorted_teachers = sorted(teachers)
            kb = []
            # Разбиваем список преподавателей на пары для создания рядов кнопок
            for i in range(0, len(sorted_teachers), 2):
                row = [KeyboardButton(text=sorted_teachers[i])]
                if i + 1 < len(sorted_teachers):
                    row.append(KeyboardButton(text=sorted_teachers[i + 1]))
                kb.append(row)
            kb.append([KeyboardButton(text="Назад")])
            logger.info(f"Создана клавиатура с {len(sorted_teachers)} преподавателями")
        except Exception as e:
            logger.error(f"Ошибка при создании клавиатуры преподавателей: {e}")
            kb = [[KeyboardButton(text="Назад")]]
            
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_schedule_days_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры с днями недели"""
    kb = [
        [KeyboardButton(text="Понедельник"), KeyboardButton(text="Вторник")],
        [KeyboardButton(text="Среда"), KeyboardButton(text="Четверг")],
        [KeyboardButton(text="Пятница"), KeyboardButton(text="Суббота")],
        [KeyboardButton(text="Показать всё расписание")],
        [KeyboardButton(text="Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_settings_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Создает клавиатуру настроек с учетом роли пользователя"""
    kb = []
    
    # Кнопка оповещений
    notifications_status = "Выкл" if not user_data.get('notifications') else "Вкл"
    kb.append([InlineKeyboardButton(
        text=f"🔔 Оповещения: {notifications_status}",
        callback_data="toggle_notifications"
    )])
    
    # Кнопка изменения роли
    kb.append([InlineKeyboardButton(
        text="👤 Изменить роль",
        callback_data="change_role"
    )])
    
    # Кнопка изменения группы/преподавателя в зависимости от роли
    if user_data.get('role') == 'Студент':
        kb.append([InlineKeyboardButton(
            text="📚 Изменить группу",
            callback_data="change_group"
        )])
    else:
        kb.append([InlineKeyboardButton(
            text="👨‍🏫 Изменить преподавателя",
            callback_data="change_teacher"
        )])
    
    # Кнопка связи с админом
    kb.append([InlineKeyboardButton(
        text="📞 Сообщение администратору",
        callback_data="message_admin"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)
