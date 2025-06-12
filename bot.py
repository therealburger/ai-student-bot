import logging
import os
import httpx

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import CommandStart
from fastapi import FastAPI, Request
from aiogram.utils.exceptions import TelegramAPIError
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
OPENROUTER_API_KEY = "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"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(bot)

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка установки webhook: {e}")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    update = types.Update(**await request.json())
    await dp.process_update(update)
    return {"status": "ok"}

@dp.message_handler(CommandStart())
async def start(message: types.Message):
    await message.reply("Привет! Я AI-помощник студентов. Задай мне вопрос.")

@dp.message_handler()
async def handle_message(message: types.Message):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://ai-student-bot.onrender.com",  # можно свой сайт
                    "X-Title": "AI Student Bot"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct",
                    "messages": [
                        {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                        {"role": "user", "content": message.text}
                    ]
                }
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            await message.reply(content)
    except Exception as e:
        logger.error(f"Ошибка OpenRouter: {e}")
        await message.reply("Произошла ошибка при обработке запроса.")
