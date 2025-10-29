from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 به ربات خوش آمدید!\n\n"
        "دستورات موجود:\n"
        "/start - شروع ربات\n"
        "/help - راهنما\n"
        "/sticker - ساخت استیکر ساده\n"
        "/ai_sticker - ساخت استیکر هوشمند"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📖 راهنمای ربات:\n\n"
        "• /start - شروع ربات\n"
        "• /help - نمایش این راهنما\n"
        "• /sticker <متن> - ساخت استیکر ساده\n"
        "• /ai_sticker <متن> - ساخت استیکر هوشمند\n\n"
        "برای استفاده از استیکر ساز، کافیست متن مورد نظر خود را بعد از دستور ارسال کنید."
    )

async def sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sticker command"""
    if not context.args:
        await update.message.reply_text(
            "❌ لطفاً متن استیکر را وارد کنید.\n"
            "مثال: /sticker سلام دنیا"
        )
        return
    
    text = " ".join(context.args)
    await update.message.reply_text(f"🎨 در حال ساخت استیکر ساده برای: {text}")

async def ai_sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ai_sticker command"""
    if not context.args:
        await update.message.reply_text(
            "❌ لطفاً متن استیکر هوشمند را وارد کنید.\n"
            "مثال: /ai_sticker زیباترین روز"
        )
        return
    
    text = " ".join(context.args)
    await update.message.reply_text(f"🤖 در حال ساخت استیکر هوشمند برای: {text}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message"""
    if update.message.text:
        await update.message.reply_text(
            f"📩 پیام شما دریافت شد: {update.message.text}\n\n"
            "برای استفاده از قابلیت‌های ربات، از دستورات زیر استفاده کنید:\n"
            "/help - نمایش راهنما"
        )

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sticker messages"""
    await update.message.reply_text(
        "😊 استیکر شما زیبا بود!\n\n"
        "برای ساخت استیکر جدید:\n"
        "/sticker <متن>\n"
        "/ai_sticker <متن>"
    )

def setup_handlers(application: Application):
    """Setup all handlers for the application"""
    logger.info("Setting up handlers...")
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sticker", sticker_command))
    application.add_handler(CommandHandler("ai_sticker", ai_sticker_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.STICKER, handle_sticker))
    
    logger.info("All handlers setup completed!")