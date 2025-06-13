import os
import logging
import httpx
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.types import Message
from fastapi import FastAPI, Request
from docx import Document
from pptx import Presentation
from pptx.util import Inches

# ────────────────────────────────
# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# ────────────────────────────────
# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ────────────────────────────────
# Инициализация бота и FastAPI
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# ────────────────────────────────
# OpenRouter запрос
async def query_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "Ты помощник для студентов, помогаешь с учебой, рефератами, задачами и презентациями."},
            {"role": "user", "content": prompt}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    result = response.json()
    return result["choices"][0]["message"]["content"]

# ────────────────────────────────
# Генерация реферата
def create_docx(text: str, filename: str) -> str:
    doc = Document()
    doc.add_heading("Реферат", level=1)
    for paragraph in text.split("\n"):
        doc.add_paragraph(paragraph.strip())
    path = os.path.join("generated", filename)
    os.makedirs("generated", exist_ok=True)
    doc.save(path)
    return path

# ────────────────────────────────
# Генерация презентации
def create_pptx(text: str, filename: str) -> str:
    prs = Presentation()
    layout = prs.slide_layouts[1]
    slides = [s.strip() for s in text.split("\n\n") if s.strip()]
    for slide_text in slides:
        parts = slide_text.split("\n", 1)
        title = parts[0].strip()
        content = parts[1].strip() if len(parts) > 1 else ""
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = title
        slide.placeholders[1].text = content
    path = os.path.join("generated", filename)
    os.makedirs("generated", exist_ok=True)
    prs.save(path)
    return path

# ────────────────────────────────
# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я бот-помощник студентов 📚\n\n"
                         "📝 /essay <тема> — сгенерировать реферат\n"
                         "📊 /presentation <тема> — сгенерировать презентацию\n"
                         "❓ Просто задай вопрос по учёбе")

@dp.message(Command("essay"))
async def cmd_essay(message: Message):
    topic = message.text.replace("/essay", "").strip()
    if not topic:
        await message.answer("Пожалуйста, укажи тему реферата.")
        return
    await message.answer("✍️ Генерирую реферат...")
    try:
        text = await query_openrouter(f"Напиши подробный реферат на тему: {topic}")
        file_path = create_docx(text, "essay.docx")
        await message.answer_document(FSInputFile(file_path), caption="📄 Вот твой реферат")
    except Exception as e:
        logger.exception("Ошибка генерации реферата")
        await message.answer("Произошла ошибка при создании реферата.")

@dp.message(Command("presentation"))
async def cmd_presentation(message: Message):
    topic = message.text.replace("/presentation", "").strip()
    if not topic:
        await message.answer("Пожалуйста, укажи тему презентации.")
        return
    await message.answer("📊 Генерирую презентацию...")
    try:
        text = await query_openrouter(f"Создай презентацию на тему: {topic}. Каждый слайд: заголовок и краткий текст. Разделяй слайды двойным переносом строки.")
        file_path = create_pptx(text, "presentation.pptx")
        await message.answer_document(FSInputFile(file_path), caption="📊 Вот твоя презентация")
    except Exception as e:
        logger.exception("Ошибка генерации презентации")
        await message.answer("Произошла ошибка при создании презентации.")

# ────────────────────────────────
# Обработка любого сообщения
@dp.message()
async def handle_message(message: Message):
    try:
        await message.answer("💡 Думаю...")
        reply = await query_openrouter(message.text)
        await message.answer(reply)
    except Exception as e:
        logger.exception("Ошибка при ответе на вопрос")
        await message.answer("Ошибка при обработке запроса.")

# ────────────────────────────────
# Webhook запуск
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def on_webhook(request: Request):
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
