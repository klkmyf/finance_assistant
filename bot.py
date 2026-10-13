import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()
from main.models import UserProfile
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI

app = FastAPI() 
@app.get("/")
def read_root():
    return {"status": "working"}


load_dotenv() 
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = "https://72tg3sx7-8000.euw.devtunnels.ms/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user, created = await asyncio.to_thread(
        UserProfile.objects.get_or_create,
        telegram_id=message.from_user.id,
        defaults={'username': message.from_user.username}
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Начать",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])

    if created:
        text = f"Привет, {message.from_user.first_name}! Я твой ИИ-ассистент по финансам. Профиль успешно создан!\n\nНажми на кнопку ниже, чтобы начать:"
    else:
        text = f"Рад видеть тебя снова, {message.from_user.first_name}!\n\nНажми на кнопку ниже, чтобы открыть свои финансы:"

    await message.answer(text, reply_markup=keyboard)

async def main():
    print("Бот успешно запущен и готов к работе")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
