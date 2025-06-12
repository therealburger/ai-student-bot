import openai
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from fastapi import FastAPI, Request
from config import TELEGRAM_TOKEN, OPENAI_API_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# Создание бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Настройка вебхука
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if WEBHOOK_URL:
    WEBHOOK_URL += WEBHOOK_PATH
else:
    raise ValueError("❌ Переменная окружения WEBHOOK_URL не установлена!")

# FastAPI приложение
app = FastAPI()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("👋 Привет! Я AI-помощник для студентов. Задай мне вопрос по учёбе!")

@dp.message_handler()
async def ask(message: types.Message):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.reply(response.choices[0].message.content)
    except Exception as e:
        await message.reply("⚠️ Произошла ошибка при обработке запроса.")
        logging.error(f"OpenAI error: {e}")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        update = types.Update.to_object(data)
        await dp.process_update(update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Ошибка обработки обновления: {e}")
        return {"ok": False, "error": str(e)}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook установлен на {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("🛑 Webhook удалён")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
