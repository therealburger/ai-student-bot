import os
import logging
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, Update
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from docx import Document
from pptx import Presentation
from dotenv import load_dotenv
import tempfile

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not all([BOT_TOKEN, OPENROUTER_API_KEY, WEBHOOK_URL]):
    raise RuntimeError("❌ BOT_TOKEN, OPENROUTER_API_KEY или WEBHOOK_URL не заданы")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# Стартовая команда
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Я бот-помощник для студентов.\n\n📄 Рефераты — напиши: `реферат: тема`\n📊 Презентации — напиши: `презентация: тема`\n🧮 Решение задач — просто отправь формулировку!")

# Основной обработчик
@dp.message(F.text)
async def handle_message(message: Message):
    text = message.text.strip().lower()

    try:
        if text.startswith("реферат:"):
            topic = message.text.split(":", 1)[1].strip()
            await generate_docx(message, topic)

        elif text.startswith("презентация:"):
            topic = message.text.split(":", 1)[1].strip()
            await generate_pptx(message, topic)

        else:
            await generate_answer(message, message.text.strip())

    except Exception as e:
        logger.exception("Ошибка обработки сообщения")
        await message.answer("Произошла ошибка при обработке. Попробуйте позже.")

# Генерация текста через OpenRouter
async def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "Ты помощник для студентов. Пиши ясно и по делу."},
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    result = response.json()
    return result["choices"][0]["message"]["content"] if "choices" in result else "❌ Ошибка генерации."

# Генерация реферата
async def generate_docx(message: Message, topic: str):
    content = await ask_openrouter(f"Напиши подробный реферат на тему: {topic}")

    document = Document()
    document.add_heading(f"Реферат: {topic}", 0)
    document.add_paragraph(content)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        document.save(tmp.name)
        await message.answer_document(FSInputFile(tmp.name, filename="referat.docx"))

# Генерация презентации
async def generate_pptx(message: Message, topic: str):
    outline = await ask_openrouter(f"Составь план презентации на тему: {topic}. Используй 5-7 пунктов.")
    points = outline.split('\n')
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]

    for point in points:
        if not point.strip():
            continue
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = topic
        slide.placeholders[1].text = point.strip()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        prs.save(tmp.name)
        await message.answer_document(FSInputFile(tmp.name, filename="presentation.pptx"))

# Ответ на обычный запрос
async def generate_answer(message: Message, user_input: str):
    reply = await ask_openrouter(user_input)
    # Telegram limit: 4096 chars
    if len(reply) > 4000:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp.write(reply.encode("utf-8"))
            tmp.flush()
            await message.answer_document(FSInputFile(tmp.name, filename="response.txt"))
    else:
        await message.answer(reply)

# Webhook: установка
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Webhook: приём обновлений
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка обновления: {e}")
    return {"ok": True}
