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
from pptx import Presentation
from pptx.util import Inches

# === Настройка переменных окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

if not BOT_TOKEN or not OPENROUTER_API_KEY:
    raise RuntimeError("❌ BOT_TOKEN или OPENROUTER_API_KEY не задан")

# === Логирование и инициализация ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# === Генерация текста через OpenRouter ===
async def generate_text(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/cinematika-7b",  # Заменить на актуальную
        "messages": [
            {"role": "system", "content": "Ты умный помощник для студентов."},
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
        return result["choices"][0]["message"]["content"] if "choices" in result else None

# === Генерация реферата в docx ===
def create_docx(title: str, content: str) -> str:
    path = f"/tmp/ref_{title[:20]}.docx"
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    doc.save(path)
    return path

# === Генерация презентации в pptx ===
def create_ppt(title: str, content: str) -> str:
    path = f"/tmp/pres_{title[:20]}.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = content
    prs.save(path)
    return path

# === /start ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Я помощник для студентов.\n\n📌 Напиши тему или вопрос, например:\n— Реферат на тему глобальное потепление\n— Презентация: солнечная система\n— Реши: 2x + 3 = 7")

# === Основная логика ===
@dp.message(F.text)
async def handle_message(message: Message):
    query = message.text.lower().strip()
    await message.answer("🔍 Обрабатываю запрос...")

    if "реферат" in query:
        content = await generate_text(f"Напиши реферат: {query}")
        if not content:
            return await message.answer("❌ Не удалось создать реферат.")
        path = create_docx(query, content)
        await message.answer_document(FSInputFile(path, filename="referat.docx"))

    elif "презентация" in query:
        content = await generate_text(f"Сделай краткую презентацию: {query}")
        if not content:
            return await message.answer("❌ Не удалось создать презентацию.")
        path = create_ppt(query, content)
        await message.answer_document(FSInputFile(path, filename="presentation.pptx"))

    elif "реши" in query or "задача" in query:
        content = await generate_text(f"Реши задачу: {query}")
        await message.answer(content if content else "❌ Не удалось решить задачу.")

    else:
        content = await generate_text(f"Ответь на вопрос: {query}")
        await message.answer(content if content else "❌ Не удалось получить ответ.")

# === Webhook ===
@app.on_event("startup")
async def startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

