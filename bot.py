import os
import signal
import threading
import time
import logging
import requests
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from datetime import datetime

# ===== CONFIGURATION =====
TOKEN = "8423656357:AAGQYh32Gk-ItGFcFxhd25-hAOxjXT2qQd8"
ADMIN_ID = "7468096294"
API_URL = "https://smmtrustpanel.com/api/v2"
API_KEY = "83c0cf2baddad52503fa7f0e9f81884b"
PORT = int(os.getenv("PORT", 10000))  # Render provides this automatically

# ===== CRYPTO ADDRESSES =====
CRYPTO_ADDRESSES = {
    "USDT-TRC20": "TRNku6CNitDdpjYiM68Sf75H1ZBexUmhub",
    "USDT-BEP20": "0x396cCF7D5a9e967eF243EC3781DfC16065502824",
    "BNB": "0x396cCF7D5a9e967eF243EC3781DfC16065502824",
    "SOL": "HwFVG6oLRB9o7XNUwPeSQA9txWL1fHG2mKxwXTVm3LKD",
    "TRX": "TRNku6CNitDdpjYiM68Sf75H1ZBexUmhub"
}

# ===== SERVICE CONFIGURATION =====
SERVICES = {
    "Telegram Views": {
        "id": 3017,
        "panel_rate": 0.0088,
        "your_rate": 0.02,
        "min": 10,
        "max": 100000,
        "speed": "50K/Day",
        "guarantee": "Non-Drop"
    },
    "Telegram Reactions": {
        "id": 3023,
        "panel_rate": 0.0778,
        "your_rate": 0.07,
        "min": 100,
        "max": 40000,
        "speed": "0-2 Hours",
        "guarantee": "Mixed Reactions"
    },
    "Telegram Members": {
        "id": 3403,
        "panel_rate": 0.5734,
        "your_rate": 1.00,
        "min": 100,
        "max": 50000,
        "speed": "50K/Day",
        "guarantee": "365-Day Refill"
    },
    "Twitter Followers": {
        "id": 3326,
        "panel_rate": 2.6239,
        "your_rate": 3.00,
        "min": 50,
        "max": 5000,
        "speed": "5K/Day",
        "guarantee": "30-Day Refill"
    },
    "Twitter Views": {
        "id": 2538,
        "panel_rate": 0.0292,
        "your_rate": 0.10,
        "min": 100,
        "max": 100000,
        "speed": "Instant",
        "guarantee": "USA Targeted"
    },
    "Twitter Likes": {
        "id": 2568,
        "panel_rate": 0.1847,
        "your_rate": 0.50,
        "min": 50,
        "max": 50000,
        "speed": "0-5 Minutes",
        "guarantee": "No Refill"
    }
}

# ===== STATES =====
(
    CHOOSING_SERVICE, INPUT_QUANTITY, INPUT_LINK, CONFIRM_ORDER,
    DEPOSIT_METHOD, DEPOSIT_AMOUNT, DEPOSIT_TXID, DEPOSIT_CONFIRM
) = range(8)

# ===== DATABASE =====
USERS = {}  # User data storage
PENDING_DEPOSITS = {}  # Pending deposits
DEPOSIT_ID_COUNTER = 1  # Auto-incrementing deposit ID

# ===== LOGGING =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== HEALTH CHECK SERVER =====
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    """Endpoint to keep Render instance alive"""
    return "Øzmain Bot is running", 200

def run_web_server():
    """Run Flask server in separate thread"""
    web_app.run(host='0.0.0.0', port=PORT)

# ===== KEEPALIVE MECHANISM =====
def send_keepalive():
    """Ping ourselves every 10 minutes to prevent sleep"""
    while True:
        try:
            requests.get(f"http://localhost:{PORT}", timeout=5)
            time.sleep(600)  # 10 minutes
        except Exception as e:
            logger.warning(f"Keepalive ping failed: {str(e)}")
            time.sleep(60)

