import os
import logging
import random
import httpx

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, Update
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties

from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Загрузка .env переменных
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не установлен")
if not OPENROUTER_API_KEY:
    raise RuntimeError("❌ OPENROUTER_API_KEY не установлен")
if not WEBHOOK_URL:
    raise RuntimeError("❌ WEBHOOK_URL не установлен")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Инициализация FastAPI
app = FastAPI()

# 📁 Папка с учебными материалами
MATERIALS_DIR = "materials"
os.makedirs(MATERIALS_DIR, exist_ok=True)

# 👋 /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я AI-помощник. Задай мне вопрос или напиши /material чтобы получить файл 📄")

# 🤖 Запрос к OpenRouter
@dp.message(F.text)
async def ask_ai(message: Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
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
                json=data
            )

        result = response.json()
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            await message.answer(reply)
        else:
            logger.error(f"Ошибка OpenRouter: {result}")
            await message.answer("Ошибка: не удалось получить ответ от модели.")
    except Exception as e:
        logger.exception("Ошибка при обращении к OpenRouter")
        await message.answer("Произошла ошибка при обработке запроса.")

# 📚 /material — отправка файла
@dp.message(F.text.lower() == "/material")
async def send_material(message: Message):
    try:
        files = os.listdir(MATERIALS_DIR)
        if not files:
            await message.answer("🗂️ Пока нет доступных материалов.")
            return

        selected_file = random.choice(files)
        file_path = os.path.join(MATERIALS_DIR, selected_file)

        await message.answer_document(FSInputFile(file_path), caption=f"📚 Вот материал: <b>{selected_file}</b>")
    except Exception as e:
        logger.exception("Ошибка при отправке файла")
        await message.answer("❌ Не удалось отправить материал.")

# Webhook: установка при запуске
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Webhook: при получении обновления
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка обновления: {e}")
    return {"ok": True}
