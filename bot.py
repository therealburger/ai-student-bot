import openai
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from fastapi import FastAPI, Request
from config import TELEGRAM_TOKEN, OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

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
        await message.reply("⚠️ Ошибка при обращении к OpenAI.")
        print(f"OpenAI error: {e}")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = types.Update.to_object(data)
    await dp.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен на {WEBHOOK_URL}")
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from fastapi import FastAPI, Request
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL")

if not WEBHOOK_HOST:
    raise RuntimeError("Переменная окружения WEBHOOK_URL не установлена")

WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
app = FastAPI()
openai = OpenAI(api_key=OPENAI_KEY)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = types.Update.to_object(data)
    await dp.process_update(update)
    return {"ok": True}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("👋 Привет! Я AI-помощник для студентов. Задай мне вопрос по учёбе!")

@dp.message_handler()
async def handle_message(message: types.Message):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message.text}]
    )
    await message.answer(response.choices[0].message.content)

if __name__ == '__main__':
    import uvicorn
    print(f"[i] Вебхук ожидается по адресу: {WEBHOOK_PATH}")
    print(f"[i] Полный WEBHOOK_URL: {WEBHOOK_URL}")
    uvicorn.run(app, host="0.0.0.0", port=10000)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