# ===== MAIN MENU =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Initialize user if new
    if user_id not in USERS:
        reg_date = datetime.now().strftime("%Y/%m/%d")
        USERS[user_id] = {"balance": 0.0, "orders": [], "registration_date": reg_date}
    
    buttons = [
        [InlineKeyboardButton("👁 Views", callback_data="service_Telegram Views")],
        [InlineKeyboardButton("👍 Reactions", callback_data="service_Telegram Reactions")],
        [InlineKeyboardButton("👥 Members", callback_data="service_Telegram Members")],
        [InlineKeyboardButton("🐦 Followers", callback_data="service_Twitter Followers")],
        [InlineKeyboardButton("👀 Views", callback_data="service_Twitter Views")],
        [InlineKeyboardButton("❤️ Likes", callback_data="service_Twitter Likes")],
        [
            InlineKeyboardButton("💰 Deposit", callback_data="deposit"),
            InlineKeyboardButton("📜 Orders", callback_data="my_orders")
        ],
        [
            InlineKeyboardButton("👤 Account", callback_data="my_account"),
            InlineKeyboardButton("🆘 Support", callback_data="support")
        ]
    ]

    await update.message.reply_text(
        "Hi, welcome to Øzmain ✋\n\n"
        "With Øzmain it's just a few taps to increase number of views, "
        "likes and votes of your Telegram and Twitter posts.\n\n"
        "To start choose an item:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ===== SERVICE ORDERING =====
async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    buttons = [
        [InlineKeyboardButton("👁 Telegram Views", callback_data="service_Telegram Views")],
        [InlineKeyboardButton("👍 Telegram Reactions", callback_data="service_Telegram Reactions")],
        [InlineKeyboardButton("👥 Telegram Members", callback_data="service_Telegram Members")],
        [InlineKeyboardButton("🐦 Twitter Followers", callback_data="service_Twitter Followers")],
        [InlineKeyboardButton("👀 Twitter Views", callback_data="service_Twitter Views")],
        [InlineKeyboardButton("❤️ Twitter Likes", callback_data="service_Twitter Likes")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
    ]
    
    await query.edit_message_text(
        "📦 *Available Services*\n\nSelect a service:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return CHOOSING_SERVICE

async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    service_name = query.data.split("_", 1)[1]
    context.user_data["service"] = service_name
    service = SERVICES[service_name]
    
    await query.edit_message_text(
        f"📊 *{service_name}*\n\n"
        f"⚡ Speed: {service['speed']}\n"
        f"🛡 Guarantee: {service['guarantee']}\n"
        f"📦 Min: {service['min']} | Max: {service['max']}\n"
        f"💵 Price: ${service['your_rate']} per 1000\n\n"
        "✍️ *Enter quantity:*\n\n"
        "Type /cancel to return to main menu",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
        ])
    )
    return INPUT_QUANTITY

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text)
        service_name = context.user_data["service"]
        service = SERVICES[service_name]
        
        if quantity < service["min"]:
            await update.message.reply_text(f"❗ Minimum order is {service['min']}")
            return INPUT_QUANTITY
        if quantity > service["max"]:
            await update.message.reply_text(f"❗ Maximum order is {service['max']}")
            return INPUT_QUANTITY
            
        context.user_data["quantity"] = quantity
        await update.message.reply_text(
            "🔗 *Now send the target link*\n\n"
            "Examples:\n"
            "Telegram: https://t.me/channel/123\n"
            "Twitter: https://twitter.com/tweet/123\n\n"
            "Type /cancel to return to main menu",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
            ])
        )
        return INPUT_LINK
    except ValueError:
        await update.message.reply_text("❗ Please enter a valid number")
        return INPUT_QUANTITY

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    service_name = context.user_data["service"]
    quantity = context.user_data["quantity"]
    service = SERVICES[service_name]
    
    # Calculate price
    price = round((quantity / 1000) * service["your_rate"], 4)
    context.user_data["price"] = price
    context.user_data["link"] = link
    
    user_id = update.effective_user.id
    balance = USERS[user_id]["balance"]
    
    if balance < price:
        await update.message.reply_text(
            f"❌ Insufficient balance!\n"
            f"Needed: ${price:.4f}\n"
            f"Your balance: ${balance:.4f}\n\n"
            "Please deposit first with /deposit",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ *Order Summary*\n\n"
        f"📦 Service: {service_name}\n"
        f"🔗 Link: {link}\n"
        f"📊 Quantity: {quantity}\n"
        f"💵 Price: ${price:.4f}\n\n"
        "Confirm this order?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm_order")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
        ]),
        parse_mode="Markdown"
    )
    return CONFIRM_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    service_name = context.user_data["service"]
    service = SERVICES[service_name]
    quantity = context.user_data["quantity"]
    link = context.user_data["link"]
    price = context.user_data["price"]
    
    # Deduct balance
    USERS[user_id]["balance"] -= price
    
    try:
        # Call SMM panel API
        params = {
            "key": API_KEY,
            "action": "add",
            "service": service["id"],
            "link": link,
            "quantity": quantity
        }
        response = requests.get(API_URL, params=params, timeout=10).json()
        
        # Save order
        order_id = response["order"]
        USERS[user_id]["orders"].append({
            "id": order_id,
            "service": service_name,
            "quantity": quantity,
            "price": price,
            "status": "Processing"
        })
        
        # Show success message
        await query.edit_message_text(
            f"🎉 *Order Successful!*\n\n"
            f"📦 Service: {service_name}\n"
            f"🆔 Order ID: {order_id}\n"
            f"💵 Charged: ${price:.4f}\n"
            f"💰 Remaining Balance: ${USERS[user_id]['balance']:.4f}\n\n"
            "Returning to main menu...",
            parse_mode="Markdown"
        )
        
        # Return to main menu
        await force_main_menu(update, context)
    except Exception as e:
        # Refund if failed
        USERS[user_id]["balance"] += price
        logger.error(f"Order failed: {str(e)}")
        await query.edit_message_text(
            f"❌ Order Failed!\n\nError: {str(e)}\n\nYour balance has been refunded.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
            ])
        )
    return ConversationHandler.END

