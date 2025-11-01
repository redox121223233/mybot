#!/usr/bin/env python3
"""
Complete integrated Telegram Bot for Vercel
All code in one file to avoid import issues
"""

import os
import json
import logging
import asyncio
import random
import tempfile
import io
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from wsgiref.simple_server import make_server

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for user states
user_states = {}

class TelegramBotFeatures:
    """Complete bot features class"""

    def __init__(self):
        self.user_data = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """🎉 به ربات من خوش آمدید! 🎉

🎨 **سازنده استیکر:**
برای ساخت استیکر، یک عکس برای من ارسال کنید.

🎮 **بازی‌ها و سرگرمی‌ها:**
• 🔢 حدس عدد - یک عدد بین ۱ تا ۱۰۰ را حدس بزنید
• ✂️ سنگ کاغذ قیچی - بازی کلاسیک

📚 **راهنما:**
/help - دیدن تمام دستورات
"""

        keyboard = [
            [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator")],
            [InlineKeyboardButton("🔢 حدس عدد", callback_data="guess_number")],
            [InlineKeyboardButton("✂️ سنگ کاغذ قیچی", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("📚 راهنما", callback_data="help")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """📚 **راهنمای کامل ربات:**

🎨 **استیکر ساز:**
1. یک عکس برای ربات ارسال کنید.
2. متنی که می‌خواهید روی استیکر باشد را بنویسید.
3. اندازه فونت را انتخاب کنید.

🎮 **بازی‌ها:**
/guess - شروع بازی حدس عدد
/rps - سنگ کاغذ قیچی

💬 **سایر:**
/start - منوی اصلی
/help - این راهنما
"""
        await update.message.reply_text(help_text)

    async def create_sticker(self, image_stream, text, font_size=60):
        """Create a sticker by adding text to an image"""
        try:
            # Open the user's image
            img = Image.open(image_stream).convert("RGBA")
            img = img.resize((512, 512))

            draw = ImageDraw.Draw(img)

            # Use a default font
            try:
                font = ImageFont.truetype("fonts/Vazir.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Calculate text position to center it
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            position = ((512 - text_width) / 2, (512 - text_height) / 2)

            # Add a simple stroke for better visibility
            stroke_width = 2
            stroke_fill = "black"
            draw.text((position[0]-stroke_width, position[1]-stroke_width), text, font=font, fill=stroke_fill)
            draw.text((position[0]+stroke_width, position[1]-stroke_width), text, font=font, fill=stroke_fill)
            draw.text((position[0]-stroke_width, position[1]+stroke_width), text, font=font, fill=stroke_fill)
            draw.text((position[0]+stroke_width, position[1]+stroke_width), text, font=font, fill=stroke_fill)

            # Draw the main text
            draw.text(position, text, font=font, fill="white")

            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            return img_bytes

        except Exception as e:
            logger.error(f"Error creating sticker: {e}")
            return None

    async def guess_number_game(self, update: Update):
        """Setup guess number game"""
        number = random.randint(1, 100)
        user_id = update.effective_user.id
        user_states[user_id] = {'mode': 'guess_game', 'number': number, 'attempts': 0}

        message = "🔢 **بازی حدس عدد!**\n\nمن یک عدد بین ۱ تا ۱۰۰ انتخاب کردم. حدس شما چیه؟"
        await update.message.reply_text(message)

    async def check_guess(self, update: Update, guess: int):
        """Check user's guess"""
        user_id = update.effective_user.id
        state = user_states.get(user_id, {})

        if state.get('mode') != 'guess_game':
            await update.message.reply_text("بازی شروع نشده! /guess رو بزنید")
            return

        number = state['number']
        state['attempts'] += 1
        attempts = state['attempts']

        if guess == number:
            message = f"🎉 **آفرین!**\n\nعدد {number} بود!\nتعداد تلاش‌ها: {attempts}"
            del user_states[user_id]
        elif guess < number:
            message = f"📈 **برو بالاتر!**\n\nحدس شما ({guess}) کوچکتره."
        else:
            message = f"📉 **برو پایین‌تر!**\n\nحدس شما ({guess}) بزرگتره."

        await update.message.reply_text(message)

    async def rock_paper_scissors_game(self, update: Update):
        """Setup rock paper scissors game"""
        keyboard = [
            [
                InlineKeyboardButton("✊ سنگ", callback_data="rps_rock"),
                InlineKeyboardButton("📄 کاغذ", callback_data="rps_paper"),
                InlineKeyboardButton("✂️ قیچی", callback_data="rps_scissors")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✂️ **سنگ کاغذ قیچی!**\n\nانتخاب کنید:", reply_markup=reply_markup)

    async def check_rps_choice(self, update: Update, user_choice: str):
        """Check RPS choice"""
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)

        choice_text = {"rock": "سنگ", "paper": "کاغذ", "scissors": "قیچی"}

        result = ""
        if user_choice == bot_choice:
            result = "🤝 **مساوی!**"
        elif (
            (user_choice == "rock" and bot_choice == "scissors") or
            (user_choice == "paper" and bot_choice == "rock") or
            (user_choice == "scissors" and bot_choice == "paper")
        ):
            result = "🎉 **شما بردید!**"
        else:
            result = "😔 **من بردم!**"

        message = f"{result}\n\nشما: {choice_text[user_choice]}\nمن: {choice_text[bot_choice]}"
        await update.callback_query.edit_message_text(message)

# Initialize bot features
bot_features = TelegramBotFeatures()

# Handler functions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.help_command(update, context)

async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.guess_number_game(update)

async def rps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.rock_paper_scissors_game(update)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos for sticker creation"""
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()

    user_states[user_id] = {
        'mode': 'sticker_creation',
        'photo_file_id': photo_file.file_id
    }
    await update.message.reply_text("🖼️ عکس شما دریافت شد.\n\nحالا متنی که می‌خواهید روی استیکر باشد را بنویسید:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for games or sticker creation"""
    user_id = update.effective_user.id
    text = update.message.text
    state = user_states.get(user_id, {})

    if state.get('mode') == 'guess_game':
        try:
            guess = int(text)
            await bot_features.check_guess(update, guess)
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد صحیح وارد کنید!")

    elif state.get('mode') == 'sticker_creation':
        state['text'] = text

        keyboard = [
            [
                InlineKeyboardButton("کوچک", callback_data="font_small"),
                InlineKeyboardButton("متوسط", callback_data="font_medium"),
                InlineKeyboardButton("بزرگ", callback_data="font_large")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اندازه فونت را انتخاب کنید:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data
    state = user_states.get(user_id, {})

    if callback_data.startswith("rps_"):
        user_choice = callback_data.split("_")[1]
        await bot_features.check_rps_choice(update, user_choice)

    elif callback_data.startswith("font_"):
        if state.get('mode') != 'sticker_creation':
            await query.edit_message_text("لطفاً ابتدا یک عکس ارسال کنید.")
            return

        font_size = {
            "font_small": 40,
            "font_medium": 60,
            "font_large": 80
        }.get(callback_data, 60)

        await query.edit_message_text("⏳ در حال ساخت استیکر...")

        photo_file_id = state['photo_file_id']
        text = state['text']

        photo_file = await context.bot.get_file(photo_file_id)
        photo_stream = io.BytesIO()
        await photo_file.download_to_memory(photo_stream)
        photo_stream.seek(0)

        sticker_bytes = await bot_features.create_sticker(photo_stream, text, font_size)

        if sticker_bytes:
            await context.bot.send_sticker(chat_id=user_id, sticker=sticker_bytes)
        else:
            await query.edit_message_text("❌ خطا در ساخت استیکر!")

        del user_states[user_id]

def setup_application(application):
    """Setup all handlers for the application"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("guess", guess_command))
    application.add_handler(CommandHandler("rps", rps_command))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

# Initialize Telegram application
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
application = None

if TELEGRAM_TOKEN:
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        setup_application(application)
        logger.info("Handlers setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up application: {e}")
else:
    logger.error("No Telegram token found in environment variables")

def wsgi_app(environ, start_response):
    """Simple WSGI handler for Vercel"""
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')

    if path == '/' and method == 'GET':
        body = json.dumps({'status': 'ok', 'message': 'Bot is running'}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [body]

    if path == '/api' and method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            body_bytes = environ['wsgi.input'].read(content_length)
            webhook_data = json.loads(body_bytes)

            async def process():
                update = Update.de_json(webhook_data, application.bot)
                await application.process_update(update)

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(process())
            else:
                loop.run_until_complete(process())

            start_response('200 OK', [('Content-Type', 'application/json')])
            return [b'{"status":"ok"}']
        except Exception as e:
            logger.error(f"Error in webhook: {e}")
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return [b'Internal Server Error']

    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Not Found']

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        environ = self.get_environ()
        result = wsgi_app(environ, self.start_response)
        self.finish_response(result)

    def do_POST(self):
        environ = self.get_environ()
        result = wsgi_app(environ, self.start_response)
        self.finish_response(result)

    def get_environ(self):
        environ = {
            'wsgi.version': (1, 0), 'wsgi.url_scheme': 'https',
            'wsgi.input': self.rfile, 'wsgi.errors': io.StringIO(),
            'wsgi.multithread': False, 'wsgi.multiprocess': False, 'wsgi.run_once': False,
            'REQUEST_METHOD': self.command, 'PATH_INFO': self.path,
            'SERVER_NAME': self.headers.get('Host', '').split(':')[0],
            'SERVER_PORT': self.headers.get('Host', '').split(':')[-1] if ':' in self.headers.get('Host', '') else '443',
        }
        for key, value in self.headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
            environ[key] = value
        if 'Content-Type' in self.headers:
            environ['CONTENT_TYPE'] = self.headers['Content-Type']
        if 'Content-Length' in self.headers:
            environ['CONTENT_LENGTH'] = self.headers['Content-Length']
        return environ

    def start_response(self, status, headers):
        self.send_response(int(status.split(' ')[0]))
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()

    def finish_response(self, result):
        for data in result:
            self.wfile.write(data)

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 8000))
    httpd = make_server('', PORT, wsgi_app)
    print(f"Serving on port {PORT}...")
    httpd.serve_forever()
