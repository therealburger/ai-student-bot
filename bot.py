import os
import logging
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, FSInputFile
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from docx import Document
from tempfile import NamedTemporaryFile

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Логгирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Бот и диспетчер
bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# FastAPI
app = FastAPI()

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я AI-помощник. Напиши вопрос или запрос на реферат:\n\n<code>реферат: Экология</code>")

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    try:
        if message.text.lower().startswith("реферат:"):
            topic = message.text.split(":", 1)[1].strip()
            await message.answer(f"✍️ Генерирую реферат по теме: <b>{topic}</b>")

            # Запрос к OpenRouter
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "mistralai/mixtral-8x7b",
                "messages": [
                    {"role": "system", "content": "Ты помощник, пишущий студенческие рефераты."},
                    {"role": "user", "content": f"Напиши реферат на тему: {topic}. Введение, основная часть, заключение. Примерно 500 слов."}
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data
                )

            result = response.json()
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]

                # Генерация файла .docx
                doc = Document()
                doc.add_heading(f'Реферат: {topic}', level=1)
                doc.add_paragraph(content)

                with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    doc.save(tmp.name)
                    await message.answer_document(FSInputFile(tmp.name), caption="📄 Вот ваш реферат")

            else:
                logger.error(f"Ошибка OpenRouter: {result}")
                await message.answer("⚠️ Не удалось сгенерировать реферат.")
        else:
            # Стандартный AI-ответ
            await ask_ai(message)
    except Exception as e:
        logger.exception("Ошибка при обработке запроса")
        await message.answer("⚠️ Произошла ошибка при генерации ответа.")

# Стандартный ответ ИИ
async def ask_ai(message: types.Message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "mistralai/mixtral-8x7b",
            "messages": [
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )

        result = response.json()
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            await message.answer(reply)
        else:
            logger.error(f"Ошибка OpenRouter: {result}")
            await message.answer("⚠️ Не удалось получить ответ от модели.")
    except Exception as e:
        logger.exception("Ошибка обращения к OpenRouter")
        await message.answer("⚠️ Произошла ошибка при обработке запроса.")

# Установка вебхука при старте
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

# Приём обновлений через вебхук
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка обновления: {e}")
    return {"ok": True}
