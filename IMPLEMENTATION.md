# 🛠️ Implementation Guide & Architecture

This document explains how the **Product Stock Finder Bot** works under the hood. If you want to modify the code or understand how it bypasses the limits of free cloud hosting, read on!

## Architecture Overview

The bot uses the `Telethon` Python library to communicate with the Telegram API and `cloudscraper` combined with `BeautifulSoup` to scrape e-commerce websites.

1. **The Bot Client**: Connects to Telegram as your *Bot* (using the Bot Token). This client listens to your chat window, handles the slash commands (`/track`, `/list`), and sends push notifications to your phone when an item is back in stock.
2. **The Web Scraper**: An asynchronous background loop (`stock_checker_loop`) that periodically fetches the HTML of your tracked product URLs.

---

## ☁️ The "Ephemeral Storage" Problem (And Solution)

### The Problem
Free cloud providers (like Render) use **Ephemeral File Systems**. This means every time they restart your app (which can happen daily), they wipe the hard drive clean and re-download your code from GitHub. 

If we used a standard `config.json` file to save your tracked URLs locally, all your tracked links would be deleted every single day.

### The Solution: Telegram-Native Storage
Instead of saving settings to a file or requiring you to set up a database (like MongoDB or PostgreSQL), the bot uses Telegram itself as the database!

**How it works:**
1. When the bot starts, it makes a lightweight HTTP request directly to the Telegram Bot API (`getChat` endpoint) to fetch the **pinned message** in your private chat.
2. If the pinned message contains `#CONFIG_DATA`, it locates the brackets `{` and `}` to extract the raw JSON data (bypassing any Markdown formatting stripped by Telegram) and loads your tracked URLs into memory.
3. Every time you track a new URL, untrack an old one, or the bot updates the `last_checked` timestamp, it simply edits this pinned message with the new JSON data.

This clever architecture means your data is safely backed up to Telegram's cloud forever, 100% for free, without needing external database providers.

---

## 🕷️ Scraping Strategy

E-commerce websites use many different formats to indicate if an item is in stock. To make the bot work on as many sites as possible without needing custom scrapers for each one, it checks availability in the following order:

1. **JSON-LD Schema (Most Reliable)**: The bot looks for `<script type="application/ld+json">` tags containing a `Product` and `Offer` schema. This is the industry standard for e-commerce SEO. Platforms like Shopify explicitly declare `schema.org/InStock` or `schema.org/OutOfStock` in this hidden data.
2. **Meta Tags**: The bot looks for `<meta property="og:availability">` or `<meta property="product:availability">`.
3. **Text Heuristics (Fallback)**: If structured data is completely missing, the bot strips away the scripts/styling and searches the visible HTML text for common phrases like "Out of stock", "Sold out", or "Currently unavailable". 
4. **Cloudscraper**: To prevent e-commerce sites from immediately blocking the bot, it uses the `cloudscraper` library which mimics a real Chrome desktop browser to bypass basic anti-bot protections.
