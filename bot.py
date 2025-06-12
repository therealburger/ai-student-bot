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

# Загрузка переменных из .env, если локально
load_dotenv()

# Получаем переменные окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_URL")

# Проверка на наличие всех нужных переменных
if not BOT_TOKEN or not OPENAI_API_KEY or not WEBHOOK_BASE_URL:
    raise RuntimeError("Ошибка: TELEGRAM_TOKEN, OPENAI_API_KEY или WEBHOOK_URL не заданы в окружении.")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

# Логгирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(bot)

# OpenAI клиент
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# FastAPI приложение
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    except TelegramAPIError as e:
        logger.error(f"❌ Не удалось установить webhook: {e}")

@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    try:
        update = types.Update(**await request.json())
        await dp.process_update(update)
    except Exception as e:
        logger.exception(f"❌ Ошибка обработки обновления: {e}")
    return {"status": "ok"}

# Обработка команды /start
@dp.message_handler(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я AI-помощник для студентов. Задай мне вопрос.")

# Обработка обычных сообщений
@dp.message_handler()
async def handle_message(message: types.Message):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text},
            ]
        )
        reply_text = response.choices[0].message.content.strip()
        await message.reply(reply_text)
    except OpenAIError as e:
        logger.error(f"OpenAI error: {e}")
        await message.reply("Произошла ошибка при обработке запроса.")
