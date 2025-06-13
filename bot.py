import os
import logging
import httpx
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я AI-помощник для студентов.\n\n"
        "📄 Напиши, что нужно — реферат, презентация или решение задачи.\n"
        "Например:\n"
        "— Реферат на тему «История Интернета»\n"
        "— Презентация по биологии про клетки\n"
        "— Реши уравнение: 2x + 3 = 7"
    )

# Обработка сообщений
@dp.message(F.text)
async def handle_message(message: Message):
    user_input = message.text.lower()

    try:
        if "реферат" in user_input:
            await generate_docx(message, user_input)
        elif "презентация" in user_input:
            await generate_pptx(message, user_input)
        else:
            await generate_answer(message, user_input)
    except Exception as e:
        logger.exception("Ошибка обработки сообщения")
        await message.answer("❌ Произошла ошибка при обработке запроса.")

# Генерация текста через OpenRouter
async def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
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
        return result["choices"][0]["message"]["content"]

# Генерация .docx
async def generate_docx(message: Message, prompt: str):
    await message.answer("✍️ Генерирую реферат...")
    content = await ask_openrouter(prompt)

    doc = Document()
    doc.add_heading('Реферат', 0)
    doc.add_paragraph(content)
    file_path = "ref.docx"
    doc.save(file_path)

    await message.answer_document(FSInputFile(file_path), caption="📄 Готовый реферат")

# Генерация .pptx
async def generate_pptx(message: Message, prompt: str):
    await message.answer("🛠 Генерирую презентацию...")
    content = await ask_openrouter(f"{prompt}. Сделай структуру с пунктами для слайдов.")
    slides = content.split('\n')

    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = "Презентация"
    slide.placeholders[1].text = prompt.capitalize()

    for line in slides:
        if line.strip():
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = line.strip()
            slide.placeholders[1].text = "..."

    file_path = "presentation.pptx"
    prs.save(file_path)
    await message.answer_document(FSInputFile(file_path), caption="📊 Готовая презентация")

# Ответ без файла
async def generate_answer(message: Message, prompt: str):
    await message.answer("🤖 Думаю над ответом...")
    reply = await ask_openrouter(prompt)
    await message.answer(reply)

# Webhook запуск
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