# ===== DEPOSIT SYSTEM =====
async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    buttons = [
        [InlineKeyboardButton("USDT-TRC20", callback_data="dep_usdt_trc20")],
        [InlineKeyboardButton("USDT-BEP20", callback_data="dep_usdt_bep20")],
        [InlineKeyboardButton("BNB", callback_data="dep_bnb")],
        [InlineKeyboardButton("SOL", callback_data="dep_sol")],
        [InlineKeyboardButton("TRX", callback_data="dep_trx")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
    ]
    
    await query.edit_message_text(
        "💎 *Select Deposit Method*\n\n"
        "Choose the cryptocurrency you want to use:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return DEPOSIT_METHOD

async def handle_deposit_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method_map = {
        "dep_usdt_trc20": "USDT-TRC20",
        "dep_usdt_bep20": "USDT-BEP20",
        "dep_bnb": "BNB",
        "dep_sol": "SOL",
        "dep_trx": "TRX"
    }
    
    method = method_map[query.data]
    context.user_data["deposit_method"] = method
    
    await query.edit_message_text(
        f"📥 *{method} Deposit Request*\n\n"
        f"💵 How much in USD do you want to deposit?\n\n"
        f"📋 Example: To deposit $10\nType: 10\n\n"
        f"⚠️ Minimum deposit: $0.5",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
        ])
    )
    return DEPOSIT_AMOUNT

async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 0.5:
            await update.message.reply_text("❗ Minimum deposit is $0.5")
            return DEPOSIT_AMOUNT
            
        context.user_data["deposit_amount"] = amount
        method = context.user_data["deposit_method"]
        address = CRYPTO_ADDRESSES[method]
        
        await update.message.reply_text(
            f"🌐 *{method} Deposit Address*\n\n"
            f"`{address}`\n\n"
            f"💵 You can send any amount but make sure it's more than minimum and it's {method}\n\n"
            f"🔗 After sending, provide TXID\n"
            f"❓ Can't find TXID? Type `NONE`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
            ])
        )
        return DEPOSIT_TXID
    except ValueError:
        await update.message.reply_text("❗ Please enter a valid number (e.g., 10 or 10.5)")
        return DEPOSIT_AMOUNT

