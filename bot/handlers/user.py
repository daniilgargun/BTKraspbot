from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
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
from bot.database.db_adapter import db_adapter as db
from bot.services.parser import ScheduleParser
from bot.config import logger, WEEKDAYS, config
from bot.middlewares import ScheduleFormatter
from bot.decorators import user_exists_check
from bot.utils.april_fools import get_survival_stats, get_mercy_button, handle_mercy_request, is_april_fools_day
import os
from datetime import datetime, timedelta
from bot.utils.date_helpers import format_russian_date, get_russian_weekday
from aiogram.filters import Command

# Создаем роутер для пользовательских команд
user_router = Router()
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
               #[InlineKeyboardButton(text="Открыть сайт?", web_app={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})]
            ]
        )
    )

@user_router.message(F.text == "📊 График учебы")
@user_exists_check()
async def study_schedule(message: Message):
    # Всегда показываем меню выбора действий для графика учебного процесса
    await message.answer(
        "🎓 Выберите действие:",
        reply_markup=get_study_schedule_keyboard()
    )

@user_router.message(F.text == "Скачать приложение")
@user_exists_check()
async def download_app(message: Message):
    from aiogram.types import FSInputFile
    
    # Попробуем несколько вариантов путей к изображению
    possible_paths = [
        # Абсолютный путь с использованием __file__
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "BTKmobil.png"),
        # Относительный путь от текущей рабочей директории
        os.path.join("bot", "database", "BTKmobil.png"),
        # Для случаев запуска из корня проекта
        "bot/database/BTKmobil.png"
    ]
    
    try:
        # Проверяем каждый путь и используем первый существующий
        image_path = None
        for path in possible_paths:
            if os.path.exists(path):
                image_path = path
                logger.info(f"Найдено изображение приложения: {path}")
                break
        
        if not image_path:
            # Если не нашли файл, выводим сообщение без изображения
            logger.error("Изображение приложения не найдено по всем указанным путям")
            await message.answer(
                "📲 <b>Хотите пользоваться расписанием ещё удобнее?</b>\n\n"
                "Теперь доступно мобильное приложение <b>«БТК Расписание»</b> для Android!\n\n"
                "✅ Быстрый доступ к расписанию\n"
                "✅ Календарь с прошлым расписанием\n"
                "✅ Простой и удобный интерфейс\n\n"
                "<a href='https://play.google.com/store/apps/details?id=com.gargun.btktimetable'>"
                "👉 <b>Скачать приложение на Android</b></a>\n\n"
                "💬 <i>Приложение только для Android.\n"
                "Если есть идеи или предложения — пишите админу через <b>Настройки</b>!</i>",
                parse_mode="HTML"
            )
            return

        # Отправляем изображение с красивым оформлением и ссылкой на приложение
        await message.answer_photo(
            photo=FSInputFile(image_path),
            caption=(
                "📲 <b>Хотите пользоваться расписанием ещё удобнее?</b>\n\n"
                "Теперь доступно мобильное приложение <b>«БТК Расписание»</b> для Android!\n\n"
                "✅ Быстрый доступ к расписанию\n"
                "✅ Календарь с прошлым расписанием\n"
                "✅ Простой и удобный интерфейс\n\n"
                "<a href='https://play.google.com/store/apps/details?id=com.gargun.btktimetable'>"
                "👉 <b>Скачать приложение на Android</b></a>\n\n"
                "💬 <i>Приложение только для Android.\n"
                "Если есть идеи или предложения — пишите админу через <b>Настройки</b>!</i>"
            ),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {message.from_user.id} запросил информацию о приложении")
    except Exception as e:
        logger.error(f"Ошибка при отправке изображения приложения: {e}")
        await message.answer("❌ Произошла ошибка при отправке информации о приложении. Попробуйте позже.")

@user_router.message(F.text == "📅 График обр процесса")
@user_exists_check()
async def education_schedule(message: Message):
    """Отправка графика образовательного процесса"""
    try:
        # Сначала проверяем наличие графика в новой системе
        photo_info = await db.get_active_schedule_photo()
        
        if photo_info:
            await message.answer_photo(
                photo_info["file_id"],
                caption="📅 График учебного процесса"
            )
            return
            
        # Если нет, пробуем получить из старой системы
        schedule_data = await db.get_schedule_image('education_schedule')
        if schedule_data:
            await message.answer_photo(
                schedule_data['file_id'],
                caption="📅 График образовательного процесса"
            )
        else:
            await message.answer("❌ График образовательного процесса еще не загружен")
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
    
    # Исправляем ключ с 'notifications' на 'notifications_enabled'
    current_status = user_data.get('notifications_enabled', False)
    new_status = not current_status
    
    if await db.toggle_notifications(user_id, new_status):
        # Обновляем данные пользователя в памяти
        user_data['notifications_enabled'] = new_status
        status_text = "включены" if new_status else "выключены"
        
        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(user_data))
        
        # Показываем уведомление
        await callback.answer(f"✅ Уведомления {status_text}")
    else:
        await callback.answer("❌ Ошибка обновления настроек уведомлений")

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

        # Отправляем сообщение всем администраторам
        success_count = 0
        for admin_id in config.ADMIN_IDS:
            try:
                await message.bot.send_message(admin_id, admin_message)
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения администратору {admin_id}: {e}")
        
        # Отправляем подтверждение пользователю
        if success_count > 0:
            await message.answer(
                "✅ Ваше сообщение успешно отправлено администраторам!"
            )
            logger.info(f"Пользователь {message.from_user.id} отправил сообщение администраторам ({success_count} получателей)")
        else:
            await message.answer("❌ Произошла ошибка при отправке сообщения. Попробуйте позже.")
            logger.error(f"Не удалось отправить сообщение ни одному администратору от пользователя {message.from_user.id}")
        
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
    
    # Если пользователь не найден, но должен существовать (так как прошел user_exists_check),
    # попробуем создать его еще раз
    if not user_data:
        logger.warning(f"Пользователь {user_id} не найден после проверки user_exists_check, пробуем создать")
        await db.create_user(user_id)
        # Получаем данные пользователя снова
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
    
    # Показываем сообщение об успешном обновлении роли
    await message.answer(f"✅ Роль успешно изменена на <b>{message.text}</b>")

    if message.text == "Студент":
        logger.info(f"Запрашиваем список групп для пользователя {user_id}")
        groups = await db.get_cached_groups()  # Используем кэшированные данные
        if not groups:
            groups = await db.get_groups()  # Если кэш пустой, запрашиваем данные напрямую
            
        if not groups:
            await message.answer("Не удалось получить список групп")
            await state.clear()
            return
            
        await message.answer(
            "📚 Выберите вашу группу:",
            reply_markup=get_groups_keyboard(groups)
        )
        await state.set_state(ScheduleStates.waiting_for_group)
    else:
        logger.info(f"Запрашиваем список преподавателей для пользователя {user_id}")
        teachers = await db.get_cached_teachers()  # Используем кэшированные данные
        if not teachers:
            teachers = await db.get_teachers()  # Если кэш пустой, запрашиваем данные напрямую
            
        if not teachers:
            await message.answer("Не удалось получить список преподавателей")
            await state.clear()
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
    
    # Сбрасываем состояние
    await state.clear()
    
    # Получаем данные пользователя для отображения в настройках
    user_data = await db.get_user(user_id)
    
    # Показываем сообщение об успешном обновлении
    await message.answer(f"✅ Группа успешно изменена на <b>{message.text}</b>")
    
    # Возвращаемся в меню настроек
    role_text = user_data.get('role', 'Не выбрана')
    group_text = user_data.get('selected_group', 'Не выбрана')
    teacher_text = user_data.get('selected_teacher', 'Не выбран')
    
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
        f"✅ Группа успешно изменена на <b>{message.text}</b>",
        reply_markup=get_start_keyboard(user_id)  # Возвращаем на стартовую клавиатуру
    )

