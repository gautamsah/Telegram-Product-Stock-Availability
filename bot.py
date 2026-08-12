"""
bot.py — Product Stock Finder Bot
──────────────────────────────────────────────────────────────────
Monitors URLs for product availability and notifies you when items come back in stock.
Stores configuration in a pinned Telegram message.
"""

import os
import sys
import json
import asyncio
import logging
import re
import time
from datetime import datetime
import threading

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    from telethon import TelegramClient, events
    from telethon.tl.types import BotCommand, BotCommandScopeDefault
    from telethon.tl.functions.bots import SetBotCommandsRequest
    from dotenv import load_dotenv
    from colorama import Fore, Style, init as colorama_init
    from bs4 import BeautifulSoup
    import cloudscraper
except ImportError:
    print("\n[!] Missing dependencies. Run:\n    pip install -r requirements.txt\n")
    sys.exit(1)

# ── Init ──────────────────────────────────────────────────────────────────────
colorama_init(autoreset=True)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ── Global State ──────────────────────────────────────────────────────────────
ACTIVE_CONFIG = {
    "urls": [],
    "settings": {
        "check_interval_minutes": 10,
        "delay_seconds": 5,
        "auto_clean": True
    },
    "next_id": 1
}
CONFIG_MSG_ID = None

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        logger.error(f"Missing environment variable: {key}")
        sys.exit(1)
    return val

# ── Web Scraping Logic ────────────────────────────────────────────────────────
def check_stock_sync(url: str) -> str:
    """Synchronous function to check stock using cloudscraper."""
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        resp = scraper.get(url, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Check JSON-LD Structured Data
        for script in soup.find_all('script', type='application/ld+json'):
            if not script.string: continue
            try:
                data = json.loads(script.string)
                # Ensure it's a list or dict
                if isinstance(data, dict):
                    data = [data]
                
                for item in data:
                    if item.get('@type') == 'Product':
                        offers = item.get('offers')
                        if isinstance(offers, dict):
                            offers = [offers]
                        if isinstance(offers, list):
                            for offer in offers:
                                avail = offer.get('availability', '')
                                if 'OutOfStock' in avail:
                                    return "out_of_stock"
                                elif 'InStock' in avail:
                                    return "in_stock"
            except json.JSONDecodeError:
                pass
                
        # 2. Check Meta tags
        meta_avail = soup.find('meta', property='og:availability') or soup.find('meta', property='product:availability')
        if meta_avail and meta_avail.get('content'):
            val = meta_avail['content'].lower()
            if 'out of stock' in val or 'outofstock' in val:
                return "out_of_stock"
            elif 'in stock' in val or 'instock' in val:
                return "in_stock"
                
        # 3. Heuristic Text Search
        # Strip script and style tags for clean text search
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True).lower()
        
        out_of_stock_phrases = [
            "out of stock",
            "sold out",
            "currently unavailable",
            "this item is currently out of stock",
            "not available"
        ]
        
        for phrase in out_of_stock_phrases:
            if phrase in text:
                return "out_of_stock"
                
        # If no out of stock markers are found, assume in stock (or unknown)
        return "in_stock"
        
    except Exception as e:
        logger.error(f"Error checking {url}: {e}")
        return "error"

async def check_stock(url: str) -> str:
    """Wrapper to run the synchronous scraper in a separate thread to avoid blocking asyncio."""
    return await asyncio.to_thread(check_stock_sync, url)

# ── Config Management (Telegram Native Storage) ───────────────────────────────

async def load_or_create_config(bot_client: TelegramClient, user_id: int):
    """Search the bot chat history for the #CONFIG_DATA message, or create it."""
    global ACTIVE_CONFIG, CONFIG_MSG_ID
    logger.info("Looking for existing config in bot chat...")
    
    try:
        async for msg in bot_client.iter_messages(user_id):
            if msg.out and msg.text and "#CONFIG_DATA" in msg.text:
                try:
                    json_str = msg.text.split("```json")[1].split("```")[0].strip()
                    ACTIVE_CONFIG = json.loads(json_str)
                    CONFIG_MSG_ID = msg.id
                    
                    # Ensure next_id exists
                    if "next_id" not in ACTIVE_CONFIG:
                        max_id = max([u.get("id", 0) for u in ACTIVE_CONFIG.get("urls", [])], default=0)
                        ACTIVE_CONFIG["next_id"] = max_id + 1
                        
                    logger.info("Loaded config from Telegram chat history!")
                    return
                except Exception as e:
                    logger.warning(f"Found config message but couldn't parse it: {e}")
    except Exception as e:
        logger.warning(f"Could not fetch history: {e}")
        
    logger.info("No config found in chat. Creating a new pinned config message...")
    await save_config(bot_client, user_id)