async def handle_deposit_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = update.message.text
    context.user_data["deposit_txid"] = txid
    method = context.user_data["deposit_method"]
    amount = context.user_data["deposit_amount"]
    
    # Format TXID display
    txid_display = txid if txid.upper() != "NONE" else "NONE (Not provided)"
    
    await update.message.reply_text(
        f"🔍 *Transaction Details*\n\n"
        f"📌 TXID: `{txid_display}`\n"
        f"💎 Type: {method}\n"
        f"💵 USD Amount: ${amount:.2f}\n\n"
        f"✅ Click 'Accept' to confirm",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Accept", callback_data="dep_confirm")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
        ])
    )
    return DEPOSIT_CONFIRM

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # IMMEDIATE VISUAL FEEDBACK (CRITICAL FIX)
    await query.edit_message_text("⏳ Processing your deposit request...")
    
    user_id = query.from_user.id
    method = context.user_data["deposit_method"]
    amount = context.user_data["deposit_amount"]
    txid = context.user_data["deposit_txid"]
    
    # Generate deposit ID
    global DEPOSIT_ID_COUNTER, PENDING_DEPOSITS
    deposit_id = DEPOSIT_ID_COUNTER
    DEPOSIT_ID_COUNTER += 1
    
    # Store pending deposit
    PENDING_DEPOSITS[deposit_id] = {
        "user_id": user_id,
        "amount": amount,
        "currency": method,
        "txid": txid,
        "status": "pending"
    }
    
    # Format TXID for message
    txid_display = txid if txid.upper() != "NONE" else "Not provided"
    
    # Get username for admin notification
    username = query.from_user.username or query.from_user.full_name
    
    # Notify admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 *New Deposit Request*\n\n"
             f"🆔 Deposit ID: `{deposit_id}`\n"
             f"👤 User: @{username} ({user_id})\n"
             f"💵 Amount: ${amount:.2f}\n"
             f"💎 Currency: {method}\n"
             f"📌 TXID: `{txid_display}`\n\n"
             f"To approve: /approve_deposit {deposit_id}",
        parse_mode="Markdown"
    )
    
    # Notify user
    await query.message.reply_text(
        f"⏳ *Deposit Submitted!*\n\n"
        f"Your deposit of ${amount:.2f} in {method} has been submitted.\n"
        f"🆔 Deposit ID: `{deposit_id}`\n\n"
        f"Administrator approval is required. "
        f"You'll be notified when your balance is updated.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
        ])
    )
    
    return ConversationHandler.END

# ===== MY ACCOUNT =====
async def show_my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = USERS.get(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ User data not found. Please use /start to initialize.")
        return
    
    # Count all orders
    num_orders = len(user_data["orders"])
    
    # Format account information
    account_info = (
        f"👤 *My Account*\n\n"
        f"▫️ User ID: `{user_id}`\n"
        f"▫️ Registry date: {user_data['registration_date']}\n"
        f"▫️ Number of orders: {num_orders}\n"
        f"▫️ Balance: ${user_data['balance']:.4f}\n\n"
    )
    
    # Only provide "Main Menu" button
    await query.edit_message_text(
        account_info,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
        ]),
        parse_mode="Markdown"
    )

# ===== ORDER HISTORY =====
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = USERS.get(user_id, {})
    orders = user_data.get("orders", [])
    
    if not orders:
        await query.edit_message_text(
            "📭 You have no orders yet.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
            ])
        )
        return
    
    message = "📋 *Your Last 5 Orders*\n\n"
    for order in orders[-5:]:
        status_icon = "✅" if order.get("status") == "Completed" else "⏳"
        message += (
            f"{status_icon} *{order['service']}*\n"
            f"🆔 ID: {order['id']}\n"
            f"🔢 Qty: {order['quantity']} | 💵 ${order['price']:.4f}\n"
            f"📊 Status: {order.get('status', 'Processing')}\n\n"
        )
    
    await query.edit_message_text(
        message, 
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
        ])
    )

