import os
import logging
import httpx

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, BufferedInputFile
from aiogram.filters import CommandStart
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
FULL_WEBHOOK_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

# ==== OpenRouter.ai ====
async def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openrouter/auto",
        "messages": [
            {"role": "system", "content": "Ты полезный AI-помощник для студентов."},
            {"role": "user", "content": prompt}
        ]
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        result = resp.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenRouter error: {result}")
            return "\u041eшибка: ответ не был получен."

# ==== Handlers ====
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    await message.answer("Привет! Я AI-помощник. Можешь скинуть текст, документ, фото или голос.")

@dp.message(F.document)
async def handle_doc(message: types.Message, bot: Bot):
    doc = message.document
    if doc.mime_type == "text/plain":
        file = await bot.download(doc)
        text = file.read().decode("utf-8")
        reply = await ask_openrouter(text)
        await message.answer(reply)
    else:
        await message.answer("Пока читаю только .txt файлы")

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer("Пока разбор голосовых не реализован. Скоро добавим!")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer("Обработка изображений в разработке.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    reply = await ask_openrouter(message.text)
    await message.answer(reply)

# ==== FastAPI integration ====
@app.on_event("startup")
async def startup():
    await bot.set_webhook(FULL_WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {FULL_WEBHOOK_URL}")

@app.post(WEBHOOK_PATH)
async def on_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Ошибка в вебхуке: {e}")
    return {"ok": True}
