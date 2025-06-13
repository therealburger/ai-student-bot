import os
import logging
import httpx
import tempfile

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from docx import Document
from pptx import Presentation

# === Загрузка переменных окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# === Логи ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# === Бот и FastAPI ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# === Команда /start ===
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я AI-помощник.\n\n"
                         "📄 Генерирую рефераты (.docx)\n"
                         "📊 Презентации (.pptx)\n"
                         "🧮 Решаю задачи и вопросы\n"
                         "Просто отправь запрос!")

# === Обработка сообщений ===
@dp.message()
async def handle_message(message: types.Message):
    try:
        user_input = message.text.lower()

        if "реферат" in user_input:
            await generate_docx(message, user_input)
        elif "презентац" in user_input:
            await generate_pptx(message, user_input)
        else:
            await generate_answer(message, user_input)

    except Exception as e:
        logger.exception("Ошибка обработки сообщения")
        await message.answer("Произошла ошибка. Попробуйте позже.")

# === Генерация текста через OpenRouter ===
async def ask_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mixtral-8x7b",
        "messages": [
            {"role": "system", "content": "Ты полезный AI-помощник, генерируешь тексты, рефераты и презентации."},
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Ошибка OpenRouter: {result}")

# === Ответ в чате ===
async def generate_answer(message, prompt):
    reply = await ask_openrouter(prompt)
    await message.answer(reply)

# === Генерация DOCX (реферата) ===
async def generate_docx(message, prompt):
    content = await ask_openrouter(f"Напиши подробный реферат на тему: {prompt}")
    doc = Document()
    doc.add_heading("Реферат", 0)
    for paragraph in content.split('\n'):
        doc.add_paragraph(paragraph)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        doc.save(tmp.name)
        file = FSInputFile(tmp.name, filename="referat.docx")
        await message.answer_document(file)

# === Генерация PPTX (презентации) ===
async def generate_pptx(message, prompt):
    content = await ask_openrouter(f"Создай структуру презентации на тему: {prompt}")
    slides = [s.strip() for s in content.split('\n') if s.strip()]

    prs = Presentation()
    for slide_text in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title, *body = slide_text.split(":")
        slide.shapes.title.text = title.strip()
        slide.placeholders[1].text = ":".join(body).strip() if body else ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        prs.save(tmp.name)
        file = FSInputFile(tmp.name, filename="presentation.pptx")
        await message.answer_document(file)

# === FastAPI startup ===
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# === Webhook endpoint ===
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка обновления: {e}")
    return {"ok": True}
