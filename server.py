import os
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "room01.sqlite3")
PRICE = int(os.getenv("ROOM_PRICE_PER_HOUR", "1200"))
OPEN_HOUR = int(os.getenv("OPEN_HOUR", "10"))
CLOSE_HOUR = int(os.getenv("CLOSE_HOUR", "23"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-this-admin-token")
app = FastAPI(title="ROOM 01 API")

# Telegram's WebApp initData MUST be validated server-side before production.
# This scaffold deliberately does not trust user IDs sent from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["GET", "POST"], allow_headers=["*"]
)

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS bookings(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          telegram_user_id INTEGER NOT NULL,
          start_at TEXT NOT NULL,
          hours INTEGER NOT NULL,
          total INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS ix_bookings_start ON bookings(start_at,status)")

class BookingRequest(BaseModel):
    telegram_user_id: int = Field(gt=0)
    start_at: datetime
    hours: int = Field(ge=1, le=4)

def overlaps(start, hours, rows):
    end = start + timedelta(hours=hours)
    for r in rows:
        old = datetime.fromisoformat(r["start_at"])
        if start < old + timedelta(hours=r["hours"]) and old < end:
            return True
    return False

@app.on_event("startup")
def startup():
    init_db()

@app.get("/api/config")
def config():
    return {"room_name": "ROOM 01", "price_per_hour": PRICE,
            "open_hour": OPEN_HOUR, "close_hour": CLOSE_HOUR}

@app.get("/api/availability")
def availability(day: str):
    try:
        target = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(400, "Invalid date")
    if target < date.today() or target > date.today() + timedelta(days=30):
        raise HTTPException(400, "Date must be within the next 30 days")
    with db() as c:
        rows = c.execute("""SELECT start_at,hours FROM bookings
            WHERE substr(start_at,1,10)=? AND status IN ('pending','confirmed')""",
            (day,)).fetchall()
    slots = []
    now = datetime.now()
    for h in range(OPEN_HOUR, CLOSE_HOUR):
        start = datetime.combine(target, datetime.min.time()).replace(hour=h)
        for duration in (1, 2, 3, 4):
            end = start + timedelta(hours=duration)
            if end.date() != target or end.hour > CLOSE_HOUR:
                continue
            slots.append({"start_at": start.isoformat(timespec="minutes"),
                          "hours": duration,
                          "available": start > now and not overlaps(start, duration, rows),
                          "total": PRICE * duration})
    return {"day": day, "slots": slots}

@app.post("/api/bookings")
def create_booking(req: BookingRequest):
    start = req.start_at.replace(tzinfo=None, second=0, microsecond=0)
    if start.minute != 0:
        raise HTTPException(400, "Bookings must start on the hour")
    if start <= datetime.now():
        raise HTTPException(400, "Start time must be in the future")
    if start.date() > date.today() + timedelta(days=30):
        raise HTTPException(400, "Bookings open for 30 days ahead")
    if start.hour < OPEN_HOUR or (start + timedelta(hours=req.hours)).date() != start.date() or (start + timedelta(hours=req.hours)).hour > CLOSE_HOUR:
        raise HTTPException(400, "Outside opening hours")
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        rows = c.execute("""SELECT start_at,hours FROM bookings
            WHERE substr(start_at,1,10)=? AND status IN ('pending','confirmed')""",
            (start.date().isoformat(),)).fetchall()
        if overlaps(start, req.hours, rows):
            c.rollback()
            raise HTTPException(409, "That time was just booked")
        cur = c.execute("""INSERT INTO bookings
            (telegram_user_id,start_at,hours,total,status,created_at)
            VALUES(?,?,?,?, 'pending', ?)""",
            (req.telegram_user_id, start.isoformat(timespec="minutes"),
             req.hours, req.hours * PRICE, datetime.now().isoformat(timespec="seconds")))
        booking_id = cur.lastrowid
        c.commit()
    # Payment is intentionally not faked. Integrate Platega after verifying current docs.
    return {"booking_id": booking_id, "status": "pending_payment",
            "start_at": start.isoformat(timespec="minutes"),
            "hours": req.hours, "total": req.hours * PRICE,
            "message": "Booking created. Payment integration is not configured yet."}

@app.get("/api/my-bookings")
def my_bookings(telegram_user_id: int):
    # Demo only: replace this query parameter with a validated Telegram initData identity.
    with db() as c:
        rows = c.execute("""SELECT id,start_at,hours,total,status FROM bookings
            WHERE telegram_user_id=? ORDER BY start_at DESC LIMIT 30""",
            (telegram_user_id,)).fetchall()
    return {"bookings": [dict(r) for r in rows]}

@app.get("/api/admin/bookings")
def admin_bookings(x_admin_token: str = Header(default="")):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")
    with db() as c:
        rows = c.execute("SELECT * FROM bookings ORDER BY start_at DESC LIMIT 200").fetchall()
    return {"bookings": [dict(r) for r in rows]}
