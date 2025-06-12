import os
import logging
import httpx

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import CommandStart
from fastapi import FastAPI, Request

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    update = types.Update(**await request.json())
    await dp.process_update(update)
    return {"status": "ok"}

@dp.message_handler(CommandStart())
async def cmd_start(message: types.Message):
    await message.reply("Привет! Я AI-помощник. Задай свой вопрос.")

@dp.message_handler()
async def ask_ai(message: types.Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openchat/openchat-3.5-1210",  # Популярная бесплатная модель
            "messages": [
                {"role": "system", "content": "Ты — полезный ассистент для студентов."},
                {"role": "user", "content": message.text}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )

        if response.status_code == 200:
            res = response.json()
            reply = res["choices"][0]["message"]["content"]
            await message.reply(reply)
        else:
            logger.error(f"Ошибка OpenRouter: {response.text}")
            await message.reply("Ошибка: не удалось получить ответ от модели.")
    except Exception as e:
        logger.exception("Произошла ошибка при обращении к модели.")
        await message.reply("Произошла ошибка при обработке запроса.")
