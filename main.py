"""ROOM 01: Telegram bot + Mini App web server."""
import asyncio
import logging
import os
import threading
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from dotenv import load_dotenv
from server import app

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("room01")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://roomykt.bothost.tech").rstrip("/")
PORT = int(os.getenv("PORT", "3000"))
BASE_DIR = Path(__file__).resolve().parent
WELCOME_IMAGE = BASE_DIR / "assets" / "room01_welcome.png"

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения BotHost.")
if not WEBAPP_URL.startswith("https://"):
    raise RuntimeError("WEBAPP_URL должен быть публичным HTTPS-адресом.")

bot = Bot(TOKEN)
dp = Dispatcher()

def is_owner(message: Message) -> bool:
    user = message.from_user
    return bool(user and (user.username or "").lstrip("@").casefold() == "ownerparadoxy")

def customer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть ROOM 01",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )],
        [InlineKeyboardButton(
            text="Открыть в браузере",
            url=WEBAPP_URL,
        )],
    ])

def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть админ-панель",
            web_app=WebAppInfo(url=WEBAPP_URL + "/admin"),
        )]
    ])

WELCOME_CAPTION = (
    "ROOM 01 — твоё личное пространство для отдыха.\n\n"
    "Фильмы, игры, музыка или вечер с друзьями — выбирай свой формат "
    "и проводи время без посторонних.\n\n"
    "Здесь можно познакомиться с комнатой, прочитать правила и посмотреть "
    "условия посещения. Бронирование откроется, когда будешь готов.\n\n"
    "Твоё время. Твои правила."
)

@dp.message(CommandStart())
async def start(message: Message):
    try:
        if WELCOME_IMAGE.is_file():
            await message.answer_photo(
                photo=FSInputFile(WELCOME_IMAGE),
                caption=WELCOME_CAPTION,
                reply_markup=customer_keyboard(),
            )
        else:
            await message.answer(WELCOME_CAPTION, reply_markup=customer_keyboard())
    except Exception:
        log.exception("Не удалось отправить приветствие с изображением")
        await message.answer(WELCOME_CAPTION, reply_markup=customer_keyboard())

    # A separate administrator message is sent only to @OwnerParadoxy.
    # The admin API independently verifies Telegram's signed Mini App initData.
    if is_owner(message):
        await message.answer(
            "ROOM 01 · Центр управления\n\n"
            "Административный доступ распознан для @OwnerParadoxy. "
            "Здесь можно управлять заявками и настройками сервиса.",
            reply_markup=admin_keyboard(),
        )

@dp.message(Command("room"))
async def room(message: Message):
    await message.answer(
        "ROOM 01 — приватная комната для фильмов, игр и отдыха своей компанией.\n\n"
        "Открой Mini App, чтобы узнать подробности, прочитать правила и перейти "
        "к выбору даты и времени.",
        reply_markup=customer_keyboard(),
    )

@dp.message(Command("rules"))
async def rules(message: Message):
    await message.answer(
        "Правила ROOM 01\n\n"
        "1. Бережно относись к мебели и оборудованию.\n"
        "2. Соблюдай время начала и окончания визита.\n"
        "3. Не оставляй после себя мусор.\n"
        "4. Не совершай опасных действий и не мешай другим посетителям здания.\n"
        "5. Изменения и отмену заявки согласовывай с администратором.\n\n"
        "Полная версия правил доступна во вкладке «Правила» в Mini App.",
        reply_markup=customer_keyboard(),
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Как пользоваться ROOM 01\n\n"
        "• /start — главное приветствие\n"
        "• /room — о комнате и переход в Mini App\n"
        "• /rules — краткие правила\n"
        "• /help — эта подсказка\n\n"
        "В Mini App можно посмотреть информацию, прочитать правила, выбрать дату "
        "и время, а также проверить свои заявки. Пока онлайн-оплата не подключена, "
        "заявка не считается подтверждённой до ответа администратора.",
        reply_markup=customer_keyboard(),
    )

async def setup_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть ROOM 01"),
        BotCommand(command="room", description="Узнать о комнате"),
        BotCommand(command="rules", description="Правила посещения"),
        BotCommand(command="help", description="Как пользоваться ботом"),
    ])

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

async def main():
    threading.Thread(target=run_web, daemon=True, name="room01-web").start()
    await setup_commands()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
