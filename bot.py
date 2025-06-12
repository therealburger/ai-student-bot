import openai
from aiogram import Bot, Dispatcher, types, executor
from config import TELEGRAM_TOKEN, OPENAI_API_KEY

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("👋 Привет! Я AI-помощник для студентов. Задай мне вопрос по учёбе!")

@dp.message_handler()
async def ask(message: types.Message):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты полезный AI-ассистент для студентов."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.reply(response.choices[0].message.content)
    except Exception as e:
        await message.reply("⚠️ Ошибка при обращении к OpenAI.")
        print(f"OpenAI error: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    executor.start_polling(dp, skip_updates=True)