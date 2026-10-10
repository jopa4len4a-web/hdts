"""Combined BotHost entrypoint: Telegram bot + Mini App web server."""
import asyncio
import os
import threading
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv
from server import app

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://roomykt.bothost.tech")
PORT = int(os.getenv("PORT", "3000"))
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it in BotHost environment variables.")
if not WEBAPP_URL.startswith("https://"):
    raise RuntimeError("WEBAPP_URL must start with https://")

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть ROOM 01", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "ROOM 01 — бронирование приватной комнаты.\nОткрой мини-приложение, чтобы выбрать дату и время.",
        reply_markup=keyboard,
    )

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

async def main():
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
