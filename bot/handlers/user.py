from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.keyboards.keyboards import (
    get_role_keyboard,
    get_groups_keyboard,
    get_teachers_keyboard,
    get_start_keyboard,
    get_schedule_days_keyboard,
    get_study_schedule_keyboard,
    get_settings_keyboard
)
from bot.services.database import Database
from bot.services.parser import ScheduleParser
from bot.config import logger, WEEKDAYS, config
from bot.middlewares import ScheduleFormatter
from bot.decorators import user_exists_check
import os
from datetime import datetime, timedelta
from bot.utils.date_helpers import format_russian_date, get_russian_weekday
from aiogram.filters import Command

# Создаем роутер для пользовательских команд
user_router = Router()
db = Database()
parser = ScheduleParser()

class ScheduleStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_group = State()
    waiting_for_teacher = State()
    waiting_for_day = State()
    waiting_for_admin_message = State()

@user_router.message(F.text == "Сайт колледжа")
@user_exists_check()
async def college_website(message: Message):
    await message.answer(
        "🌐 Нажмите кнопку ниже, чтобы открыть сайт колледжа:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть сайт", web_app={"url": "https://bartc.by/index.php/obuchayushchemusya/dnevnoe-otdelenie/tekushchee-raspisanie"})]
            ]
        )
    )

@user_router.message(F.text == "📊 График учебы")
@user_exists_check()
async def study_schedule(message: Message):
    await message.answer(
        "🎓 Выберите действие:",
        reply_markup=get_study_schedule_keyboard()
    )
    
