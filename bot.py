import asyncio
import logging
import requests
from telegram import Update
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
TOKEN = "8462686827:AAF0S878DtGZ3sifOL_eQMqUlSyxQK0iCKQ"  # Replace with your bot token
ADMIN_ID = "7468096294"  # Replace with your Telegram ID
API_URL = "https://smmtrustpanel.com/api/v2"
API_KEY = "83c0cf2baddad52503fa7f0e9f81884b"  # Replace with your panel API key

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
    "Telegram Views": {"id": 3017, "your_rate": 0.02, "min": 10, "max": 100000},
    "Telegram Reactions": {"id": 3023, "your_rate": 0.07, "min": 100, "max": 40000},
    "Telegram Members": {"id": 3403, "your_rate": 1.00, "min": 100, "max": 50000},
    "Twitter Followers": {"id": 3326, "your_rate": 3.00, "min": 50, "max": 5000},
    "Twitter Views": {"id": 2538, "your_rate": 0.10, "min": 100, "max": 100000},
    "Twitter Likes": {"id": 2568, "your_rate": 0.50, "min": 50, "max": 50000}
}

# ===== STATES =====
(CHOOSING_SERVICE, INPUT_QUANTITY, INPUT_LINK, CONFIRM_ORDER,
 DEPOSIT_METHOD, DEPOSIT_AMOUNT, DEPOSIT_TXID, DEPOSIT_CONFIRM) = range(8)

# ===== DATABASE =====
USERS = {}
PENDING_DEPOSITS = {}
DEPOSIT_ID_COUNTER = 1

# ===== LOGGING =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== MAIN MENU =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "📦 Available Services\n\nSelect a service:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHOOSING_SERVICE

async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service_name = query.data.split("_", 1)[1]
    service = SERVICES[service_name]
    context.user_data["service"] = service_name
    
    await query.edit_message_text(
        f"📊 {service_name}\n\n"
        f"💵 Price: ${service['your_rate']} per 1000\n"
        f"📦 Min: {service['min']} | Max: {service['max']}\n\n"
        "Enter quantity:",
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
            "🔗 Now send the target link\n\n"
            "Examples:\nTelegram: https://t.me/channel/123\nTwitter: https://twitter.com/tweet/123",
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
            f"Needed: ${price:.4f}\nYour balance: ${balance:.4f}\n\n"
            "Please deposit first with /deposit"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ Order Summary\n\n"
        f"📦 Service: {service_name}\n"
        f"🔗 Link: {link}\n"
        f"📊 Quantity: {quantity}\n"
        f"💵 Price: ${price:.4f}\n\n"
        "Confirm this order?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm_order")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
        ])
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
        
        await query.edit_message_text(
            f"🎉 Order Successful!\n\n"
            f"📦 Service: {service_name}\n"
            f"🆔 Order ID: {order_id}\n"
            f"💵 Charged: ${price:.4f}\n"
            f"💰 Remaining Balance: ${USERS[user_id]['balance']:.4f}\n\n"
            "Returning to main menu..."
        )
        await force_main_menu(update, context)
    except Exception as e:
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
        "💎 Select Deposit Method\n\nChoose cryptocurrency:",
        reply_markup=InlineKeyboardMarkup(buttons)
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
        f"📥 {method} Deposit Request\n\n"
        f"💵 How much in USD? (Min: $0.5)\n\n"
        "Example: For $10, type: 10",
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
            f"🌐 {method} Deposit Address\n\n"
            f"{address}\n\n"
            f"💵 Send at least ${amount:.2f} worth of {method}\n\n"
            "🔗 After sending, provide TXID or type NONE",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
            ])
        )
        return DEPOSIT_TXID
    except ValueError:
        await update.message.reply_text("❗ Please enter a valid number")
        return DEPOSIT_AMOUNT

async def handle_deposit_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = update.message.text
    context.user_data["deposit_txid"] = txid
    method = context.user_data["deposit_method"]
    amount = context.user_data["deposit_amount"]
    
    txid_display = txid if txid.upper() != "NONE" else "NONE"
    
    await update.message.reply_text(
        f"🔍 Transaction Details\n\n"
        f"📌 TXID: {txid_display}\n"
        f"💎 Type: {method}\n"
        f"💵 USD Amount: ${amount:.2f}\n\n"
        f"✅ Click 'Accept' to confirm",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Accept", callback_data="dep_confirm")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="force_main_menu")]
        ])
    )
    return DEPOSIT_CONFIRM

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
    
    # Notify admin
    username = query.from_user.username or query.from_user.full_name
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 New Deposit Request\n\n"
             f"🆔 ID: {deposit_id}\n👤 User: @{username} ({user_id})\n"
             f"💵 Amount: ${amount:.2f}\n💎 Currency: {method}\n"
             f"📌 TXID: {txid}\n\nApprove with: /approve_deposit {deposit_id}"
    )
    
    # Notify user
    await query.edit_message_text(
        f"⏳ Deposit Submitted\n\n"
        f"${amount:.2f} in {method}\n🆔 ID: {deposit_id}\n\n"
        f"Awaiting admin approval. You'll be notified when approved."
    )
    await force_main_menu(update, context)
    return ConversationHandler.END

# ===== MY ACCOUNT =====
async def show_my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = USERS.get(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ User not found. Use /start")
        return
    
    num_orders = len(user_data["orders"])
    await query.edit_message_text(
        f"👤 My Account\n\n"
        f"▫️ User ID: {user_id}\n"
        f"▫️ Joined: {user_data['registration_date']}\n"
        f"▫️ Orders: {num_orders}\n"
        f"▫️ Balance: ${user_data['balance']:.4f}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
        ])
    )

