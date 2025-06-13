import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, FSInputFile, Update
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import httpx
from docx import Document

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set")
if not OPENROUTER_API_KEY:
    raise RuntimeError("❌ OPENROUTER_API_KEY is not set")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# /start
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("👋 Привет! Напиши тему — и я отправлю тебе реферат в файле.")

# Генерация текста через OpenRouter
async def generate_text(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/cinematika-7b",  # Замените при необходимости
        "messages": [
            {"role": "system", "content": "Ты помощник студентов. Пиши полные ответы."},
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Ошибка OpenRouter: {result}")
            return None

# Обработка обычных сообщений
@dp.message(F.text)
async def handle_message(message: Message):
    await message.answer("⏳ Генерирую реферат...")

    topic = message.text.strip()
    content = await generate_text(topic)

    if not content:
        await message.answer("⚠️ Ошибка генерации текста.")
        return

    # Генерация .docx
    filename = f"ref_{message.from_user.id}.docx"
    doc = Document()
    doc.add_heading(topic, 0)
    doc.add_paragraph(content)
    filepath = f"/tmp/{filename}"
    doc.save(filepath)

    await message.answer_document(FSInputFile(filepath, filename=filename))

# Webhook
@app.on_event("startup")
async def startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
    return {"ok": True}


