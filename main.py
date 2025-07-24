import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# ===== CONFIGURATION =====
TOKEN = "7416187173:AAEG5Yly2m2uMhIQTSPQtVbuZVqCXsXQ3Ok"  # From @BotFather
ADMIN_ID = "7468096294"  # From @userinfobot
API_URL = "https://smmtrustpanel.com/api/v2"
API_KEY = "83c0cf2baddad52503fa7f0e9f81884b"  # From your panel dashboard

# ===== CRYPTO ADDRESSES =====
CRYPTO_ADDRESSES = {
    "USDT-TRC20": "TRNku6CNitDdpjYiM68Sf75H1ZBexUmhub",
    "BNB": "0x396cCF7D5a9e967eF243EC3781DfC16065502824",
    "USDT-BEP20": "0x396cCF7D5a9e967eF243EC3781DfC16065502824",
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
    DEPOSIT_METHOD, DEPOSIT_CONFIRM
) = range(6)

# ===== DATABASE =====
USERS = {}  # Stores user data: {user_id: {"balance": 0.0, "orders": []}}

# ===== LOGGING =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== MAIN MENU =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.setdefault(user_id, {"balance": 0.0, "orders": []})
    
    # Create main menu buttons
    first_row = [
        InlineKeyboardButton("TG 👁 View", callback_data="service_Telegram Views"),
        InlineKeyboardButton("TG 👍 Reaction", callback_data="service_Telegram Reactions"),
        InlineKeyboardButton("TG 🤖 Members", callback_data="service_Telegram Members")
    ]
    
    second_row = [
        InlineKeyboardButton("💰 DEPOSIT", callback_data="deposit"),
        InlineKeyboardButton("🛒 My Orders", callback_data="my_orders")
    ]
    
    third_row = [
        InlineKeyboardButton("💳 Balance", callback_data="balance"),
        InlineKeyboardButton("🆘 Support", callback_data="support")
    ]

    await update.message.reply_text(
        "🌟 *SMM Service Bot* 🌟\n\n"
        "▫️ Instant Delivery\n▫️ Competitive Pricing\n▫️ 24/7 Support\n\n"
        "**Main Menu:**",
        reply_markup=InlineKeyboardMarkup([first_row, second_row, third_row]),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ===== SERVICE ORDERING =====
async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"service_{name}")]
        for name in SERVICES.keys()
    ]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    await query.edit_message_text(
        "📦 *Available Services*\n\n"
        "Select a service:",
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
        "✍️ *Enter quantity:*",
        parse_mode="Markdown"
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
            "Twitter: https://twitter.com/tweet/123",
            parse_mode="Markdown"
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
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]
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
        response = requests.get(API_URL, params=params).json()
        
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
            f"🎉 *Order Successful!*\n\n"
            f"📦 Service: {service_name}\n"
            f"🆔 Order ID: {order_id}\n"
            f"💵 Charged: ${price:.4f}\n"
            f"💰 Remaining Balance: ${USERS[user_id]['balance']:.4f}\n\n"
            "Track status with /myorders",
            parse_mode="Markdown"
        )
    except Exception as e:
        # Refund if failed
        USERS[user_id]["balance"] += price
        logger.error(f"Order failed: {str(e)}")
        await query.edit_message_text(
            f"❌ Order Failed!\n\nError: {str(e)}\n\nYour balance has been refunded."
        )
    return ConversationHandler.END

# ===== DEPOSIT SYSTEM =====
async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    buttons = [
        [InlineKeyboardButton("USDT-TRC20", callback_data="dep_usdt_trc20")],
        [InlineKeyboardButton("BNB", callback_data="dep_bnb")],
        [InlineKeyboardButton("SOL", callback_data="dep_sol")],
        [InlineKeyboardButton("TRX", callback_data="dep_trx")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        "💎 *Deposit Crypto*\n\n"
        "▫️ Min Deposit: **$0.5**\n"
        "▫️ Instant Approval\n\n"
        "Select payment method:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return DEPOSIT_METHOD

async def show_deposit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method_map = {
        "dep_usdt_trc20": ("USDT-TRC20", CRYPTO_ADDRESSES["USDT-TRC20"]),
        "dep_bnb": ("BNB", CRYPTO_ADDRESSES["BNB"]),
        "dep_sol": ("SOL", CRYPTO_ADDRESSES["SOL"]),
        "dep_trx": ("TRX", CRYPTO_ADDRESSES["TRX"])
    }
    
    method, address = method_map[query.data]
    context.user_data["deposit_method"] = method
    
    await query.edit_message_text(
        f"📌 *Send {method}*\n\n"
        f"`{address}`\n\n"
        f"⚠️ **Important:**\n"
        f"1. Send ONLY {method}\n"
        f"2. Minimum: $0.5 equivalent\n"
        f"3. Network fees apply\n\n"
        "After sending, click below:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm Deposit", callback_data="dep_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")]
        ]),
        parse_mode="Markdown"
    )
    return DEPOSIT_CONFIRM

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = context.user_data["deposit_method"]
    
    # Add $0.5 to balance (in production: verify blockchain transaction)
    USERS[user_id]["balance"] += 0.5
    
    await query.edit_message_text(
        f"✅ *Deposit Received!*\n\n"
        f"💎 Method: {method}\n"
        f"💰 New Balance: ${USERS[user_id]['balance']:.2f}\n\n"
        "You can now place orders!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ===== UTILITY FUNCTIONS =====
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = USERS[user_id]["balance"]
    
    await query.edit_message_text(
        f"💳 *Your Balance*\n\n"
        f"💰 Available: ${balance:.4f}\n\n"
        "Deposit with /deposit",
        parse_mode="Markdown"
    )

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    orders = USERS[user_id].get("orders", [])
    
    if not orders:
        await query.edit_message_text("📭 You have no active orders.")
        return
    
    message = "📋 *Your Recent Orders*\n\n"
    for order in orders[-5:]:
        message += (
            f"🆔 {order['id']}\n"
            f"📦 {order['service']}\n"
            f"🔢 {order['quantity']} | 💵 ${order['price']:.4f}\n"
            f"📊 Status: {order['status']}\n\n"
        )
    
    await query.edit_message_text(message, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Action cancelled.")
    return ConversationHandler.END

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return ConversationHandler.END

# ===== MAIN FUNCTION =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Order conversation handler
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_services, pattern="^service_")],
        states={
            CHOOSING_SERVICE: [CallbackQueryHandler(service_selected, pattern="^service_")],
            INPUT_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
            INPUT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order, pattern="^confirm_order$")]
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel_order$"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ]
    )
    
    # Deposit conversation handler
    deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_deposit, pattern="^deposit$")],
        states={
            DEPOSIT_METHOD: [CallbackQueryHandler(show_deposit_address, pattern="^dep_")],
            DEPOSIT_CONFIRM: [CallbackQueryHandler(confirm_deposit, pattern="^dep_confirm$")]
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^dep_cancel$"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ]
    )
    
    # Main handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(order_conv)
    app.add_handler(deposit_conv)
    app.add_handler(CallbackQueryHandler(show_balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(show_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    
    app.run_polling()

if __name__ == "__main__":
    main()