async def save_config(bot_client: TelegramClient, user_id: int):
    """Save the ACTIVE_CONFIG back to the Telegram chat as an edited message."""
    global CONFIG_MSG_ID
    
    json_str = json.dumps(ACTIVE_CONFIG, indent=2, ensure_ascii=False)
    text = (
        "⚙️ **Bot Configuration Data** ⚙️\n"
        "_(Do not delete this message! The bot uses it to remember your tracked URLs.)_\n\n"
        "#CONFIG_DATA\n"
        "```json\n"
        f"{json_str}\n"
        "```"
    )
    
    if CONFIG_MSG_ID:
        try:
            await bot_client.edit_message(user_id, CONFIG_MSG_ID, text)
        except Exception as e:
            logger.error(f"Failed to edit config msg, sending new one: {e}")
            CONFIG_MSG_ID = None
            
    if not CONFIG_MSG_ID:
        msg = await bot_client.send_message(user_id, text)
        CONFIG_MSG_ID = msg.id
        try:
            await bot_client.pin_message(user_id, msg.id, notify=False)
        except Exception:
            pass

# ── Background Task ───────────────────────────────────────────────────────────

async def stock_checker_loop(bot_client: TelegramClient, user_id: int):
    """Periodically checks all tracked URLs for stock changes."""
    await asyncio.sleep(10) # Initial delay
    
    while True:
        urls = ACTIVE_CONFIG.get("urls", [])
        interval = ACTIVE_CONFIG["settings"].get("check_interval_minutes", 10)
        delay = ACTIVE_CONFIG["settings"].get("delay_seconds", 5)
        
        if not urls:
            await asyncio.sleep(60)
            continue
            
        logger.info(f"Starting stock check loop for {len(urls)} URLs...")
        
        changed = False
        for u_obj in urls:
            url = u_obj["url"]
            last_status = u_obj.get("status")
            
            logger.info(f"Checking {url}...")
            current_status = await check_stock(url)
            
            # If it transitioned to in stock!
            if current_status == "in_stock" and last_status == "out_of_stock":
                msg = (
                    f"🎉 **PRODUCT IN STOCK!** 🎉\n\n"
                    f"🔗 [Click here to buy]({url})\n\n"
                    f"ID: {u_obj['id']}"
                )
                await bot_client.send_message(user_id, msg, link_preview=False)
            
            if current_status != "error" and current_status != last_status:
                u_obj["status"] = current_status
                u_obj["last_checked"] = datetime.now().isoformat()
                changed = True
            
            # Sleep between requests to avoid bans
            await asyncio.sleep(delay)
            
        if changed:
            await save_config(bot_client, user_id)
            
        # Wait for the next interval
        await asyncio.sleep(interval * 60)

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print(Fore.CYAN + "Starting Product Stock Finder Bot..." + Style.RESET_ALL)

    api_id     = int(get_env("TELEGRAM_API_ID"))
    api_hash   = get_env("TELEGRAM_API_HASH")
    bot_token  = get_env("TELEGRAM_BOT_TOKEN")
    user_id    = int(get_env("TELEGRAM_USER_ID"))
    
    bot_client = TelegramClient("bot_session", api_id, api_hash)
    await bot_client.start(bot_token=bot_token)
    bot_me = await bot_client.get_me()
    logger.info(f"Bot Client connected as @{bot_me.username}.")
    
    try:
        commands = [
            BotCommand(command="track", description="Track a URL"),
            BotCommand(command="untrack", description="Stop tracking by ID"),
            BotCommand(command="list", description="List tracked URLs"),
            BotCommand(command="check", description="Test a URL instantly"),
            BotCommand(command="set_interval", description="Set check interval (mins)"),
            BotCommand(command="set_delay", description="Set delay between checks (secs)"),
            BotCommand(command="help", description="Show help"),
        ]
        await bot_client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='',
            commands=commands
        ))
    except Exception as e:
        logger.warning(f"Failed to register slash commands menu: {e}")

    await load_or_create_config(bot_client, user_id)
    
    # ── Command Handlers ──────────────────────────────────────────────────────

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/start$|^/help$"))
    async def cmd_help(event):
        text = (
            "🤖 **Product Stock Finder Bot**\n\n"
            "Track URLs and get notified when they are back in stock.\n\n"
            "➕ **/track <url>** — Track a new product link\n"
            "➖ **/untrack <id>** — Stop tracking a link by its ID\n"
            "📋 **/list** — View all tracked links and their statuses\n"
            "🔍 **/check <url>** — Instantly check a link without tracking it\n"
            "⏱️ **/set_interval <mins>** — Set background check interval\n"
            "⏳ **/set_delay <secs>** — Set delay between checking each link\n"
        )
        await event.reply(text)

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/track (?P<url>.+)"))
    async def cmd_track(event):
        url = event.pattern_match.group("url").strip()
        if not url.startswith("http"):
            url = "https://" + url
            
        uid = ACTIVE_CONFIG["next_id"]
        ACTIVE_CONFIG["next_id"] += 1
        
        # Initial check to get status
        await event.reply(f"🔍 Checking initial status for ID {uid}...")
        status = await check_stock(url)
        
        ACTIVE_CONFIG["urls"].append({
            "id": uid,
            "url": url,
            "status": status,
            "added_at": datetime.now().isoformat(),
            "last_checked": datetime.now().isoformat()
        })
        
        await save_config(bot_client, user_id)
        
        status_emoji = "🟢" if status == "in_stock" else "🔴" if status == "out_of_stock" else "⚠️"
        await event.reply(f"✅ Now tracking ID **{uid}**!\nCurrent Status: {status_emoji} `{status}`")

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/untrack (?P<id>\d+)"))
    async def cmd_untrack(event):
        uid = int(event.pattern_match.group("id"))
        
        initial_len = len(ACTIVE_CONFIG["urls"])
        ACTIVE_CONFIG["urls"] = [u for u in ACTIVE_CONFIG["urls"] if u["id"] != uid]
        
        if len(ACTIVE_CONFIG["urls"]) < initial_len:
            await save_config(bot_client, user_id)
            await event.reply(f"✅ Untracked ID **{uid}**.")
        else:
            await event.reply(f"❌ Could not find ID **{uid}** in tracking list.")

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/list$"))
    async def cmd_list(event):
        urls = ACTIVE_CONFIG.get("urls", [])
        if not urls:
            await event.reply("📋 You are not tracking any URLs right now.")
            return
            
        text = "📋 **Tracked URLs:**\n\n"
        for u in urls:
            status = u.get("status", "unknown")
            status_emoji = "🟢" if status == "in_stock" else "🔴" if status == "out_of_stock" else "⚠️"
            
            # Truncate URL if too long
            url_str = u["url"]
            if len(url_str) > 50:
                url_str = url_str[:47] + "..."
                
            text += f"**ID {u['id']}** {status_emoji}\n🔗 {url_str}\n\n"
            
        await event.reply(text, link_preview=False)

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/check (?P<url>.+)"))
    async def cmd_check(event):
        url = event.pattern_match.group("url").strip()
        if not url.startswith("http"):
            url = "https://" + url
            
        await event.reply(f"🔍 Testing URL (Not saving to config)...")
        status = await check_stock(url)
        status_emoji = "🟢" if status == "in_stock" else "🔴" if status == "out_of_stock" else "⚠️"
        
        await event.reply(f"Result: {status_emoji} `{status}`")

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/set_interval (?P<mins>\d+)"))
    async def cmd_set_interval(event):
        mins = int(event.pattern_match.group("mins"))
        if mins < 1: mins = 1
        
        ACTIVE_CONFIG["settings"]["check_interval_minutes"] = mins
        await save_config(bot_client, user_id)
        await event.reply(f"⏱️ Check interval updated to **{mins} minutes**.")

    @bot_client.on(events.NewMessage(chats=[user_id], pattern=r"^/set_delay (?P<secs>\d+)"))
    async def cmd_set_delay(event):
        secs = int(event.pattern_match.group("secs"))
        if secs < 0: secs = 0
        
        ACTIVE_CONFIG["settings"]["delay_seconds"] = secs
        await save_config(bot_client, user_id)
        await event.reply(f"⏳ Delay between checks updated to **{secs} seconds**.")


    # ── Run Background Loops ──────────────
    print(Fore.GREEN + "\nBot is online and ready!" + Style.RESET_ALL)
    print("Send /help to your bot in Telegram to get started.\n")
    
    # Render requires a web server to bind to the PORT environment variable
    from aiohttp import web
    async def health_check(request):
        return web.Response(text="Bot is running!")
    
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    asyncio.create_task(stock_checker_loop(bot_client, user_id))
    
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