# ===== ORDER HISTORY =====
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    orders = USERS.get(user_id, {}).get("orders", [])
    
    if not orders:
        message = "📭 No orders yet"
    else:
        message = "📋 Last 5 Orders\n\n"
        for order in orders[-5:]:
            status_icon = "✅" if order.get("status") == "Completed" else "⏳"
            message += (
                f"{status_icon} {order['service']}\n"
                f"🆔 ID: {order['id']}\n"
                f"🔢 Qty: {order['quantity']} | 💵 ${order['price']:.4f}\n"
                f"📊 Status: {order.get('status', 'Processing')}\n\n"
            )
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="force_main_menu")]
        ])
    )

# ===== SUPPORT FUNCTION =====
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔰 Support\n\n"
        "Contact our team for help:\n"
        "@DVMAJ\n\n"
        "Returning to main menu in 5 seconds..."
    )
    await asyncio.sleep(5)
    await force_main_menu(update, context)
    return ConversationHandler.END

# ===== ADMIN COMMANDS =====
async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    command = update.message.text.split()[0]
    
    if command == "/add_balance":
        try:
            target_id = int(context.args[0])
            amount = float(context.args[1])
            if target_id in USERS:
                USERS[target_id]["balance"] += amount
                await update.message.reply_text(f"✅ Added ${amount:.2f} to user {target_id}")
                await context.bot.send_message(
                    target_id,
                    f"💳 Balance +${amount:.2f}\nNew balance: ${USERS[target_id]['balance']:.2f}"
                )
            else:
                await update.message.reply_text("❌ User not found")
        except:
            await update.message.reply_text("Usage: /add_balance USER_ID AMOUNT")
    
    elif command == "/pending_deposits":
        if not PENDING_DEPOSITS:
            await update.message.reply_text("ℹ️ No pending deposits")
            return
            
        message = "📋 Pending Deposits\n\n"
        for dep_id, dep in PENDING_DEPOSITS.items():
            message += f"🆔 {dep_id} | 👤 {dep['user_id']}\n💵 ${dep['amount']:.2f} {dep['currency']}\n\n"
        await update.message.reply_text(message)
    
    elif command == "/approve_deposit":
        try:
            dep_id = int(context.args[0])
            dep = PENDING_DEPOSITS.get(dep_id)
            if dep:
                user_id = dep["user_id"]
                amount = dep["amount"]
                if user_id in USERS:
                    USERS[user_id]["balance"] += amount
                    del PENDING_DEPOSITS[dep_id]
                    await update.message.reply_text(f"✅ Approved deposit {dep_id}")
                    await context.bot.send_message(
                        user_id,
                        f"✅ Deposit Approved\n\n${amount:.2f} added to your balance\nNew balance: ${USERS[user_id]['balance']:.2f}"
                    )
                else:
                    await update.message.reply_text("❌ User not found")
            else:
                await update.message.reply_text("❌ Deposit not found")
        except:
            await update.message.reply_text("Usage: /approve_deposit DEPOSIT_ID")

# ===== NAVIGATION FUNCTIONS =====
async def force_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        chat_id = query.message.chat_id
    else:
        chat_id = update.message.chat_id
    
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
        text="⬅️ Back to main menu, what can I do for you?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ConversationHandler.END

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    await force_main_menu(update, context)
    return ConversationHandler.END

# ===== MAIN FUNCTION WITH GRACEFUL SHUTDOWN =====
def main():
    # Create Application with persistent data
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("cancel", cancel_operation))
    app.add_handler(CallbackQueryHandler(cancel_operation, pattern="^force_main_menu$"))
    
    # Admin commands
    app.add_handler(CommandHandler("add_balance", handle_admin_command))
    app.add_handler(CommandHandler("pending_deposits", handle_admin_command))
    app.add_handler(CommandHandler("approve_deposit", handle_admin_command))
    
    # Order conversation
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_services, pattern="^service_")],
        states={
            CHOOSING_SERVICE: [CallbackQueryHandler(service_selected, pattern="^service_")],
            INPUT_QUANTITY: [MessageHandler(filters.TEXT, handle_quantity)],
            INPUT_LINK: [MessageHandler(filters.TEXT, handle_link)],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order, pattern="^confirm_order$")]
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)]
    )
    
    # Deposit conversation
    deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_deposit, pattern="^deposit$")],
        states={
            DEPOSIT_METHOD: [CallbackQueryHandler(handle_deposit_method, pattern="^dep_")],
            DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT, handle_deposit_amount)],
            DEPOSIT_TXID: [MessageHandler(filters.TEXT, handle_deposit_txid)],
            DEPOSIT_CONFIRM: [CallbackQueryHandler(confirm_deposit, pattern="^dep_confirm$")]
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)]
    )
    
    # Main handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(order_conv)
    app.add_handler(deposit_conv)
    app.add_handler(CallbackQueryHandler(show_my_account, pattern="^my_account$"))
    app.add_handler(CallbackQueryHandler(show_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    
    # Start the bot with graceful shutdown handling
    app.run_polling(
        close_loop=False,  # Important for Render
        stop_signals=None,  # Disable default signal handling
        allowed_updates=None  # Receive all update types
    )

if __name__ == "__main__":
    main()
