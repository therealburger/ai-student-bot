import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.filters import CommandStart
import httpx
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Я AI-помощник для студентов.\n\n"
                         "📄 Реферат: /essay тема\n"
                         "📊 Презентация: /ppt тема\n"
                         "🧠 Вопрос: просто напиши его сообщением")


@dp.message(F.text.startswith("/essay "))
async def generate_essay(message: Message):
    topic = message.text.replace("/essay ", "").strip()
    await message.answer("⏳ Генерирую реферат...")
    try:
        content = await ask_openrouter(f"Напиши подробный реферат на тему: {topic}")
        file_path = f"essay_{message.from_user.id}.docx"
        doc = Document()
        doc.add_heading(f"Реферат: {topic}", 0)
        doc.add_paragraph(content)
        doc.save(file_path)
        await message.answer_document(FSInputFile(file_path))
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Ошибка при генерации реферата: {e}")
        await message.answer("❌ Ошибка при создании реферата.")


@dp.message(F.text.startswith("/ppt "))
async def generate_presentation(message: Message):
    topic = message.text.replace("/ppt ", "").strip()
    await message.answer("⏳ Генерирую презентацию...")
    try:
        content = await ask_openrouter(f"Составь краткий план презентации на тему: {topic}")
        slides = content.split("\n")
        prs = Presentation()
        slide_layout = prs.slide_layouts[1]
        for slide_text in slides:
            slide = prs.slides.add_slide(slide_layout)
            title, body = slide_text.split(":", 1) if ":" in slide_text else ("Слайд", slide_text)
            slide.shapes.title.text = title.strip()
            slide.placeholders[1].text = body.strip()
        file_path = f"presentation_{message.from_user.id}.pptx"
        prs.save(file_path)
        await message.answer_document(FSInputFile(file_path))
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Ошибка при генерации презентации: {e}")
        await message.answer("❌ Ошибка при создании презентации.")


@dp.message()
async def handle_message(message: Message):
    await message.answer("⏳ Думаю над ответом...")
    try:
        reply = await ask_openrouter(message.text)
        await message.answer(reply[:4096])
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await message.answer("❌ Не удалось получить ответ.")


async def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openchat/openchat-3.5-0106",
        "messages": [
            {"role": "system", "content": "Ты полезный AI-ассистент, создающий учебные материалы."},
            {"role": "user", "content": prompt}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    result = response.json()
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    raise Exception(f"Ошибка OpenRouter: {result}")


@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    update = await request.json()
    await dp.feed_raw_update(bot, update)
    return {"ok": True}