# ===== SUPPORT FUNCTION =====
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Send support message
    await query.edit_message_text(
        "🔰 *Support*\n\n"
        "Please feel free to reach out to our support team, "
        "if you have any questions or issues.\n\n"
        "@DVMAJ",
        parse_mode="Markdown"
    )
    
    # Automatically return to main menu after 5 seconds
    await asyncio.sleep(5)
    await force_main_menu(update, context)
    return ConversationHandler.END

# ===== ADMIN COMMANDS =====
async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized access. This incident will be reported.")
        return
    
    command = update.message.text.split()[0]
    
    if command == "/add_balance":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
            return
        
        try:
            target_user_id = int(context.args[0])
            amount = float(context.args[1])
            
            if target_user_id not in USERS:
                await update.message.reply_text(f"❌ User {target_user_id} not found")
                return
                
            USERS[target_user_id]["balance"] += amount
            await update.message.reply_text(f"✅ Added ${amount:.2f} to user {target_user_id}")
            
            # Notify user
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"💳 *Balance Updated*\n\n"
                     f"An administrator has added ${amount:.2f} to your balance.\n"
                     f"New balance: ${USERS[target_user_id]['balance']:.2f}",
                parse_mode="Markdown"
            )
            
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments. Usage: /add_balance <user_id> <amount>")
    
    elif command == "/pending_deposits":
        if not PENDING_DEPOSITS:
            await update.message.reply_text("ℹ️ No pending deposits")
            return
            
        message = "📋 *Pending Deposits*\n\n"
        for deposit_id, deposit in PENDING_DEPOSITS.items():
            message += (
                f"🆔 Deposit ID: `{deposit_id}`\n"
                f"👤 User: {deposit['user_id']}\n"
                f"💵 Amount: ${deposit['amount']:.2f}\n"
                f"💎 Currency: {deposit['currency']}\n"
                f"📌 TXID: {deposit['txid']}\n\n"
            )
            
        await update.message.reply_text(message, parse_mode="Markdown")
    
    elif command == "/approve_deposit":
        if not context.args:
            await update.message.reply_text("Usage: /approve_deposit <deposit_id>")
            return
            
        try:
            deposit_id = int(context.args[0])
            deposit = PENDING_DEPOSITS.get(deposit_id)
            
            if not deposit:
                await update.message.reply_text(f"❌ Deposit ID {deposit_id} not found")
                return
                
            user_id = deposit["user_id"]
            amount = deposit["amount"]
            
            if user_id not in USERS:
                await update.message.reply_text(f"❌ User {user_id} not found")
                return
                
            # Add balance
            USERS[user_id]["balance"] += amount
            deposit["status"] = "approved"
            
            # Notify user
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Deposit Approved*\n\n"
                     f"Your deposit of ${amount:.2f} has been approved.\n"
                     f"🆔 Deposit ID: `{deposit_id}`\n"
                     f"New balance: ${USERS[user_id]['balance']:.2f}",
                parse_mode="Markdown"
            )
            
            # Remove from pending
            del PENDING_DEPOSITS[deposit_id]
            await update.message.reply_text(f"✅ Deposit ID {deposit_id} approved. User balance updated.")
            
        except ValueError:
            await update.message.reply_text("❌ Invalid deposit ID")

