import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, SUPPORT_USERNAME
from database import add_user, update_service, init_db, is_admin, get_all_requests, add_admin, get_user_requests, update_request_status
from aiogram.types import InputMediaPhoto, InputMediaVideo
import aiosqlite
from datetime import datetime, timedelta


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

DB_PATH = "users.db"

admin_states = {}

portfolio_items = [
    {
        "type": "photo",
        "media": "https://cdn-edge.kwork.ru/files/portfolio/t3/40/75ce69e15585395879863b8114c89f3e8f4d98f1-1685679487.jpg",
        "caption": "Сайт-визитка для клиента A"
    },
    {
        "type": "photo",
        "media": "https://pic.rutubelist.ru/video/5d/24/5d241166a5413e7e6f6ed3c8d8be9012.jpg",
        "caption": "Пример слайдшоу"
    }
]


# Главное меню
main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📈 Услуги", callback_data="services")],
    [InlineKeyboardButton(text="📂 Посмотреть примеры", callback_data="portfolio")],
    [InlineKeyboardButton(text="🆘 Тех. поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
    [InlineKeyboardButton(text="🌟 Наши отзывы", callback_data="view_reviews")]
])

# Кнопки услуг
services_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💻 Сайт-визитка", callback_data="service_Сайт-визитка")],
    [InlineKeyboardButton(text="💎 Установка ОС", callback_data="service_Установка ОС")],
    [InlineKeyboardButton(text="🌇 Слайдшоу", callback_data="service_Слайдшоу")],
    [InlineKeyboardButton(text="🙆‍♀️ Обработка старого фото", callback_data="service_Обработка старого фото")],
])

async def send_main_menu(user_id: int, text: str = "Что вас интересует?"):
    photo_url = "https://sun9-36.userapi.com/impf/c850232/v850232621/153fd8/rgSHvgyOdDk.jpg?size=1048x1048&quality=96&sign=656aef88ba383f6f471e719fd5babe79&type=album"

    await bot.send_photo(
        chat_id=user_id,
        photo=photo_url,
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Услуги", callback_data="services")],
            [InlineKeyboardButton(text="📂 Посмотреть примеры", callback_data="portfolio")],
            [InlineKeyboardButton(text="🆘 Тех. поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="🌟 Наши отзывы", callback_data="view_reviews")]
        ])
    )

@dp.callback_query(F.data == "view_reviews")
async def view_reviews(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT telegram_id, review, rating FROM users WHERE review IS NOT NULL")
        reviews = await cursor.fetchall()

    if not reviews:
        await callback.message.answer("У нас пока нет отзывов.")
    else:
        text = "📋 <b>Отзывы:</b>\n\n"
        for user_id, review, rating in reviews:
            text += f"👤 <code>{user_id}</code> — Оценка: {rating}/5\nОтзыв: {review}\n\n"

        await callback.message.answer(text)


@dp.callback_query(F.data == "portfolio")
async def portfolio_start(callback: CallbackQuery):
    index = 0
    item = portfolio_items[index]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"portfolio_nav:{index-1}"),
            InlineKeyboardButton(text="➡️", callback_data=f"portfolio_nav:{index+1}")
        ]
    ])

    if item["type"] == "photo":
        await callback.message.answer_photo(photo=item["media"], caption=item["caption"], reply_markup=keyboard)
    else:
        await callback.message.answer_video(video=item["media"], caption=item["caption"], reply_markup=keyboard)


@dp.callback_query(F.data.startswith("portfolio_nav:"))
async def portfolio_navigate(callback: CallbackQuery):
    index = int(callback.data.split(":")[1])
    total = len(portfolio_items)

    if index < 0 or index >= total:
        await callback.answer("Нет больше работ.")
        return

    item = portfolio_items[index]

    # Кнопки навигации
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"portfolio_nav:{index-1}"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"portfolio_nav:{index+1}"))

    # Кнопка выхода
    exit_button = InlineKeyboardButton(text="🔙 Выйти в меню", callback_data="portfolio_exit")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=([nav_buttons] if nav_buttons else []) + [[exit_button]]
    )

    await callback.message.delete()

    if item["type"] == "photo":
        await callback.message.answer_photo(photo=item["media"], caption=item["caption"], reply_markup=keyboard)
    else:
        await callback.message.answer_video(video=item["media"], caption=item["caption"], reply_markup=keyboard)

@dp.callback_query(F.data == "portfolio_exit")
async def portfolio_exit(callback: CallbackQuery):
    await callback.message.delete()
    await send_main_menu(callback.from_user.id, "🔙 Вы вернулись в главное меню.")


@dp.message(CommandStart())
async def start_handler(message: Message):
    await add_user(message.from_user.id)
    await send_main_menu(message.from_user.id, "Добро пожаловать! Выберите действие:")

@dp.callback_query(F.data == "services")
async def services_handler(callback: CallbackQuery):
    await callback.message.answer("Выберите интересующую вас услугу:", reply_markup=services_kb)

