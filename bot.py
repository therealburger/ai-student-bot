import os
import logging
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile, Update
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from docx import Document
from pptx import Presentation

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "👋 Привет! Я AI-помощник студентов.\n\n"
        "📄 Реферат: `реферат: тема`\n"
        "📊 Презентация: `презентация: тема`\n"
        "🧮 Задача: просто напиши её!"
    )

@dp.message()
async def handle_message(message: Message):
    try:
        text = message.text.lower()

        if text.startswith("реферат:"):
            prompt = text.split("реферат:", 1)[1].strip()
            await generate_docx(message, prompt)

        elif text.startswith("презентация:"):
            prompt = text.split("презентация:", 1)[1].strip()
            await generate_pptx(message, prompt)

        else:
            await generate_answer_as_pptx(message, message.text)

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await message.answer("❌ Ошибка при обработке запроса.")

async def generate_answer_as_pptx(message: Message, prompt: str):
    try:
        content = await ask_openrouter(prompt)
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Ответ на вопрос"
        slide.placeholders[1].text = content.strip()

        filename = f"/tmp/answer_{message.chat.id}.pptx"
        prs.save(filename)

        await message.answer("📎 Ответ сгенерирован в формате презентации:")
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)

    except Exception as e:
        logger.error(f"Ошибка генерации ответа-презентации: {e}")
        await message.answer("❌ Ошибка при генерации ответа.")

async def generate_docx(message: Message, prompt: str):
    try:
        content = await ask_openrouter(f"Напиши подробный реферат на тему: {prompt}")
        doc = Document()
        doc.add_heading(f"Реферат: {prompt}", 0)
        doc.add_paragraph(content)

        filename = f"/tmp/ref_{message.chat.id}.docx"
        doc.save(filename)

        await message.answer("📎 Отправляю реферат .docx:")
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)

    except Exception as e:
        logger.error(f"Ошибка при генерации реферата: {e}")
        await message.answer("❌ Ошибка при генерации реферата.")

async def generate_pptx(message: Message, prompt: str):
    try:
        content = await ask_openrouter(
            f"Создай презентацию по теме: {prompt}. Формат: Слайд 1: Заголовок - Текст. Один слайд на строку."
        )

        prs = Presentation()
        for line in content.split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                title = parts[0].strip()
                body = parts[1].strip()
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = title
                slide.placeholders[1].text = body

        filename = f"/tmp/ppt_{message.chat.id}.pptx"
        prs.save(filename)

        await message.answer("📎 Отправляю презентацию .pptx:")
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)

    except Exception as e:
        logger.error(f"Ошибка при генерации презентации: {e}")
        await message.answer("❌ Ошибка при генерации презентации.")

async def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    result = response.json()
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Ошибка OpenRouter: {result}")

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
