import os
import json
import logging
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from database import (
    init_db,
    add_product,
    delete_product,
    get_active_products,
    create_order,
    get_order_by_id,
    update_payment_ref,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")


# --- Direct Telegram Notification Sender (Thread-safe) ---
def send_telegram_direct(chat_id: int, text: str):
    """Sends a Telegram message using simple HTTP POST without asyncio conflicts."""
    if not chat_id or not BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"User-Agent": "BotOrderDispatcher"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        logger.error(f"Failed to deliver message to chat {chat_id}: {e}")


# --- Combined Health Check & Order API Server ---
class WebRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/products":
            try:
                products = get_active_products()
                payload = json.dumps(products).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                logger.error(f"Error serving /api/products: {e}", exc_info=True)
                err_payload = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(err_payload)))
                self.end_headers()
                self.wfile.write(err_payload)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b"OK")

    def do_POST(self):
        if self.path == "/api/order":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                data = json.loads(body.decode("utf-8"))

                user_id = int(data.get("user_id", 0))
                customer_info = data.get("customer", {})
                items = data.get("items", [])
                payment_method = data.get("payment_method", "MOBILE_MONEY")

                order_id = create_order(
                    telegram_user_id=user_id,
                    customer_name=customer_info.get("name", "Unknown"),
                    phone_number=customer_info.get("phone", ""),
                    delivery_address=customer_info.get("address", ""),
                    delivery_notes=customer_info.get("notes", ""),
                    payment_method=payment_method,
                    items=items,
                )

                order = get_order_by_id(order_id)
                total = float(order["total_amount"])

                # Send Buyer Confirmation with updated payment details
                customer_msg = (
                    f"✅ *Order #{order['id']} Confirmed!*\n\n"
                    f"💰 *Total:* {total:,.2f} ETB\n"
                    f"📍 *Delivery to:* {order['delivery_address']}\n"
                    f"📞 *Phone:* {order['phone_number']}\n\n"
                    "💳 *Payment Instructions:*\n"
                    "Please transfer the total amount using either option below:\n\n"
                    "📱 *Telebirr:* `0950438114`\n"
                    "🏦 *CBE Account:* `1000665061047`\n"
                    "👤 *Account Name:* Kidanemariam Sintayehu\n\n"
                    "After payment, reply directly in this chat with your transaction reference number or upload your payment screenshot."
                )
                if user_id:
                    send_telegram_direct(user_id, customer_msg)

                # Send Admin Alert
                if ADMIN_CHAT_ID:
                    admin_msg = (
                        f"🚨 *New Order Alert: #{order['id']}*\n"
                        f"👤 *Customer:* {order['customer_name']}\n"
                        f"📱 *Phone:* {order['phone_number']}\n"
                        f"📍 *Address:* {order['delivery_address']}\n"
                        f"💵 *Amount:* {total:,.2f} ETB\n"
                        f"📦 *Items:* {len(order.get('items', []))} item(s)"
                    )
                    send_telegram_direct(ADMIN_CHAT_ID, admin_msg)

                resp = json.dumps({"status": "success", "order_id": order_id}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

            except Exception as e:
                logger.error(f"Error creating order via API: {e}", exc_info=True)
                err_resp = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(err_resp)))
                self.end_headers()
                self.wfile.write(err_resp)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), WebRequestHandler)
    logger.info(f"HTTP API & Health server active on port {port}")
    server.serve_forever()


