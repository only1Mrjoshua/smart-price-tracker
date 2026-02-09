# Smart E-Commerce Price Tracker & Deal Notifier (MVP)

This MVP tracks product prices across:

- Jumia
- Konga
- Amazon
- eBay

It stores price history, shows a 6-month trend chart, and sends email + in-app notifications when alerts trigger.

## Important limitations (Ethical + Practical)

- Scraping is **best-effort** and may fail due to anti-bot measures, layout changes, or Terms of Service.
- This MVP uses **direct URL tracking** as the primary mode (most reliable).
- If access appears blocked or parsing fails, the product is marked `blocked` and retried later.
- The app checks `robots.txt` and will not fetch pages disallowed for the bot user-agent.

## Tech stack

- Frontend: HTML + CSS + Vanilla JS
- Backend: FastAPI
- DB: MongoDB
- Scheduler: APScheduler (runs inside FastAPI)
- HTTP: httpx
- Parsing: BeautifulSoup4
- Auth: JWT
- Email: SMTP

## Setup

### 1) Start MongoDB

Make sure MongoDB is running locally or update `MONGO_URI`.

### 2) Backend

```bash
cd smart-price-tracker
python -m venv .venv
# Windows:
# .venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Create .env from example
# (If you use python-dotenv in your own environment, load it in your shell)
# For this MVP, export env vars or set them in your OS.
```
