from aiogram import Router, F
from aiogram.types import Message
from bot.keyboards.keyboards import get_admin_keyboard
from bot.config import config
from bot.config import logger
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.services.database import Database
from bot.services.parser import ScheduleParser
from google.cloud import firestore
from datetime import datetime, timedelta
import psutil
import os
from bot.utils.validators import InputValidator
from bot.services.logger import security_logger
from bot.services.monitoring import monitor
import asyncio
from aiogram.filters import Command

db = Database()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_user_id = State()
    waiting_for_user_message = State()
    waiting_for_schedule_type = State()
    waiting_for_schedule_photo = State()
    
admin_router = Router()

@admin_router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("⛔️ У вас нет доступа к этой команде")
        return
        
    await message.answer(
        "🛠 <b>Панель управления администратора</b>\n\n"
        "Выберите необходимое действие из меню ниже.",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@admin_router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        # Получаем статистику пользователей
        users = await db.get_all_users()
        total_users = len(users)
        
        # Считаем пользователей с уведомлениями
        notif_users = len([u for u in users if u.get('notifications', False)])

        # Считаем пользователей по ролям
        students = len([u for u in users if u.get('role') == 'student'])
        teachers = len([u for u in users if u.get('role') == 'teacher'])

        # Время работы бота
        bot_start_time = os.path.getctime(os.path.abspath(__file__))
        uptime = datetime.now() - datetime.fromtimestamp(bot_start_time)
        uptime_days = uptime.days
        uptime_hours = uptime.seconds // 3600 
        uptime_minutes = (uptime.seconds % 3600) // 60
        
        # Кэш
        cached_groups = len(await db.get_cached_groups())
        cached_teachers = len(await db.get_cached_teachers())

        stats_text = (
            "📊 <b>Детальная статистика бота</b>\n\n"
            f"⏱️ <b>Время работы:</b>\n"
            f"   • Дней: {uptime_days}\n"
            f"   • Часов: {uptime_hours}\n"
            f"   • Минут: {uptime_minutes}\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"   • Всего: {total_users}\n"
            f"   • Студентов: {students}\n"
            f"   • Преподавателей: {teachers}\n"
            f"   • С уведомлениями: {notif_users}\n\n"
            f"💾 <b>Кэш:</b>\n"
            f"   • Групп: {cached_groups}\n"
            f"   • Преподавателей: {cached_teachers}"
        )
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await callback.answer("❌ Произошла ошибка при получении статистики")

@admin_router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        users = await db.get_all_users()
        
        # Подсчет статистики по группам
        group_stats = {}
        total_students = 0
        total_teachers = 0
        
        for user in users:
            role = user.get('role')
            if role == 'Студент':
                total_students += 1
                group = user.get('selected_group')
                if group:
                    group_stats[group] = group_stats.get(group, 0) + 1
            elif role == 'Преподаватель':
                total_teachers += 1

        # Формируем текст статистики
        users_text = "👥 Статистика пользователей\n\n"
        
        users_text += "📊 Распределение по группам:\n"
        for group in sorted(group_stats.keys()):
            users_text += f"• {group}: {group_stats[group]} чел.\n"
        
        users_text += f"\n📈 Общая статистика:\n"
        users_text += f"• Всего пользователей: {len(users)}\n"
        users_text += f"• Студентов: {total_students}\n"
        users_text += f"• Преподавателей: {total_teachers}\n"
        users_text += f"• Количество групп: {len(group_stats)}\n"
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            users_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователей: {e}")
        await callback.answer("❌ Произошла ошибка")


@admin_router.callback_query(lambda c: c.data == "admin_update")
async def admin_update(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        await callback.message.edit_text("🔄 Начинаю обновление расписания...")
        
        parser = ScheduleParser()
        schedule_data, groups_list, teachers_list, error = await parser.parse_schedule()

        if error:
            logger.error(f"Ошибка при парсинге: {error}")
            await callback.message.edit_text(
                f"❌ Ошибка при обновлении расписания:\n{error}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
                ]])
            )
            return

        # Обновляем расписание в базе данных
        await db.update_schedule(schedule_data)
        # Обновляем время последнего обновления кэша
        await db.update_cache_time()
        
        update_text = (
            "✅ Расписание успешно обновлено!\n\n"
            f"📊 Статистика:\n"
            f"• Групп: {len(groups_list)}\n"
            f"• Преподавателей: {len(teachers_list)}"
        )
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            update_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button)
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении расписания: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при обновлении расписания",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
            ]])
        )

@admin_router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        users = await db.get_all_users()
        user_count = len(users) if users else 0

        await callback.message.edit_text(
            f"📨 Отправка сообщения всем пользователям\n\n"
            f"Всего пользователей: {user_count}\n\n"
            "Введите текст сообщения для рассылки.\n"
            "Поддерживается HTML-форматирование:\n"
            "• <b>жирный текст</b>\n"
            "• <i>курсив</i>\n"
            "• <u>подчеркнутый</u>\n"
            "• <code>моноширинный</code>\n"
            "• <a href='ссылка'>текст ссылки</a>\n\n"
            "Для отмены нажмите кнопку «Отменить»",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_admin")]
            ])
        )
        await state.set_state(AdminStates.waiting_for_broadcast_message)
    except Exception as e:
        logger.error(f"Ошибка при подготовке рассылки: {e}")
        await callback.answer("❌ Произошла ошибка")

