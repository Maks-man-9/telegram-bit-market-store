import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import (
    Update,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from database import init_db, create_order, get_order_by_id, update_payment_ref

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
MOBILE_MONEY_DETAILS = os.getenv(
    "MOBILE_MONEY_DETAILS", 
    "Transfer to Merchant ID: 882910 (VoltTech Supply). Use your Order ID as reference."
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Lightweight HTTP Health Check server for Cloud Hosts (Render)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"VoltTech Bot is running 24/7.")
    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health server listening on port {port}")
    server.serve_forever()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"Hello, {user.first_name}!\n\n"
        "Welcome to *VoltTech Hardware Store* ⚡\n"
        "Browse our catalog of fast chargers, Thunderbolt cables, NVMe drives, and adapters.\n\n"
        "Tap the button below to launch our store app."
    )
    
    reply_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("🛍️ Open Store", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        text=welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_kb
    )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") != "SUBMIT_ORDER":
            logger.warning(f"Unknown action received: {data.get('action')}")
            return

        order_id = create_order(
            telegram_user_id=user.id,
            customer_name=data["customer_name"],
            phone_number=data["phone_number"],
            delivery_address=data["delivery_address"],
            delivery_notes=data.get("delivery_notes", ""),
            payment_method=data["payment_method"],
            items=data["items"]
        )

        order = get_order_by_id(order_id)
        if not order:
            await message.reply_text("Failed to retrieve order details.")
            return

        items_summary = "\n".join([
            f"• {item['product_name']} (x{item['quantity']}) — ${item['subtotal']:.2f}"
            for item in order["items"]
        ])

        receipt_text = (
            f"✅ *Order Confirmed!* `#{order['id']:04d}`\n\n"
            f"*Customer:* {order['customer_name']}\n"
            f"*Phone:* `{order['phone_number']}`\n"
            f"*Delivery To:* {order['delivery_address']}\n"
        )
        if order["delivery_notes"]:
            receipt_text += f"*Notes:* {order['delivery_notes']}\n"

        receipt_text += (
            f"\n*Itemized Items:*\n{items_summary}\n\n"
            f"*Total Sum:* `${order['total_amount']:.2f}`\n"
            f"*Payment Method:* `{order['payment_method']}`\n"
        )

        if order["payment_method"] == "MOBILE_MONEY":
            receipt_text += (
                f"\n⚠️ *Payment Required:*\n"
                f"{MOBILE_MONEY_DETAILS}\n"
                f"Once paid, reply to this chat with your transaction code or screenshot."
            )
        else:
            receipt_text += "\n💵 Please keep exact cash ready upon arrival of the delivery courier."

        await message.reply_text(receipt_text, parse_mode=ParseMode.MARKDOWN)

        if ADMIN_CHAT_ID:
            admin_alert = (
                f"🚨 *NEW ORDER NOTIFICATION* `#{order['id']:04d}`\n\n"
                f"*Customer:* {order['customer_name']} ([TG Profile](tg://user?id={user.id}))\n"
                f"*Phone:* `{order['phone_number']}`\n"
                f"*Address:* {order['delivery_address']}\n"
                f"*Items:*\n{items_summary}\n\n"
                f"*Total:* `${order['total_amount']:.2f}`\n"
                f"*Payment:* `{order['payment_method']}`"
            )
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=admin_alert,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send admin order alert: {e}")

    except Exception as e:
        logger.error(f"Error executing order processing: {e}", exc_info=True)
        await message.reply_text("An error occurred while verifying the order. Please contact support.")

async def handle_user_text_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user_text = message.text.strip()
    user = update.effective_user

    if len(user_text) >= 4 and not user_text.startswith("/"):
        await message.reply_text(
            f"✅ Payment reference received: `{user_text}`.\nOur team is verifying the transfer and will confirm shortly!",
            parse_mode=ParseMode.MARKDOWN
        )

        if ADMIN_CHAT_ID:
            admin_notice = (
                f"💳 *Payment Reference Submitted*\n\n"
                f"*From Customer:* {user.full_name} ([TG Profile](tg://user?id={user.id}))\n"
                f"*Reference Code:* `{user_text}`\n\n"
                f"Check your banking app / Telebirr to confirm deposit."
            )
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=admin_notice,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send admin reference alert: {e}")

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    await message.reply_text(
        "✅ Receipt screenshot received! Our team is verifying your payment and preparing your package.",
        parse_mode=ParseMode.MARKDOWN
    )

    if ADMIN_CHAT_ID:
        try:
            await context.bot.forward_message(
                chat_id=ADMIN_CHAT_ID,
                from_chat_id=message.chat_id,
                message_id=message.message_id
            )
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"📸 *Payment Slip* received from {user.full_name} ([TG Profile](tg://user?id={user.id})).",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to relay screenshot to admin: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    init_db()

    threading.Thread(target=start_health_server, daemon=True).start()

    request_config = HTTPXRequest(
        connection_pool_size=10,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0
    )

    app = ApplicationBuilder().token(BOT_TOKEN).request(request_config).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text_replies))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_error_handler(error_handler)

    logger.info("Bot started successfully. Waiting for orders and screenshots...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
