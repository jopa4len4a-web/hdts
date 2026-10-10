# ROOM 01 — BotHost revision with admin panel

## Files
- `main.py` — starts Telegram bot and FastAPI on the same process
- `server.py` — booking API, SQLite database, Telegram Mini App signature validation, admin API
- `web/` — customer Mini App and `/admin` page
- `Dockerfile` — Python container entry point

## BotHost setup
1. Select Docker deployment if available; do not run `main.py` with Node.js.
2. Set `BOT_TOKEN` to the token from @BotFather.
3. Set `WEBAPP_URL=https://roomykt.bothost.tech`.
4. Set `PORT=3000`.
5. Ensure the container has persistent storage and set `DATA_DIR=/app/data` if supported.
6. Deploy. Check `https://roomykt.bothost.tech/api/health`.
7. Open the Mini App from Telegram, then open `https://roomykt.bothost.tech/admin` inside Telegram to access the admin panel.

## Admin access
The backend verifies Telegram Web App `initData` and permits admin APIs only when the verified username is `@OwnerParadoxy`. Username changes can affect access; for stronger long-term control, add the Telegram numeric user ID to the allowlist as well.

## Important
- The admin panel lets you change room name, hourly price, opening/closing hours, booking statuses, and save Platega merchant/API fields.
- **Saving Platega credentials does not activate payments.** Real payment creation, signed webhook/callback verification, duplicate-event protection, and status transition after verified payment still need to be implemented against current official Platega documentation.
- Smart-lock code generation is not integrated. Do not promise automatic door access until the exact lock model and API are tested.
- Use HTTPS and persistent storage. Do not expose `BOT_TOKEN` or Platega secrets in frontend files or screenshots.
- Do not use the booking/payment workflow with real customers until payment integration, cancellation rules, backups, and timezone behavior have been tested.


## Updated multi-tab customer interface
- Customer `/start` message opens the Mini App introduction.
- Only the Telegram username `@OwnerParadoxy` receives a separate admin-panel message.
- Mini App tabs: About, Booking, Rules, My bookings, Information.
- Booking CTA is presented after the introductory section; the booking tab is still available through navigation.
- Rules and location/contact details are draft content and should be reviewed before accepting real customers.