# --- Admin Conversation States for /addproduct ---
(
    WAITING_NAME,
    WAITING_CATEGORY,
    WAITING_PRICE,
    WAITING_STOCK,
    WAITING_SPECS,
    WAITING_PHOTO,
) = range(6)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name or "there"
    welcome_text = (
        f"👋 Welcome to the store, {user_first_name}!\n\n"
        "Browse our collection and place orders directly in the WebApp below."
    )

    keyboard = [
        [InlineKeyboardButton("🛍️ Open Store", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    if is_admin(update.effective_user.id):
        welcome_text += "\n\n🛠️ *Admin Controls:*\n/addproduct - Add a new item\n/deleteproduct - Deactivate an item\n/catalog - View current stock"

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    products = get_active_products()
    if not products:
        await update.message.reply_text("No active products currently in the catalog.")
        return

    text = "📦 *Current Active Catalog:*\n\n"
    for p in products:
        text += f"• *ID #{p['id']}* — {p['name']}\n  Price: {float(p['price']):,.2f} ETB | Stock: {p['stock_count']}\n\n"
    text += "To deactivate an item: `/deleteproduct <id>`"
    await update.message.reply_text(text, parse_mode="Markdown")


async def delete_product_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/deleteproduct <id>`\nExample: `/deleteproduct 3`", parse_mode="Markdown")
        return

    try:
        pid = int(context.args[0])
        success = delete_product(pid)
        if success:
            await update.message.reply_text(f"🗑️ Product #{pid} was successfully deactivated.")
        else:
            await update.message.reply_text(f"❌ Product #{pid} not found.")
    except ValueError:
        await update.message.reply_text("Please provide a valid numeric product ID.")


async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END

    await update.message.reply_text("📝 Step 1/6: Enter the *Product Name*:\n(or send /cancel to abort)", parse_mode="Markdown")
    return WAITING_NAME


async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_p_name"] = update.message.text.strip()
    await update.message.reply_text("🏷️ Step 2/6: Enter the *Category* (e.g., Chargers, Cables, Audio, Storage):", parse_mode="Markdown")
    return WAITING_CATEGORY


async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_p_cat"] = update.message.text.strip()
    await update.message.reply_text("💵 Step 3/6: Enter the *Price in Birr (ETB)* (e.g., 2500):", parse_mode="Markdown")
    return WAITING_PRICE


async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
        context.user_data["new_p_price"] = price
        await update.message.reply_text("📦 Step 4/6: Enter the *Stock Quantity* (e.g., 20):", parse_mode="Markdown")
        return WAITING_STOCK
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for price (e.g., 1800 or 2450.50):")
        return WAITING_PRICE


async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text.strip())
        context.user_data["new_p_stock"] = stock
        await update.message.reply_text("📋 Step 5/6: Enter *Short Specs / Description*:\n(e.g., '65W GaN Fast Charging, Dual Port')", parse_mode="Markdown")
        return WAITING_SPECS
    except ValueError:
        await update.message.reply_text("❌ Please enter a whole number for stock quantity:")
        return WAITING_STOCK


async def add_product_specs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_p_specs"] = update.message.text.strip()
    await update.message.reply_text(
        "🖼️ Step 6/6: Send a *Photo* of the item, or send an image URL text:\n(or send /skip for placeholder)",
        parse_mode="Markdown"
    )
    return WAITING_PHOTO


async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    image_url = "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"

    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        image_url = file.file_path
    elif update.message.text and update.message.text.startswith("http"):
        image_url = update.message.text.strip()

    pid = add_product(
        name=context.user_data["new_p_name"],
        category=context.user_data["new_p_cat"],
        price=context.user_data["new_p_price"],
        stock_count=context.user_data["new_p_stock"],
        specs=context.user_data["new_p_specs"],
        image_url=image_url,
    )

    await update.message.reply_text(
        f"🎉 *Product Added Successfully!*\n\n"
        f"• *ID:* #{pid}\n"
        f"• *Name:* {context.user_data['new_p_name']}\n"
        f"• *Price:* {context.user_data['new_p_price']:,.2f} ETB\n"
        f"• *Stock:* {context.user_data['new_p_stock']}\n\n"
        "It is now stored in your Supabase database.",
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🚫 Product creation cancelled.")
    return ConversationHandler.END


def main():
    init_db()

    threading.Thread(target=run_web_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("catalog", catalog))
    app.add_handler(CommandHandler("deleteproduct", delete_product_cmd))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addproduct", add_product_start)],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name)],
            WAITING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_category)],
            WAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_price)],
            WAITING_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_stock)],
            WAITING_SPECS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_specs)],
            WAITING_PHOTO: [
                MessageHandler(filters.PHOTO, add_product_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_photo),
                CommandHandler("skip", add_product_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    app.add_handler(conv_handler)

    logger.info("Bot started and listening...")
    app.run_polling()


if __name__ == "__main__":
    main()
