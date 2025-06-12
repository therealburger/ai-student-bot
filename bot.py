import os
import logging
import httpx

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, Message
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise RuntimeError("❌ WEBHOOK_URL is not set")
if not OPENROUTER_API_KEY:
    raise RuntimeError("❌ OPENROUTER_API_KEY is not set")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Бот и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# FastAPI
app = FastAPI()

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Я AI-помощник. Задай вопрос или отправь файл!")

# Обработка текстовых сообщений
@dp.message(lambda msg: msg.text)
async def ask_ai(message: Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": "Ты полезный AI-помощник для студентов."},
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
            await message.answer("⚠️ Ошибка: не удалось получить ответ от модели.")
    except Exception as e:
        logger.exception("Ошибка при запросе к OpenRouter")
        await message.answer("❌ Произошла ошибка при обработке запроса.")

# Запуск webhook
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Обработка обновлений Telegram через FastAPI
@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка при обработке обновления: {e}")
    return {"ok": True}
