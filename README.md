# N' Kitchens Flask Website

Ready-to-host Flask food ordering website for N' Kitchens.

## Features
- Public menu with cart
- Checkout without customer signup
- Orders saved to SQLite
- Admin login and dashboard
- Order status updates
- Telegram order alerts
- Easy to host on Render, Railway, VPS, or any Python host

## Default admin login
- Username: `admin`
- Password: `admin123`

Change both in `.env` before production.

## Local setup
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open:
- Website: `http://127.0.0.1:5000`
- Admin login: `http://127.0.0.1:5000/admin/login`

## Telegram setup
1. Create a bot with `@BotFather`.
2. Copy the bot token into `TELEGRAM_BOT_TOKEN`.
3. Send one message to your bot from Telegram.
4. Open this in your browser, replacing `YOUR_BOT_TOKEN`:
   `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
5. Find your `chat.id` in the JSON response and place it into `TELEGRAM_CHAT_ID`.
6. Place an order from the site. A Telegram alert should be sent instantly.

## Production notes
- Use PostgreSQL later if you want better scale.
- Change `SECRET_KEY` and admin credentials.
- Replace sample image URLs and WhatsApp/Telegram links.
- For Render/Railway, set the same values from `.env.example` as environment variables.

## Suggested next upgrades
- Delivery fee logic by area
- Customer order tracking page
- Online payments
- Real branded food photos and logo
