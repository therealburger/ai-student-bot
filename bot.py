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

bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(bot)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

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
    await message.reply("Привет! Я AI-помощник для студентов. Задай мне вопрос.")

@dp.message_handler()
async def handle_message(message: types.Message):
    try:
        chat_completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text},
            ]
        )
        await message.reply(chat_completion.choices[0].message.content)
    except OpenAIError as e:
        logger.error(f"OpenAI error: {e}")
        await message.reply("Произошла ошибка при обработке запроса.")

