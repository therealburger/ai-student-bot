import os
import logging
import httpx
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, Update
from aiogram.filters import CommandStart
from docx import Document
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я AI-помощник. Напиши запрос, например: Реферат на тему: Глобальное потепление")

@dp.message()
async def handle_message(message: types.Message):
    try:
        if message.text.lower().startswith("реферат на тему:"):
            topic = message.text.split(":", 1)[-1].strip()
            content = await generate_essay(topic)
            file_path = f"/tmp/essay_{message.from_user.id}.docx"
            save_to_docx(content, file_path)
            await message.answer_document(FSInputFile(file_path), caption=f"Реферат на тему: {topic}")
        else:
            await message.answer("Пожалуйста, напиши: Реферат на тему: [тема]")
    except Exception as e:
        logger.exception("Ошибка при обработке запроса")
        await message.answer("Произошла ошибка при обработке запроса.")

def save_to_docx(text: str, file_path: str):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(file_path)

async def generate_essay(topic: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "Ты пишешь студенческие рефераты."},
            {"role": "user", "content": f"Напиши подробный реферат на тему: {topic}. Размер — около 2 страниц."}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()
        return result["choices"][0]["message"]["content"]

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception("Ошибка обработки обновления")
    return {"ok": True}
