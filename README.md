# ROOM 01 Telegram Mini App — starter

Starter project includes:
- Telegram bot that opens the Mini App
- responsive dark Mini App UI
- FastAPI backend
- SQLite bookings and overlap checks
- basic admin API endpoint protected by a token

## Run locally

Use Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `BOT_TOKEN`, `WEBAPP_URL`, and other settings in `.env`.

Start API:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

Host `web/` on a public HTTPS static host, then set `WEBAPP_URL` to that HTTPS page.
In `web/app.js`, set `const API = "https://YOUR-API-DOMAIN";` before deploying.
Start the Telegram bot in a second terminal:
```bash
python bot.py
```

## Important security / production work still required

This is a development scaffold, NOT ready to take real payments or grant access:
1. Validate Telegram `initData` signature on the server. Current API accepts a browser-supplied Telegram ID for demonstration; this is insecure for production.
2. Add user authentication middleware and derive user ID only from validated `initData`.
3. Configure CORS for only the actual Mini App domain.
4. Integrate Platega using its current official merchant documentation. Do not trust client-side payment status; verify payment server-side / webhook.
5. Integrate a specific compatible lock model only after confirming its API and safe exit/manual override.
6. Add cancellation/refund policy, privacy notice, rate limiting, logs, backups, monitoring, timezone rules, and tests.
7. Protect and expand admin operations; never expose `ADMIN_TOKEN` in frontend code.
8. Test edge cases and concurrency before taking bookings.

The API creates a booking with `pending` status. It intentionally does not pretend that payment or smart-lock integration exists.
