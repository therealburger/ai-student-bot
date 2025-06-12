import os
import logging
import httpx

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from aiogram.filters import CommandStart
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

# Обработка команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я AI-помощник. Задай вопрос или пришли файл/голосовое.")

# Обработка текстовых сообщений
@dp.message(lambda msg: msg.text)
async def ask_ai(message: types.Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": "Ты полезный ассистент для студентов."},
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
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            await message.answer(reply)
        else:
            logger.error(f"Ошибка OpenRouter: {result}")
            await message.answer("Ошибка: не удалось получить ответ от модели.")
    except Exception as e:
        logger.exception("Ошибка при обращении к OpenRouter")
        await message.answer("Произошла ошибка при обработке запроса.")

# Обработка голосовых сообщений
@dp.message(lambda msg: msg.voice)
async def handle_voice(message: types.Message):
    await message.answer("🎙 Обработка голосовых пока в разработке.")

# Обработка изображений
@dp.message(lambda msg: msg.photo)
async def handle_photo(message: types.Message):
    await message.answer("🖼 Обработка изображений в скором времени будет доступна!")

# Обработка документов (файлов)
@dp.message(lambda msg: msg.document)
async def handle_document(message: types.Message):
    await message.answer("📄 Файл получен! Мы скоро научим меня его анализировать.")

# Webhook: запуск при старте
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Webhook: обработка входящих сообщений
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка обновления: {e}")
    return {"ok": True}
