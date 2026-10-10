import os, sqlite3, hmac, hashlib, json, time
from urllib.parse import parse_qsl
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

TZ = ZoneInfo("Asia/Yakutsk")
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DATA_DIR = BASE_DIR
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "room01.sqlite3"))
PRICE = int(os.getenv("ROOM_PRICE_PER_HOUR", "1200"))
OPEN_HOUR = int(os.getenv("OPEN_HOUR", "10"))
CLOSE_HOUR = int(os.getenv("CLOSE_HOUR", "23"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
app = FastAPI(title="ROOM 01 API")

def db():
    c = sqlite3.connect(DB_PATH, timeout=15)
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
        c.execute("""CREATE TABLE IF NOT EXISTS settings(
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )""")

def telegram_identity(init_data: str) -> dict:
    if not BOT_TOKEN:
        raise HTTPException(503, "Bot token is not configured on the server")
    if not init_data:
        raise HTTPException(401, "Открой Mini App через Telegram")
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", "")
        auth_date = int(pairs.get("auth_date", "0"))
        if not received_hash or time.time() - auth_date > 86400 or auth_date > time.time() + 60:
            raise ValueError("stale auth data")
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise ValueError("bad signature")
        user = json.loads(pairs["user"])
        uid = int(user["id"])
        if uid <= 0:
            raise ValueError("bad user")
        return {"id": uid, "username": str(user.get("username", "")).lstrip("@").lower()}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(401, "Не удалось подтвердить аккаунт Telegram. Закрой и открой Mini App заново.")

def telegram_user_id(init_data: str) -> int:
    return int(telegram_identity(init_data)["id"])

def require_admin(init_data: str) -> dict:
    identity = telegram_identity(init_data)
    if identity["username"] != "ownerparadoxy":
        raise HTTPException(403, "Доступ к админ-панели разрешён только @OwnerParadoxy")
    return identity

def get_setting(key: str, default: str = "") -> str:
    with db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    with db() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, value))
        c.commit()

class BookingRequest(BaseModel):
    init_data: str = Field(min_length=1)
    start_at: datetime
    hours: int = Field(ge=1, le=4)

def now_local():
    return datetime.now(TZ).replace(tzinfo=None, second=0, microsecond=0)

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

@app.get("/api/health")
def health():
    return {"ok": True, "service": "ROOM 01"}

@app.get("/api/config")
def config():
    return {
        "room_name": get_setting("room_name", "ROOM 01"),
        "price_per_hour": int(get_setting("price_per_hour", str(PRICE))),
        "open_hour": int(get_setting("open_hour", str(OPEN_HOUR))),
        "close_hour": int(get_setting("close_hour", str(CLOSE_HOUR))),
    }

@app.get("/api/availability")
def availability(day: str):
    try:
        target = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(400, "Invalid date")
    today = now_local().date()
    if target < today or target > today + timedelta(days=30):
        raise HTTPException(400, "Date must be within the next 30 days")
    with db() as c:
        rows = c.execute("SELECT start_at,hours FROM bookings WHERE substr(start_at,1,10)=? AND status IN ('pending','confirmed')", (day,)).fetchall()
    cfg = config()
    price = cfg["price_per_hour"]
    open_hour = cfg["open_hour"]
    close_hour = cfg["close_hour"]
    slots=[]; now=now_local()
    for h in range(open_hour, close_hour):
        start = datetime.combine(target, datetime.min.time()).replace(hour=h)
        for duration in (1,2,3,4):
            end=start+timedelta(hours=duration)
            if end.date()!=target or end.hour>close_hour: continue
            slots.append({"start_at":start.isoformat(timespec="minutes"), "hours":duration,
                          "available":start>now and not overlaps(start,duration,rows), "total":price*duration})
    return {"day":day,"slots":slots}

