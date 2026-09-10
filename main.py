import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database
from checkers import LinkChecker
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
BOT_TOKEN = "8926241222:AAF5YC7PfWayyalFIYixS53-OkSW1rVQFlA"

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

# Временное хранилище для ожидания ответа "да/нет"
pending_reservations = {}

# Приветственное сообщение
WELCOME_MESSAGE = """
👋 Привет! Я бот для бронирования клиентов.

📋 Как пользоваться:
1. Отправь мне ссылку на клиента
2. Я проверю, свободен ли он
3. Если свободен - предложу забронировать
4. Если занят - покажу, кем

🔗 Поддерживаемые платформы:
• YouTube каналы
• Instagram профили
• Telegram каналы
• Telegram профили

Отправь ссылку на клиента:
"""

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("✅ Веб-сервер запущен на порту 10000")

# ===== ОБРАБОТЧИКИ БОТА =====

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(WELCOME_MESSAGE)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(WELCOME_MESSAGE)

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    clients = db.get_all_clients()
    if not clients:
        await message.answer("📊 Пока нет забронированных клиентов")
        return
    
    stats = f"📊 Статистика бронирований:\n\n"
    for client in clients:
        status = "🔴 Занят" if client[4] else "🟢 Свободен"
        stats += f"• {client[2]} ({client[1]}) - {status}\n"
        if client[4]:
            stats += f"  Забронирован: @{client[4]}\n"
    
    await message.answer(stats)

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_username = message.from_user.username or f"user{user_id}"
    user_url = f"https://t.me/{user_username}" if message.from_user.username else f"tg://user?id={user_id}"
    
    if user_id in pending_reservations:
        answer = message.text.lower().strip()
        if answer in ['да', 'yes', 'y', '1', 'подтвердить']:
            client_data = pending_reservations[user_id]
            success = db.reserve_client(
                client_data['platform'],
                client_data['username'],
                user_username,
                user_url
            )
            if success:
                await message.answer(
                    f"✅ Готово! Клиент записан за тобой.\n\n"
                    f"Можешь отправить следующего."
                )
            else:
                await message.answer("❌ Не удалось забронировать клиента. Возможно, его уже заняли.")
            
            del pending_reservations[user_id]
        elif answer in ['нет', 'no', 'n', '0', 'отмена']:
            del pending_reservations[user_id]
            await message.answer("👌 Ок, можешь отправить другого клиента.")
        else:
            await message.answer("Пожалуйста, ответьте 'да' или 'нет'")
        return
    
    url = message.text.strip()
    
    async with LinkChecker() as checker:
        platform = checker.identify_platform(url)
        
        if not platform:
            await message.answer(
                "❌ Не удалось определить платформу.\n"
                "Пожалуйста, отправьте ссылку на:\n"
                "• YouTube канал\n"
                "• Instagram профиль\n"
                "• Telegram канал или профиль\n"
                "• Или username в формате @username"
            )
            return
        
        exists = False
        username = None
        
        if platform == 'youtube':
            exists, username = await checker.check_youtube_channel(url)
        elif platform == 'instagram':
            exists, username = await checker.check_instagram_profile(url)
        elif platform == 'telegram':
            exists, username = await checker.check_telegram(url)
        
        if not exists or not username:
            await message.answer(
                "❌ Не удалось определить клиента. Проверьте правильность ссылки."
            )
            return
        
        client_record = db.check_client(platform, username)
        
        if client_record and client_record[4]:
            if client_record[4] == user_username:
                await message.answer(
                    f"🔴 Этот клиент уже занят <b>вами</b>.\n\nОтправь другого клиента.",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"🔴 Этот клиент уже занят @{client_record[4]}.\n\nОтправь другого клиента."
                )
        elif client_record and not client_record[4]:
            pending_reservations[user_id] = {
                'platform': platform,
                'username': username,
                'url': url
            }
            
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(text="✅ Да, забронировать", callback_data=f"reserve_{user_id}"))
            keyboard.add(InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{user_id}"))
            
            await message.answer(
                f"🟢 Этот клиент свободен!\n\n"
                f"📋 Клиент: {url}\n"
                f"🔗 Платформа: {platform}\n\n"
                f"Хотите забронировать?",
                reply_markup=keyboard.as_markup()
            )
        else:
            db.add_client(platform, username, url)
            
            pending_reservations[user_id] = {
                'platform': platform,
                'username': username,
                'url': url
            }
            
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(text="✅ Да, забронировать", callback_data=f"reserve_{user_id}"))
            keyboard.add(InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{user_id}"))
            
            await message.answer(
                f"🟢 Этот клиент свободен!\n\n"
                f"📋 Клиент: {url}\n"
                f"🔗 Платформа: {platform}\n\n"
                f"Хотите забронировать?",
                reply_markup=keyboard.as_markup()
            )

@dp.callback_query()
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data.startswith("reserve_"):
        if int(data.split("_")[1]) == user_id and user_id in pending_reservations:
            client_data = pending_reservations[user_id]
            user_username = callback_query.from_user.username or f"user{user_id}"
            user_url = f"https://t.me/{user_username}" if callback_query.from_user.username else f"tg://user?id={user_id}"
            
            success = db.reserve_client(
                client_data['platform'],
                client_data['username'],
                user_username,
                user_url
            )
            
            if success:
                await callback_query.message.edit_text(
                    f"✅ Готово! Клиент записан за тобой.\n\n"
                    f"Можешь отправить следующего."
                )
            else:
                await callback_query.message.edit_text("❌ Не удалось забронировать клиента. Возможно, его уже заняли.")
            
            del pending_reservations[user_id]
            await callback_query.answer()
        else:
            await callback_query.answer("❌ Это не ваша кнопка!", show_alert=True)
    
    elif data.startswith("cancel_"):
        if int(data.split("_")[1]) == user_id and user_id in pending_reservations:
            del pending_reservations[user_id]
            await callback_query.message.edit_text("👌 Ок, можешь отправить другого клиента.")
            await callback_query.answer()
        else:
            await callback_query.answer("❌ Это не ваша кнопка!", show_alert=True)

# ===== ЗАПУСК =====

async def main():
    print("🤖 Запускаю веб-сервер...")
    await start_web_server()
    print("✅ Веб-сервер запущен!")
    print("🤖 Запускаю бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