@dp.callback_query(F.data.startswith("service_"))
async def service_selected(callback: CallbackQuery):
    service = callback.data.split("service_")[1]
    await update_service(callback.from_user.id, service)
    await callback.message.answer(
        f"Заявка на услугу <b>{service}</b> успешно принята!\n"
        "Через несколько минут вам ответит исполнитель в ЛС."
    )
    await send_main_menu(callback.from_user.id)

@dp.message(F.text == "/status")
async def status_handler(message: Message):
    requests = await get_user_requests(message.from_user.id)
    if not requests:
        return await message.answer("У вас пока нет активных заявок.")

    text = "📋 <b>Ваши заявки:</b>\n\n"
    for req_id, service, status in requests:
        text += f"🆔 <code>{req_id}</code> — {service} — <b>{status}</b>\n"
    await message.answer(text)


@dp.message(F.text == "/admin")
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет доступа к админ-панели.")

    requests = await get_all_requests()
    if not requests:
        return await message.answer("Заявок пока нет.")

    text = "📋 <b>Список заявок:</b>\n\n"
    for req_id, user_id, service, status, created_at, status_changed_at in requests:
        text += f"{created_at} 🆔 <code>{req_id}</code> | 👤 <code>{user_id}</code> — {service} — (🕒: {status_changed_at}) <b>{status}</b>\n"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉ Написать пользователю", callback_data="admin_write_user")],
        [InlineKeyboardButton(text="✏ Изменить статус заявки", callback_data="admin_change_status")],
        [InlineKeyboardButton(text="📊 Статистика заявок", callback_data="admin_show_analytics")],
        [InlineKeyboardButton(text="🔙 Выйти в главное меню", callback_data="admin_back")]
    ])
    await message.answer(text, reply_markup=markup)