# ===== NAVIGATION FUNCTIONS =====
async def force_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = query.message.chat_id
    else:
        chat_id = update.message.chat_id
    
    # Resend main menu
    user_id = update.effective_user.id
    if user_id not in USERS:
        reg_date = datetime.now().strftime("%Y/%m/%d")
        USERS[user_id] = {"balance": 0.0, "orders": [], "registration_date": reg_date}
    
    buttons = [
        [InlineKeyboardButton("👁 Views", callback_data="service_Telegram Views")],
        [InlineKeyboardButton("👍 Reactions", callback_data="service_Telegram Reactions")],
        [InlineKeyboardButton("👥 Members", callback_data="service_Telegram Members")],
        [InlineKeyboardButton("🐦 Followers", callback_data="service_Twitter Followers")],
        [InlineKeyboardButton("👀 Views", callback_data="service_Twitter Views")],
        [InlineKeyboardButton("❤️ Likes", callback_data="service_Twitter Likes")],
        [
            InlineKeyboardButton("💰 Deposit", callback_data="deposit"),
            InlineKeyboardButton("📜 Orders", callback_data="my_orders")
        ],
        [
            InlineKeyboardButton("👤 Account", callback_data="my_account"),
            InlineKeyboardButton("🆘 Support", callback_data="support")
        ]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text="⬅️ We are back to the main menu, what can I do for you?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Universal cancel function that returns to main menu"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Operation cancelled. Returning to main menu...")
    else:
        await update.message.reply_text("❌ Operation cancelled. Returning to main menu...")
    
    # Return to main menu
    await force_main_menu(update, context)
    return ConversationHandler.END

# ===== GRACEFUL SHUTDOWN HANDLER =====
def handle_shutdown(signum, frame):
    """Clean up before exiting"""
    logger.info(f"Received shutdown signal {signum}. Stopping bot gracefully...")
    # Add any cleanup actions here if needed
    os._exit(0)

# ===== MAIN FUNCTION =====
def main():
    # Start health check server
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # Start keepalive pinger
    threading.Thread(target=send_keepalive, daemon=True).start()
    
    # Build application
    app = Application.builder().token(TOKEN).build()
    
    # Add cancel handler
    app.add_handler(CommandHandler("cancel", cancel_operation))
    app.add_handler(CallbackQueryHandler(cancel_operation, pattern="^force_main_menu$"))
    
    # Add admin command handlers
    app.add_handler(CommandHandler("add_balance", handle_admin_command))
    app.add_handler(CommandHandler("pending_deposits", handle_admin_command))
    app.add_handler(CommandHandler("approve_deposit", handle_admin_command))
    
    # Order conversation handler
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_services, pattern="^service_")],
        states={
            CHOOSING_SERVICE: [CallbackQueryHandler(service_selected, pattern="^service_")],
            INPUT_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity),
                CommandHandler("cancel", cancel_operation)
            ],
            INPUT_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link),
                CommandHandler("cancel", cancel_operation)
            ],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order, pattern="^confirm_order$")]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_operation, pattern="^cancel_operation$"),
            CallbackQueryHandler(force_main_menu, pattern="^force_main_menu$"),
            CommandHandler("cancel", cancel_operation)
        ]
    )
    
    # Deposit conversation handler
    deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_deposit, pattern="^deposit$")],
        states={
            DEPOSIT_METHOD: [CallbackQueryHandler(handle_deposit_method, pattern="^dep_")],
            DEPOSIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deposit_amount),
                CommandHandler("cancel", cancel_operation)
            ],
            DEPOSIT_TXID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deposit_txid),
                CommandHandler("cancel", cancel_operation)
            ],
            DEPOSIT_CONFIRM: [CallbackQueryHandler(confirm_deposit, pattern="^dep_confirm$")]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_operation, pattern="^cancel_operation$"),
            CallbackQueryHandler(force_main_menu, pattern="^force_main_menu$"),
            CommandHandler("cancel", cancel_operation)
        ]
    )
    
    # Main handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(order_conv)
    app.add_handler(deposit_conv)
    app.add_handler(CallbackQueryHandler(show_my_account, pattern="^my_account$"))
    app.add_handler(CallbackQueryHandler(show_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    
    # Register shutdown signals
    signal.signal(signal.SIGTERM, handle_shutdown)  # For Render
    signal.signal(signal.SIGINT, handle_shutdown)   # For Ctrl+C
    
    # Start with conflict prevention
    logger.info("Starting bot with conflict prevention...")
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
        poll_interval=0.5
    )

if __name__ == "__main__":
    # Initialize logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Øzmain Bot...")
    main()
