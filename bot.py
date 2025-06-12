import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import CommandStart
from aiogram.utils.exceptions import TelegramAPIError
from fastapi import FastAPI, Request
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

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
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.process_update(update)
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
    return {"status": "ok"}


@dp.message_handler(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привет! Я AI-помощник для студентов. Задай мне вопрос.")


@dp.message_handler()
async def ask_mistral(message: types.Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

        data = response.json()

        if "choices" in data:
            reply = data["choices"][0]["message"]["content"]
        else:
            reply = "Ошибка: не удалось получить ответ от модели."

        await message.reply(reply)

    except Exception as e:
        logger.error(f"Ошибка OpenRouter: {e}")
        await message.reply("Произошла ошибка при обращении к ИИ. Попробуй позже.")
