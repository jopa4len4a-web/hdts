"""ROOM 01: Telegram bot + Mini App web server."""
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
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://roomykt.bothost.tech").rstrip("/")
PORT = int(os.getenv("PORT", "3000"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it in BotHost environment variables.")
if not WEBAPP_URL.startswith("https://"):
    raise RuntimeError("WEBAPP_URL must start with https://")

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    username = (message.from_user.username or "").lstrip("@").lower() if message.from_user else ""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Узнать о ROOM 01", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "ROOM 01 — приватная комната для своей компании в Якутске.\n\n"
        "В мини-приложении можно узнать, что это за место, прочитать правила, "
        "посмотреть условия и перейти к бронированию.",
        reply_markup=keyboard,
    )
    # Admin entry is sent as a separate message only to this Telegram username.
    # The server independently validates Telegram initData before exposing admin APIs.
    if username == "ownerparadoxy":
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Открыть админ-панель", web_app=WebAppInfo(url=WEBAPP_URL + "/admin"))
        ]])
        await message.answer(
            "Администрирование ROOM 01\n"
            "Эта кнопка видна только аккаунту @OwnerParadoxy. Доступ к данным "
            "дополнительно проверяется сервером.",
            reply_markup=admin_keyboard,
        )

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

async def main():
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
