import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import CommandStart
from aiogram.utils.exceptions import TelegramAPIError
from fastapi import FastAPI, Request
import httpx

from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(bot)

# FastAPI приложение
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка установки webhook: {e}")

@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    try:
        update = types.Update(**await request.json())
        await dp.process_update(update)
    except Exception as e:
        logger.exception(f"Ошибка обработки обновления: {e}")
    return {"status": "ok"}

@dp.message_handler(CommandStart())
async def handle_start(message: types.Message):
    await message.answer("Привет! Я AI-помощник для студентов. Задай мне вопрос.")

@dp.message_handler()
async def handle_question(message: types.Message):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct:free",
                    "messages": [
                        {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                        {"role": "user", "content": message.text}
                    ]
                }
            )
        data = response.json()
        if response.status_code == 200 and "choices" in data:
            reply = data["choices"][0]["message"]["content"]
        else:
            logger.error(f"Ошибка OpenRouter: {data}")
            reply = "Произошла ошибка при обращении к ИИ. Попробуйте позже."

        await message.reply(reply)
    except Exception as e:
        logger.exception(f"Ошибка при обработке сообщения: {e}")
        await message.reply("Произошла ошибка при обработке запроса.")