@user_router.message(F.text == "📅 График обр процесса")
@user_exists_check()
async def education_schedule(message: Message):
    """Отправка графика образовательного процесса"""
    try:
        schedule_data = await db.get_schedule_image('education_schedule')
        if not schedule_data:
            await message.answer("❌ График образовательного процесса еще не загружен")
            return
            
        await message.answer_photo(
            schedule_data['file_id'],
            caption="📅 График образовательного процесса"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке графика образовательного процесса: {e}")
        await message.answer("❌ Произошла ошибка при загрузке графика")

@user_router.message(F.text == "👥 Спецгруппы")
@user_exists_check()
async def special_groups(message: Message):
    """Отправка списка спецгрупп"""
    schedule_data = await db.get_schedule_image('special_groups')
    if not schedule_data:
        await message.answer("❌ Список спецгрупп еще не загружен")
        return
    
    await message.answer_photo(
        schedule_data['file_id'],
        caption="👥 Список специальных групп"
    )   

@user_router.message(F.text == "🔔 Звонки")
@user_exists_check()
async def bell_schedule(message: Message):
    """Отправка расписания звонков"""
    schedule_data = await db.get_schedule_image('bell_schedule')
    if not schedule_data:
        await message.answer("❌ Расписание звонков еще не загружено")
        return
    
    await message.answer_photo(
        schedule_data['file_id'],
        caption="🔔 Расписание звонков"
    )


@user_router.message(F.text == "Назад")
@user_exists_check()
async def back_to_main_menu(message: Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вернулся в главное меню")
    await state.clear()
    await message.answer(
        "👋 Привет! 🤖 Я бот для просмотра расписания БТК.\n\n⚙️ Вы можете изменить свою роль в меню настроек.",
        reply_markup=get_start_keyboard(message.from_user.id)
    )
@user_router.message(F.text == "⚙️ Настройки")
@user_exists_check()
async def settings_menu(message: Message, state: FSMContext):
    """Обработчик меню настроек"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data:
        logger.error(f"Не удалось получить данные пользователя {user_id}")
        await message.answer("❌ Произошла ошибка при загрузке настроек")
        return

    role_text = user_data.get('role', 'Не выбрана')
    teacher_text = user_data.get('selected_teacher', 'Не выбран')
    group_text = user_data.get('selected_group', 'Не выбрана')

    settings_text = "⚙️ Настройки\n\n"
    settings_text += f"👤 Роль: {role_text}\n"
    
    if role_text == "Преподаватель":
        settings_text += f"📋 Преподаватель: {teacher_text}\n"
    else:
        settings_text += f"📋 Группа: {group_text}\n"

    settings_text += "\nДоступные настройки:\n"
    settings_text += "🔔 Оповещения - включить/выключить уведомления о расписании\n"
    settings_text += "👤 Изменить роль - выбрать роль студента или преподавателя\n"
    settings_text += "👨‍🏫 Изменить преподавателя - выбрать преподавателя для отслеживания\n" 
    settings_text += "📞 Сообщение администратору - связаться с администратором бота"

    await message.answer(
        settings_text,
        reply_markup=get_settings_keyboard(user_data)
    )

@user_router.callback_query(lambda c: c.data == "toggle_notifications")
async def toggle_notifications_callback(callback: CallbackQuery):
    """Обработчик включения/выключения уведомлений"""
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data:
        await callback.answer("❌ Ошибка получения данных пользователя")
        return

    new_status = not user_data.get('notifications', False)
    if await db.toggle_notifications(user_id, new_status):
        user_data['notifications'] = new_status
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(user_data))
        await callback.answer("✅ Настройки уведомлений обновлены")
    else:
        await callback.answer("❌ Ошибка обновления настроек")

@user_router.callback_query(lambda c: c.data == "change_role")
async def change_role_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения роли"""
    await callback.message.answer("👥 Выберите вашу роль:", reply_markup=get_role_keyboard())
    await state.set_state(ScheduleStates.waiting_for_role)
    await callback.answer()

@user_router.callback_query(lambda c: c.data == "change_group")
async def change_group_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения группы"""
    groups = await db.get_cached_groups()
    if groups:
        await callback.message.answer(
            "📚 Выберите вашу группу:",
            reply_markup=get_groups_keyboard(groups)
        )
        await state.set_state(ScheduleStates.waiting_for_group)
    else:
        await callback.answer("❌ Не удалось получить список групп")

@user_router.callback_query(lambda c: c.data == "change_teacher")
async def change_teacher_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения преподавателя"""
    teachers = await db.get_cached_teachers()
    if teachers:
        await callback.message.answer(
            "👨‍🏫 Выберите преподавателя:",
            reply_markup=get_teachers_keyboard(teachers)
        )
        await state.set_state(ScheduleStates.waiting_for_teacher)
    else:
        await callback.answer("❌ Не удалось получить список преподавателей")

@user_router.callback_query(lambda c: c.data == "message_admin")
async def message_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик отправки сообщения администратору"""
    await callback.message.answer(
        "📝 Напишите ваше сообщение для администратора.\n\n"
        "Чтобы отменить, напишите /cancel"
    )
    await state.set_state(ScheduleStates.waiting_for_admin_message)
    await callback.answer()

@user_router.message(ScheduleStates.waiting_for_admin_message)
async def process_admin_message(message: Message, state: FSMContext):
    """Обработка сообщения для администратора"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отправка сообщения администратору отменена")
        return

    if not message.text:
        await message.answer("❌ Сообщение не может быть пустым")
        return

    try:
        # Формируем сообщение для админа
        admin_message = (
            f"📨 Новое сообщение от пользователя\n"
            f"👤 ID: {message.from_user.id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Username: @{message.from_user.username}\n\n"
            f"📝 Сообщение:\n{message.text}"
        )

        # Отправляем сообщение админу
        await message.bot.send_message(config.ADMIN_ID, admin_message)
        
        # Отправляем подтверждение пользователю
        await message.answer(
            "✅ Ваше сообщение успешно отправлено администратору!"
        )
        
        logger.info(f"Пользователь {message.from_user.id} отправил сообщение администратору")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения администратору: {e}")
        await message.answer("❌ Произошла ошибка при отправке сообщения. Попробуйте позже.")
    
    finally:
        await state.clear()


@user_router.message(F.text == "расписание")
@user_exists_check()
async def schedule_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил расписание")
    user_data = await db.get_user(user_id)
    
    if not user_data or not user_data.get('role'):
        logger.info(f"Пользователь {user_id} еще не выбрал роль")
        await message.answer(
            "👥 Выберите вашу роль:",
            reply_markup=get_role_keyboard()
        )
        await state.set_state(ScheduleStates.waiting_for_role)
    else:
        role = user_data.get('role')
        if role == 'Студент' and not user_data.get('selected_group'):
            groups = await db.get_groups()
            if not groups:
                await message.answer("❌ Не удалось получить список групп")
                return
            await message.answer(
                "📚 Выберите вашу группу:",
                reply_markup=get_groups_keyboard(groups)
            )
            await state.set_state(ScheduleStates.waiting_for_group)
        elif role == 'Преподаватель' and not user_data.get('selected_teacher'):
            teachers = await db.get_teachers()
            if not teachers:
                await message.answer("❌ Не удалось получить список преподавателей")
                return
            await message.answer(
                "👨‍🏫 Выберите преподавателя:",
                reply_markup=get_teachers_keyboard(teachers)
            )
            await state.set_state(ScheduleStates.waiting_for_teacher)
        else:
            await message.answer(
                "📅 Выберите день недели:",
                reply_markup=get_schedule_days_keyboard()
            )
            await state.set_state(ScheduleStates.waiting_for_day)

@user_router.message(ScheduleStates.waiting_for_role)
async def process_role_selection(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text not in ["Студент", "Преподаватель"]:
        logger.warning(f"Пользователь {user_id} выбрал некорректную роль: {message.text}")
        await message.answer("Пожалуйста, выберите корректную роль")
        return

    logger.info(f"Пользователь {user_id} выбрал роль: {message.text}")
    await db.update_user_role(user_id, message.text)

    if message.text == "Студент":
        logger.info(f"Запрашиваем список групп для пользователя {user_id}")
        groups = await db.get_groups()
        if not groups:
            await message.answer("Не удалось получить список групп")
            return
        await message.answer(
            "📚 Выберите вашу группу:",
            reply_markup=get_groups_keyboard(groups)
        )
        await state.set_state(ScheduleStates.waiting_for_group)
    else:
        logger.info(f"Запрашиваем список преподавателей для пользователя {user_id}")
        teachers = await db.get_teachers()
        if not teachers:
            await message.answer("Не удалось получить список преподавателей")
            return
        await message.answer(
            "👨‍🏫 Выберите преподавателя:",
            reply_markup=get_teachers_keyboard(teachers)
        )
        await state.set_state(ScheduleStates.waiting_for_teacher)

@user_router.message(ScheduleStates.waiting_for_group)
async def process_group_selection(message: Message, state: FSMContext):
    user_id = message.from_user.id

    logger.info(f"Пользователь {user_id} выбрал группу: {message.text}")
    await db.update_selected_group(user_id, message.text)
    
    await message.answer(
        "📅 Выберите день недели:",
        reply_markup=get_schedule_days_keyboard()
    )
    await state.set_state(ScheduleStates.waiting_for_day)

@user_router.message(ScheduleStates.waiting_for_teacher)
async def process_teacher_selection(message: Message, state: FSMContext):
    user_id = message.from_user.id

    logger.info(f"Пользователь {user_id} выбрал преподавателя: {message.text}")
    await db.update_selected_teacher(user_id, message.text)
    
    await message.answer(
        "📅 Выберите день недели:",
        reply_markup=get_schedule_days_keyboard()
    )
    await state.set_state(ScheduleStates.waiting_for_day)

@user_router.message(ScheduleStates.waiting_for_day)
async def process_day_selection(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    parser = ScheduleParser()
    
    if message.text == "Показать всё расписание":
        schedule_data = await parser.get_full_schedule(user_data)
        if not schedule_data:
            await message.answer("❌ Расписание не найдено")
            return
        response = ScheduleFormatter.format_full_schedule(schedule_data, user_data)
        await message.answer(response)
        
    elif message.text in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]:
        schedule_data = await parser.get_schedule_for_day(message.text.lower(), user_data)
        if isinstance(schedule_data, list):
            response = ScheduleFormatter.format_schedule(schedule_data, message.text, user_data)
            await message.answer(response)
        elif isinstance(schedule_data, str):
            # Если вернулось сообщение об ошибке
            await message.answer(schedule_data)
        else:
            await message.answer(
                f"ℹ️ Расписание на {message.text.lower()}\n\n"
                "В ближайшие дни занятий нет."
            )
    else:
        await message.answer("❌ Пожалуйста, выберите корректный день недели из меню")
        return
    
    await state.set_state(ScheduleStates.waiting_for_day)

@user_router.message(Command("today"))
async def cmd_today(message: Message):
    """Показать расписание на сегодня"""
    try:
        today = datetime.now().strftime("%A").lower()
        await message.answer(f"🗓 Получаю расписание на сегодня ({today})...")
        # Здесь будет логика получения расписания
    except Exception as e:
        logger.error(f"Ошибка при получении расписания на сегодня: {e}")
        await message.answer("❌ Ошибка при получении расписания")

@user_router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    """Показать расписание на завтра"""
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A").lower()
        await message.answer(f"🗓 Получаю расписание на завтра ({tomorrow})...")
        # Здесь будет логика получения расписания
    except Exception as e:
        logger.error(f"Ошибка при получении расписания на завтра: {e}")
        await message.answer("❌ Ошибка при получении расписания")

@user_router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Показать полное расписание"""
    try:
        await message.answer("📚 Получаю полное расписание...")
        # Здесь будет логика получения расписания
    except Exception as e:
        logger.error(f"Ошибка при получении полного расписания: {e}")
        await message.answer("❌ Ошибка при получении расписания")