import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.utils.executor import start_webhook
from aiogram.utils.exceptions import TelegramAPIError
from aiogram.dispatcher.filters import CommandStart

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from openai import OpenAI, OpenAIError

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

# Устанавливаем переменную окружения для OpenAI
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(bot)
openai_client = OpenAI()  # Без параметров — использует переменные окружения

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    except TelegramAPIError as e:
        logger.error(f"Failed to set webhook: {e}")

@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    try:
        update = types.Update(**await request.json())
        await dp.process_update(update)
    except Exception as e:
        logger.exception(f"Ошибка обработки обновления: {e}")
    return {"status": "ok"}

@dp.message_handler(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply("\u041f\u0440\u0438\u0432\u0435\u0442! \u042f AI-\u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a \u0434\u043b\u044f \u0441\u0442\u0443\u0434\u0435\u043d\u0442\u043e\u0432. \u0417\u0430\u0434\u0430\u0439 \u043c\u043d\u0435 \u0432\u043e\u043f\u0440\u043e\u0441.")

@dp.message_handler()
async def handle_message(message: types.Message):
    try:
        chat_completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "\u0422\u044b \u043f\u043e\u043b\u0435\u0437\u043d\u044b\u0439 AI-\u0430\u0441\u0441\u0438\u0441\u0442\u0435\u043d\u0442 \u0434\u043b\u044f \u0441\u0442\u0443\u0434\u0435\u043d\u0442\u043e\u0432."},
                {"role": "user", "content": message.text},
            ]
        )
        await message.reply(chat_completion.choices[0].message.content)
    except OpenAIError as e:
        logger.error(f"OpenAI error: {e}")
        await message.reply("\u041f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u043e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0435 \u0437\u0430\u043f\u0440\u043e\u0441\u0430.")