@admin_router.callback_query(lambda c: c.data == "admin_send_id")
async def admin_send_id(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    # Получаем список всех пользователей
    users = await db.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "❌ В базе данных нет пользователей",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
            ]])
        )
        return

    await callback.message.edit_text(
        "👤 <b>Отправка сообщения по ID</b>\n\n"
        "Введите ID пользователя, которому хотите отправить сообщение:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
        ]])
    )
    await state.set_state(AdminStates.waiting_for_user_id)

@admin_router.callback_query(lambda c: c.data == "admin_study_schedule")
async def admin_study_schedule(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 График обр. процесса", callback_data="upload_schedule_edu")],
        [InlineKeyboardButton(text="👥 Спецгруппы", callback_data="upload_schedule_special")],
        [InlineKeyboardButton(text="🔔 Звонки", callback_data="upload_schedule_bells")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ])

    await callback.message.edit_text(
        "📋 Управление графиками и расписаниями\n\n"
        "Выберите тип расписания для загрузки:",
        reply_markup=keyboard
    )

@admin_router.callback_query(lambda c: c.data.startswith("upload_schedule_"))
async def schedule_upload_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    schedule_types = {
        "upload_schedule_edu": "график образовательного процесса",
        "upload_schedule_special": "список спецгрупп",
        "upload_schedule_bells": "расписание звонков"
    }

    schedule_type = callback.data
    await state.update_data(schedule_type=schedule_type)
    
    await callback.message.edit_text(
        f"📤 Отправьте фото для раздела «{schedule_types[schedule_type]}»\n\n"
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_admin")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_schedule_photo)

@admin_router.message(AdminStates.waiting_for_schedule_photo, F.photo)
async def process_schedule_photo(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return

    try:
        state_data = await state.get_data()
        schedule_type = state_data.get('schedule_type')

        # Получаем самую большую версию фото
        photo = message.photo[-1]
        file_id = photo.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path

        # Загружаем фото в Firebase Storage и получаем URL
        schedule_data = {
            'file_id': file_id,
            'file_path': file_path,
            'uploaded_at': firestore.SERVER_TIMESTAMP,
            'uploaded_by': message.from_user.id
        }

        # Сохраняем данные в Firestore
        schedule_types_map = {
            "upload_schedule_edu": "education_schedule",
            "upload_schedule_special": "special_groups",
            "upload_schedule_bells": "bell_schedule"
        }
        
        collection_name = schedule_types_map.get(schedule_type)
        if not collection_name:
            raise ValueError("Неверный тип расписания")

        await db.save_schedule_image(collection_name, schedule_data)

        await message.answer(
            "✅ Фото успешно загружено и сохранено!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к управлению", callback_data="admin_study_schedule")]
            ])
        )

    except Exception as e:
        logger.error(f"Ошибка при сохранении фото расписания: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении фото.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Попробовать снова", callback_data=schedule_type)],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
            ])
        )
    finally:
        await state.clear()

