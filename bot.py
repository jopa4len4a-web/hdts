import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in .env")
if not WEBAPP_URL.startswith("https://"):
    raise RuntimeError("WEBAPP_URL must be a public HTTPS URL for Telegram Mini Apps")

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть ROOM 01", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "ROOM 01 — бронирование приватной комнаты.\n"
        "Открой мини-приложение, чтобы выбрать дату и время.",
        reply_markup=keyboard
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
