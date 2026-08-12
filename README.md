# Product Stock Finder Telegram Bot

A Telegram bot that monitors e-commerce URLs (including shortened links) and alerts you when out-of-stock products become available again. It runs in the cloud or locally, and uniquely uses a pinned Telegram message to save your tracked URLs—meaning you don't need a database and the config survives bot restarts!

## Features
- **Stock Tracking:** Automatically checks product pages for "In Stock" / "Out of Stock" status.
- **Dynamic Intervals:** Set your own checking interval and delay between checks to avoid IP bans.
- **Numbered Tracking List:** Easily untrack links using their serial number.
- **Link Unshortening:** Resolves redirect links (e.g. bit.ly, amzn.to) to check the real product page.
- **No Database Needed:** Saves settings directly in your Telegram chat as a pinned message.

## Setup Instructions

1. Clone or download this repository.
2. Run `pip install -r requirements.txt`.
3. Create a `.env` file with your Telegram API credentials:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_USER_ID=your_telegram_id
   ```
4. Run `python bot.py`.

## Bot Commands

- `/track <url>`: Track a new product link.
- `/untrack <id>`: Stop tracking a link using its ID.
- `/list`: See all tracked URLs and their statuses.
- `/check <url>`: Test a link instantly without saving it.
- `/set_interval <minutes>`: Set the background check loop interval.
- `/set_delay <seconds>`: Set the delay between each URL check.

## How It Works
The bot uses a combination of structured data checking (Schema.org JSON-LD and meta tags) and heuristic text matching (e.g., looking for "Out of stock", "Sold out" on the page) to determine availability. It uses `cloudscraper` to bypass basic bot protections.
