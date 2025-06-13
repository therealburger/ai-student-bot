import os
import logging
import httpx

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import DefaultBotProperties, Message, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from dotenv import load_dotenv

from docx import Document

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация бота и FastAPI
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# Команда /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Я AI-помощник. Напиши тему, и я сгенерирую реферат в .docx!")

# Обработка сообщений
@dp.message(F.text)
async def handle_text(message: Message):
    try:
        # Отправка запроса в OpenRouter
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "mistralai/mistral-7b-instruct",  # Популярная бесплатная модель
            "messages": [
                {"role": "system", "content": "Сгенерируй краткий студенческий реферат на тему."},
                {"role": "user", "content": message.text}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

        result = response.json()
        if "choices" not in result:
            logger.error(f"Ошибка OpenRouter: {result}")
            await message.answer("Ошибка генерации. Попробуй позже.")
            return

        content = result["choices"][0]["message"]["content"]

        # Сохраняем результат в файл .docx
        file_path = f"/tmp/ref_{message.from_user.id}.docx"
        document = Document()
        document.add_heading(message.text, 0)
        document.add_paragraph(content)
        document.save(file_path)

        # Отправляем пользователю файл
        await message.answer_document(FSInputFile(file_path), caption="Вот твой реферат 🎓")

    except Exception as e:
        logger.exception("Ошибка при генерации или отправке файла")
        await message.answer("Произошла ошибка. Попробуй позже.")

# Установка webhook
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Обработка запросов от Telegram
@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = bot.session.telegram_object_decoder.decode(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception("Ошибка при обработке обновления")
    return {"ok": True}