@user_router.message(ScheduleStates.waiting_for_teacher)
async def process_teacher_selection(message: Message, state: FSMContext):
    user_id = message.from_user.id

    logger.info(f"Пользователь {user_id} выбрал преподавателя: {message.text}")
    await db.update_selected_teacher(user_id, message.text)
    
    # Сбрасываем состояние
    await state.clear()
    
    # Получаем данные пользователя для отображения в настройках
    user_data = await db.get_user(user_id)
    
    # Показываем сообщение об успешном обновлении
    await message.answer(f"✅ Преподаватель успешно изменен на <b>{message.text}</b>")
    
    # Возвращаемся в меню настроек
    role_text = user_data.get('role', 'Не выбрана')
    group_text = user_data.get('selected_group', 'Не выбрана')
    teacher_text = user_data.get('selected_teacher', 'Не выбран')
    
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
        f"✅ Преподаватель успешно изменен на <b>{message.text}</b>",
        reply_markup=get_start_keyboard(user_id)  # Возвращаем на стартовую клавиатуру
    )

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
        
        # Добавляем первоапрельскую статистику выживаемости, если сегодня 1 апреля
        if is_april_fools_day():
            response += get_survival_stats("full")
            # Добавляем кнопку "Просить пощады"
            await message.answer(response, reply_markup=get_mercy_button())
        else:
            await message.answer(response)
        
    elif message.text in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]:
        # Определяем тип дня для статистики выживаемости
        day_type = "weekend" if message.text == "Суббота" else "lecture"

        schedule_data = await parser.get_schedule_for_day(message.text.lower(), user_data)
        
        # Теперь schedule_data может быть словарем или строкой (сообщением об ошибке)
        if isinstance(schedule_data, dict):
            # Если расписание найдено и это словарь, форматируем его
            if schedule_data:
                response = ScheduleFormatter.format_schedule(schedule_data, message.text, user_data)
                
                # Добавляем первоапрельскую статистику выживаемости, если сегодня 1 апреля
                if is_april_fools_day():
                    response += get_survival_stats(day_type)
                    # Добавляем кнопку "Просить пощады"
                    await message.answer(response, reply_markup=get_mercy_button())
                else:
                    await message.answer(response)
            else:
                # Если словарь пустой, значит занятий нет
                resp_text = (
                    f"ℹ️ Расписание на {message.text.lower()}\n\n"
                    "В ближайшие дни занятий нет."
                )
                if is_april_fools_day():
                    resp_text += get_survival_stats("weekend")
                    await message.answer(resp_text, reply_markup=get_mercy_button())
                else:
                    await message.answer(resp_text)

        elif isinstance(schedule_data, str):
            # Если вернулось сообщение об ошибке
            await message.answer(schedule_data)
        else:
            # На случай, если что-то пошло не так и вернулся неожиданный тип
            await message.answer("❌ Произошла неизвестная ошибка при получении расписания.")
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

@user_router.message(Command("schedule_photo"))
async def send_schedule_photo(message: Message):
    """Отправка графика учебного процесса пользователю"""
    try:
        # Получаем активный график
        photo_info = await db.get_active_schedule_photo()
        
        if photo_info:
            await message.answer_photo(
                photo_info["file_id"],
                caption="📅 График учебного процесса"
            )
        else:
            await message.answer(
                "❌ График учебного процесса пока не загружен.\n"
                "Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке графика пользователю: {e}")
        await message.answer(
            "❌ Произошла ошибка при получении графика.\n"
            "Пожалуйста, попробуйте позже."
        )

# Обработчик нажатия на кнопку "Просить пощады"
@user_router.callback_query(lambda c: c.data == "april_fools_mercy")
async def mercy_button_callback(callback: CallbackQuery):
    # Проверяем, первое ли апреля
    if is_april_fools_day():
        # Получаем случайный ответ о пощаде
        response = await handle_mercy_request(callback.message)
        # Отвечаем в виде временного всплывающего сообщения
        await callback.answer(response, show_alert=True)
    else:
        # Если не первое апреля, сообщаем что функция недоступна
        await callback.answer("Эта функция доступна только 1 апреля!", show_alert=True)