@admin_router.callback_query(lambda c: c.data == "back_to_admin")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    await state.clear()
    await callback.message.edit_text(
        "🛠 <b>Панель управления администратора</b>\n\n"
        "Выберите необходимое действие из меню ниже.",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@admin_router.callback_query(lambda c: c.data == "admin_bans")
async def admin_bans(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        banned_users = await db.get_banned_users()
        
        if not banned_users:
            await callback.message.edit_text(
                "📋 Список забаненных пользователей пуст",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
                ]])
            )
            return

        bans_text = "🚫 <b>Список забаненных пользователей:</b>\n\n"
        
        for user in banned_users:
            user_id = user['user_id']
            username = user.get('username', 'Нет username')
            ban_date = user.get('ban_date', 'Дата не указана')
            ban_reason = user.get('ban_reason', 'Причина не указана')
            
            bans_text += (
                f"👤 <b>ID:</b> <code>{user_id}</code>\n"
                f"<b>Username:</b> @{username}\n"
                f"<b>Дата бана:</b> {ban_date}\n"
                f"<b>Причина:</b> {ban_reason}\n"
                f"<a href='tg://user?id={user_id}'>Разбанить</a>\n\n"
            )

        # Создаем клавиатуру с кнопками разбана для каждого пользователя
        keyboard = []
        for user in banned_users:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🔓 Разбанить {user['user_id']}", 
                    callback_data=f"unban_{user['user_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")])
        
        await callback.message.edit_text(
            bans_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка банов: {e}")
        await callback.answer("❌ Произошла ошибка")

@admin_router.callback_query(lambda c: c.data.startswith("unban_"))
async def unban_user(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        user_id = int(callback.data.split("_")[1])
        if await db.unban_user(user_id):
            await callback.answer(f"✅ Пользователь {user_id} разбанен")
            # Обновляем список банов
            await admin_bans(callback)
        else:
            await callback.answer("❌ Ошибка при разбане пользователя")
    except Exception as e:
        logger.error(f"Ошибка при разбане пользователя: {e}")
        await callback.answer("❌ Произошла ошибка")

@admin_router.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для массовой рассылки"""
    if message.from_user.id != config.ADMIN_ID:
        return

    if not message.text:
        await message.answer("❌ Сообщение не может быть пустым")
        return

    try:
        users = await db.get_all_users()
        sent_count = 0
        error_count = 0
        batch_size = 30  # Размер пачки для одновременной отправки
        
        progress_msg = await message.answer("⏳ Начинаю рассылку...")

        # Разбиваем пользователей на пачки
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            tasks = []
            
            # Создаем задачи для каждого пользователя в пачке
            for user in batch:
                try:
                    user_id = int(user['user_id'])
                    task = message.bot.send_message(
                        user_id,
                        message.text,
                        parse_mode="HTML"
                    )
                    tasks.append(task)
                except ValueError:
                    error_count += 1
                    continue

            # Отправляем сообщения пачкой
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1
                    else:
                        sent_count += 1
                
                # Обновляем прогресс
                await progress_msg.edit_text(
                    f"⏳ Прогресс рассылки:\n"
                    f"• Отправлено: {sent_count}/{len(users)}\n"
                    f"• Ошибок: {error_count}\n"
                    f"• Прогресс: {((i + len(batch)) / len(users) * 100):.1f}%"
                )
                
                # Небольшая пауза между пачками
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка при отправке пачки сообщений: {e}")
                error_count += len(tasks)

        # Итоговый отчет
        await progress_msg.edit_text(
            f"✅ Рассылка завершена\n\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {len(users)}\n"
            f"• Успешно отправлено: {sent_count}\n"
            f"• Ошибок: {error_count}\n"
            f"• Процент успеха: {(sent_count/len(users)*100):.1f}%"
        )

        logger.info(f"Рассылка завершена. Отправлено: {sent_count}, Ошибок: {error_count}")

    except Exception as e:
        logger.error(f"Ошибка при массовой рассылке: {e}")
        await message.answer(
            "❌ Произошла ошибка при рассылке\n"
            f"Ошибка: {str(e)}"
        )
    
    finally:
        await state.clear()

@admin_router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    """Обработка введенного ID пользователя"""
    if message.from_user.id != config.ADMIN_ID:
        return

    try:
        user_id = int(message.text)
        # Проверяем существование пользователя
        user_exists = await db.user_exists(user_id)
        
        if not user_exists:
            await message.answer(
                "❌ Пользователь с таким ID не найден\n"
                "Попробуйте ввести другой ID или нажмите кнопку «Назад»",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
                ]])
            )
            return

        # Сохраняем ID пользователя в состояние
        await state.update_data(target_user_id=user_id)
        
        await message.answer(
            "✏️ Теперь введите текст сообщения для отправки.\n"
            "Поддерживается HTML-форматирование:\n"
            "• <b>жирный текст</b>\n"
            "• <i>курсив</i>\n"
            "• <u>подчеркнутый</u>\n"
            "• <code>моноширинный</code>\n"
            "• <a href='ссылка'>текст ссылки</a>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_admin")
            ]])
        )
        await state.set_state(AdminStates.waiting_for_user_message)
        
    except ValueError:
        await message.answer(
            "❌ Некорректный ID пользователя. Введите числовой ID:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
            ]])
        )

@admin_router.message(AdminStates.waiting_for_user_message)
async def process_user_message(message: Message, state: FSMContext):
    """Обработка сообщения для отправки конкретному пользователю"""
    if message.from_user.id != config.ADMIN_ID:
        return

    if not message.text:
        await message.answer("❌ Сообщение не может быть пустым")
        return

    try:
        # Получаем сохраненный ID пользователя
        state_data = await state.get_data()
        user_id = state_data.get('target_user_id')
        
        if not user_id:
            await message.answer("❌ Ошибка: ID пользователя не найден")
            await state.clear()
            return

        # Отправляем сообщение
        try:
            await message.bot.send_message(
                user_id,
                message.text,
                parse_mode="HTML"
            )
            
            await message.answer(
                "✅ Сообщение успешно отправлено!\n\n"
                f"Получатель: {user_id}\n"
                f"Текст: {message.text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
                ]])
            )
            logger.info(f"Админ отправил сообщение пользователю {user_id}")
            
        except Exception as e:
            await message.answer(
                f"❌ Ошибка при отправке сообщения:\n{str(e)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
                ]])
            )
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике сообщения: {e}")
        await message.answer("❌ Произошла ошибка при обработке сообщения")
    
    finally:
        await state.clear()


