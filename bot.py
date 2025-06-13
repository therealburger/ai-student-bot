import os
import logging
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, Update
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from docx import Document
from pptx import Presentation

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

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Я AI-помощник студентов!\n\n📄 Напиши тему реферата, презентации или вопрос — и я помогу!")

# Генерация ответа от AI
async def ask_ai(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "Ты AI-помощник студентов."},
            {"role": "user", "content": prompt}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()
        return result["choices"][0]["message"]["content"] if "choices" in result else "❌ Ошибка генерации ответа."

# Генерация DOCX
def create_docx(content: str, filename: str = "essay.docx") -> str:
    path = f"/tmp/{filename}"
    doc = Document()
    doc.add_paragraph(content)
    doc.save(path)
    return path

# Генерация PPTX
def create_pptx(content: str, filename: str = "presentation.pptx") -> str:
    path = f"/tmp/{filename}"
    prs = Presentation()
    for slide_text in content.split("\n\n"):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_text.strip().split("\n")[0][:50]
        slide.placeholders[1].text = "\n".join(slide_text.strip().split("\n")[1:])
    prs.save(path)
    return path

# Обработка сообщений
@dp.message(F.text)
async def handle_text(message: Message):
    user_input = message.text.lower()

    if "реферат" in user_input:
        await message.answer("✍️ Пишу реферат...")
        content = await ask_ai(f"Напиши реферат на тему: {message.text}")
        path = create_docx(content)
        await message.answer_document(FSInputFile(path), caption="📄 Реферат готов!")

    elif "презентация" in user_input:
        await message.answer("🧑‍🏫 Готовлю презентацию...")
        content = await ask_ai(f"Создай структуру и текст слайдов презентации по теме: {message.text}")
        path = create_pptx(content)
        await message.answer_document(FSInputFile(path), caption="📊 Презентация готова!")

    elif "задача" in user_input or "реши" in user_input:
        await message.answer("🧮 Решаю задачу...")
        answer = await ask_ai(f"Реши задачу: {message.text}")
        await message.answer(answer)

    else:
        await message.answer("🔍 Думаю...")
        answer = await ask_ai(message.text)
        await message.answer(answer)

# Webhook
@app.on_event("startup")
async def startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
