import os
import logging
import httpx

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# FastAPI
app = FastAPI()

# Кнопки
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📚 Получить материалы", callback_data="materials")],
    [InlineKeyboardButton(text="🔄 Поделиться ботом", switch_inline_query="")],
    [InlineKeyboardButton(text="💳 Подписка скоро", callback_data="subscribe")],
])

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я AI-помощник для студентов 🎓\n\n"
        "❓ Задавай мне вопросы\n📎 Получай материалы\n💬 Делись с друзьями\n\n"
        "⬇️ Выбери действие ниже:",
        reply_markup=menu_keyboard
    )

# Получить материалы (PDF)
@dp.callback_query(F.data == "materials")
async def send_materials(callback: types.CallbackQuery):
    await callback.answer()
    file_path = "materials/sample_essay.pdf"
    doc = FSInputFile(file_path, filename="Реферат.pdf")
    await callback.message.answer_document(
        doc, caption="📎 Вот пример реферата. Скоро будет больше материалов!"
    )

# Подписка (заглушка)
@dp.callback_query(F.data == "subscribe")
async def subscribe_soon(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("💳 Подписка появится скоро! Пока пользуйся ботом бесплатно.")

# Обработка текстов — AI-ответ
@dp.message()
async def ask_ai(message: types.Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openrouter/openchat-3.5-0106",
            "messages": [
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )

        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        await message.answer(reply)

    except Exception as e:
        logger.exception(f"Ошибка OpenRouter: {e}")
        await message.answer("❌ Ошибка: не удалось получить ответ от модели.")

# Webhook: установка
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Webhook: входящие обновления
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка обновления: {e}")
    return {"ok": True}
