import os
import logging
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Update
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

from docx import Document
from pptx import Presentation

# Загрузка переменных
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REQUIRED_CHANNEL_ID = os.getenv("REQUIRED_CHANNEL_ID")  # @channel_username

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()


# Проверка подписки
async def is_user_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Ошибка при проверке подписки: {e}")
        return False


# Старт
@dp.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я AI-помощник студентов.\n\n"
        "📄 Реферат: `реферат: тема`\n"
        "📊 Презентация: `презентация: тема`\n"
        "🧮 Задача: просто напиши её!"
    )


# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    try:
        # Проверка подписки
        if not await is_user_subscribed(message.from_user.id):
            kb = InlineKeyboardBuilder()
            kb.button(
                text="📢 Подписаться",
                url=f"https://t.me/{REQUIRED_CHANNEL_ID.replace('@', '')}"
            )
            await message.answer("🚫 Для использования бота подпишитесь на наш канал:", reply_markup=kb.as_markup())
            return

        text = message.text.lower()

        if text.startswith("реферат:"):
            prompt = text.split("реферат:", 1)[1].strip()
            await generate_docx(message, prompt)

        elif text.startswith("презентация:"):
            prompt = text.split("презентация:", 1)[1].strip()
            await generate_pptx(message, prompt)

        else:
            await generate_answer(message, text)

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await message.answer("❌ Произошла ошибка.")


# Ответ
async def generate_answer(message: types.Message, prompt: str):
    try:
        response = await ask_openrouter(prompt)
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка ответа: {e}")
        await message.answer("❌ Ошибка генерации ответа.")


# DOCX
async def generate_docx(message: types.Message, prompt: str):
    try:
        content = await ask_openrouter(f"Напиши подробный реферат на тему: {prompt}")
        doc = Document()
        doc.add_heading(f"Реферат: {prompt}", 0)
        doc.add_paragraph(content)

        filename = f"ref_{message.chat.id}.docx"
        doc.save(filename)
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)

    except Exception as e:
        logger.error(f"Ошибка .docx: {e}")
        await message.answer("❌ Ошибка при генерации реферата.")


# PPTX
async def generate_pptx(message: types.Message, prompt: str):
    try:
        content = await ask_openrouter(f"Сделай структуру презентации по теме: {prompt}. Формат: Слайд 1: Заголовок - Описание")
        prs = Presentation()
        for line in content.split("\n"):
            if ":" in line:
                title, body = line.split(":", 1)
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = title.strip()
                slide.placeholders[1].text = body.strip()

        filename = f"ppt_{message.chat.id}.pptx"
        prs.save(filename)
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)

    except Exception as e:
        logger.error(f"Ошибка .pptx: {e}")
        await message.answer("❌ Ошибка при генерации презентации.")


# OpenRouter запрос
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


# Webhook
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