async def get_weekly_stats():
    one_week_ago = datetime.now() - timedelta(weeks=1)
    one_week_ago_str = one_week_ago.isoformat(' ', timespec='seconds')

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT service, COUNT(*) FROM users
            WHERE created_at >= ?
            GROUP BY service
        """, (one_week_ago_str,))
        weekly_stats = await cursor.fetchall()
        return weekly_stats



async def get_service_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем количество заявок по каждой услуге
        cursor = await db.execute("""
            SELECT service, COUNT(*) FROM users
            GROUP BY service
        """)
        service_stats = await cursor.fetchall()
        return service_stats



async def get_total_requests():
    # Получаем общее количество заявок
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total = await cursor.fetchone()
    return total[0] if total else 0



@dp.callback_query(F.data == "admin_show_analytics")
async def show_analytics(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа.")

    # Получаем статистику по заявкам за неделю
    weekly_stats = await get_weekly_stats()
    total_requests = await get_total_requests()

    # Формируем текст статистики
    stats_text = f"📊 <b>Статистика заявок:</b>\n\n"
    stats_text += f"Всего заявок: {total_requests}\n\n"
    stats_text += "<b>Заявки за последнюю неделю:</b>\n"

    if not weekly_stats:
        stats_text += "Нет заявок за последнюю неделю."
    else:
        for service, count in weekly_stats:
            stats_text += f"🔹 {service}: {count} заявок\n"

    await callback.message.answer(stats_text)


@dp.callback_query(F.data == "admin_change_status")
async def choose_user(callback: CallbackQuery):
    # Получаем все заявки
    requests = await get_all_requests()

    if not requests:
        return await callback.answer("Заявок пока нет.")

    # Создаем список кнопок
    keyboard = []
    for req_id, user_id, service, status, created_at, status_changed_at in requests:
        # Пропускаем пользователей с выполненным статусом
        if status == "Выполнен":
            continue

        keyboard.append([
            InlineKeyboardButton(
                text=f"ID: {req_id} — {service}",
                callback_data=f"admin_change_status_user:{user_id}"  # Перенаправляем на выбор пользователя
            )
        ])

    if not keyboard:
        return await callback.answer("Нет пользователей с заявками, статус которых можно изменить.")

    # Создаем клавиатуру с параметром inline_keyboard
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.answer("Выберите пользователя для изменения статуса:", reply_markup=markup)



@dp.callback_query(F.data.startswith("admin_change_status_user:"))
async def choose_status_for_user(callback: CallbackQuery):
    # Извлекаем ID выбранного пользователя
    user_id = callback.data.split(":")[1]

    # Отправляем администратору меню для выбора статуса
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Принят", callback_data=f"admin_change_status:{user_id}:Принят"),
        InlineKeyboardButton(text="Выполняется", callback_data=f"admin_change_status:{user_id}:Выполняется"),
        InlineKeyboardButton(text="Выполнен", callback_data=f"admin_change_status:{user_id}:Выполнен"),
    ]])

    await callback.message.answer(f"Выберите новый статус для пользователя с ID {user_id}:", reply_markup=markup)


@dp.callback_query(F.data.startswith("admin_change_status:"))
async def admin_set_status(callback: CallbackQuery):
    try:
        # Получаем ID пользователя и новый статус
        parts = callback.data.split(":")
        user_id = parts[1]
        status = parts[2]
    except IndexError:
        return await callback.answer("Ошибка данных.")

    if not await is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа.")

    # Обновляем статус заявки в базе данных
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET status = ?, status_changed_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (status, user_id))
        await db.commit()

    await callback.message.answer(f"Статус пользователя с ID {user_id} изменен на: {status}")

    # Если статус "Выполнен", можно отправить запрос на отзыв
    if status == "Выполнен":
        await notify_user_for_review(user_id)


async def notify_user_for_review(user_id: int):
    # Отправляем пользователю сообщение с запросом на отзыв
    await bot.send_message(
        user_id,
        "Ваш заказ был выполнен! Пожалуйста, оцените нашу работу от 1 до 5 и оставьте отзыв.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оценить", callback_data="give_review")]
        ])
    )

@dp.message(~F.text.startswith("/"))
async def handle_text_input(message: Message):
    state = admin_states.get(message.from_user.id)

    if state == "waiting_rating":
        try:
            rating = int(message.text)
            if rating < 1 or rating > 5:
                return await message.answer("❌ Оценка должна быть от 1 до 5.")
            admin_states[message.from_user.id] = {"state": "waiting_review", "rating": rating}
            return await message.answer("Теперь, пожалуйста, оставьте отзыв о выполненной работе.")
        except ValueError:
            return await message.answer("❌ Пожалуйста, введите число от 1 до 5.")

    elif isinstance(state, dict) and state.get("state") == "waiting_review":
        review = message.text
        rating = state["rating"]
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET review = ?, rating = ? WHERE telegram_id = ?", (review, rating, message.from_user.id))
                await db.commit()
            await message.answer("Спасибо за ваш отзыв! Мы ценим ваше мнение.")
        except Exception as e:
            await message.answer(f"❌ Ошибка при сохранении отзыва: {e}")
        await send_main_menu(message.from_user.id, "🔙 Вы вернулись в главное меню.")
        admin_states.pop(message.from_user.id, None)

    elif state == "awaiting_user_id":
        try:
            target_id = int(message.text)
            link_btn = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Открыть диалог", url=f"tg://user?id={target_id}")]
            ])
            await message.answer(f"Вот ссылка для диалога с <code>{target_id}</code>:", reply_markup=link_btn)
        except ValueError:
            await message.answer("❌ Неверный формат. Введите числовой ID.")
        finally:
            admin_states.pop(message.from_user.id, None)
            await send_main_menu(message.from_user.id, "✅ Возвращаюсь в главное меню.")

    else:
        await message.answer("⚠️ Неизвестная команда или сообщение.")



@dp.callback_query(F.data == "give_review")
async def give_review(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    await callback.message.answer("Пожалуйста, поставьте оценку от 1 до 5.")

    # Переводим пользователя в состояние ожидания оценки
    admin_states[user_id] = "waiting_rating"


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await send_main_menu(callback.from_user.id, "🔙 Вы вернулись в главное меню.")


@dp.callback_query(F.data == "admin_write_user")
async def admin_write_user(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа.")

    admin_states[callback.from_user.id] = "awaiting_user_id"
    await callback.message.answer("Введите <b>ID пользователя</b>, которому хотите написать:")

@dp.message(~F.text.startswith("/"))
async def handle_admin_input(message: Message):
    state = admin_states.get(message.from_user.id)
    if state == "awaiting_user_id":
        try:
            target_id = int(message.text)
            link_btn = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Открыть диалог", url=f"tg://user?id={target_id}")]
            ])
            await message.answer(f"Вот ссылка для диалога с <code>{target_id}</code>:", reply_markup=link_btn)
        except ValueError:
            await message.answer("❌ Неверный формат. Введите числовой ID.")
        finally:
            admin_states.pop(message.from_user.id, None)
    await send_main_menu(message.from_user.id, "✅ Возвращаюсь в главное меню.")


@dp.message(F.text.startswith("/addadmin"))
async def cmd_add_admin(message: Message):
    if message.from_user.id != 570201599:  # Замените на свой ID
        return await message.answer("Только главный админ может добавлять других админов.")

    try:
        # Разделяем сообщение на команду и аргумент
        parts = message.text.split()
        if len(parts) != 2:  # Если аргумента нет
            return await message.answer("⚠️ Используйте: /addadmin <user_id>")

        _, user_id = parts
        user_id = int(user_id)  # Преобразуем в int, если это возможно

        # Добавляем администратора
        await add_admin(user_id)
        await message.answer(f"✅ Пользователь {user_id} теперь админ.")

    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Ошибка: {e}")
        await message.answer(f"⚠️ Произошла ошибка при добавлении администратора. Ошибка: {e}")




async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