@app.post("/api/bookings")
def create_booking(req: BookingRequest):
    uid = telegram_user_id(req.init_data)
    start=req.start_at.replace(tzinfo=None, second=0, microsecond=0)
    now=now_local()
    if start.minute != 0: raise HTTPException(400,"Bookings must start on the hour")
    if start <= now: raise HTTPException(400,"Start time must be in the future")
    if start.date() > now.date()+timedelta(days=30): raise HTTPException(400,"Bookings open for 30 days ahead")
    cfg = config()
    price = cfg["price_per_hour"]
    if start.hour<cfg["open_hour"] or (start+timedelta(hours=req.hours)).date()!=start.date() or (start+timedelta(hours=req.hours)).hour>cfg["close_hour"]:
        raise HTTPException(400,"Outside opening hours")
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        rows=c.execute("SELECT start_at,hours FROM bookings WHERE substr(start_at,1,10)=? AND status IN ('pending','confirmed')",(start.date().isoformat(),)).fetchall()
        if overlaps(start,req.hours,rows):
            c.rollback(); raise HTTPException(409,"Это время уже заняли. Выбери другое.")
        cur=c.execute("INSERT INTO bookings (telegram_user_id,start_at,hours,total,status,created_at) VALUES(?,?,?,?, 'pending', ?)",
                      (uid,start.isoformat(timespec="minutes"),req.hours,req.hours*price,now.isoformat(timespec="seconds")))
        booking_id=cur.lastrowid; c.commit()
    return {"booking_id":booking_id,"status":"pending_payment","start_at":start.isoformat(timespec="minutes"),
            "hours":req.hours,"total":req.hours*price,"message":"Заявка создана. Онлайн-оплата ещё не подключена."}

@app.get("/api/my-bookings")
def my_bookings(x_telegram_init_data: str = Header(default="")):
    uid=telegram_user_id(x_telegram_init_data)
    with db() as c:
        rows=c.execute("SELECT id,start_at,hours,total,status FROM bookings WHERE telegram_user_id=? ORDER BY start_at DESC LIMIT 30",(uid,)).fetchall()
    return {"bookings":[dict(r) for r in rows]}

@app.get("/admin")
def admin_page():
    return FileResponse(str(WEB_DIR / "admin.html"))

@app.get("/api/admin/bookings")
def admin_bookings(init_data: str = Header(default="", alias="X-Telegram-Init-Data")):
    require_admin(init_data)
    with db() as c:
        rows = c.execute("SELECT * FROM bookings ORDER BY start_at DESC LIMIT 300").fetchall()
    return {"bookings": [dict(r) for r in rows]}

class AdminBookingUpdate(BaseModel):
    init_data: str = Field(min_length=1)
    status: str

@app.post("/api/admin/bookings/{booking_id}")
def admin_update_booking(booking_id: int, req: AdminBookingUpdate):
    require_admin(req.init_data)
    if req.status not in ("pending", "confirmed", "cancelled", "completed"):
        raise HTTPException(400, "Недопустимый статус")
    with db() as c:
        cur = c.execute("UPDATE bookings SET status=? WHERE id=?", (req.status, booking_id))
        c.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Бронирование не найдено")
    return {"ok": True}

class AdminSettings(BaseModel):
    init_data: str = Field(min_length=1)
    room_name: str = Field(default="ROOM 01", min_length=1, max_length=60)
    price_per_hour: int = Field(ge=1, le=1000000)
    open_hour: int = Field(ge=0, le=23)
    close_hour: int = Field(ge=1, le=24)
    platega_merchant_id: str = Field(default="", max_length=200)
    platega_secret: str = Field(default="", max_length=500)
    platega_api_url: str = Field(default="", max_length=500)

@app.get("/api/admin/settings")
def admin_get_settings(init_data: str = Header(default="", alias="X-Telegram-Init-Data")):
    require_admin(init_data)
    return {
        "room_name": get_setting("room_name", "ROOM 01"),
        "price_per_hour": int(get_setting("price_per_hour", str(PRICE))),
        "open_hour": int(get_setting("open_hour", str(OPEN_HOUR))),
        "close_hour": int(get_setting("close_hour", str(CLOSE_HOUR))),
        "platega_merchant_id": get_setting("platega_merchant_id", ""),
        "platega_secret_set": bool(get_setting("platega_secret", "")),
        "platega_api_url": get_setting("platega_api_url", ""),
        "payment_integration_status": "not_connected",
    }

@app.post("/api/admin/settings")
def admin_save_settings(req: AdminSettings):
    require_admin(req.init_data)
    if req.close_hour <= req.open_hour:
        raise HTTPException(400, "Время закрытия должно быть позже времени открытия")
    set_setting("room_name", req.room_name)
    set_setting("price_per_hour", str(req.price_per_hour))
    set_setting("open_hour", str(req.open_hour))
    set_setting("close_hour", str(req.close_hour))
    set_setting("platega_merchant_id", req.platega_merchant_id.strip())
    set_setting("platega_api_url", req.platega_api_url.strip())
    # Empty secret means keep the previously saved value.
    if req.platega_secret.strip():
        set_setting("platega_secret", req.platega_secret.strip())
    return {"ok": True, "message": "Настройки сохранены. Оплата не активируется автоматически."}

# Mount frontend after API routes so /api/* remains handled by FastAPI.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
