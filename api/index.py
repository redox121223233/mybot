#!/usr/bin/env python3
"""
Complete integrated Telegram Bot for Vercel with Sticker Pack Support
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
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for user states
user_states = {}

class StickerPackHandler:
    """Handle sticker pack creation and management"""
    
    def __init__(self):
        # Dictionary to store user sticker packs
        # Format: {user_id: {pack_name: {"name": str, "title": str, "stickers": List[Dict]}}}
        self.user_sticker_packs = {}
        # Current pack being created by each user
        self.user_current_pack = {}
        
    async def create_new_sticker_pack(self, user_id: int, pack_name: str, pack_title: str) -> Dict:
        """Create a new sticker pack for user"""
        try:
            # Initialize user data if not exists
            if user_id not in self.user_sticker_packs:
                self.user_sticker_packs[user_id] = {}
                
            # Check if pack already exists
            if pack_name in self.user_sticker_packs[user_id]:
                return {
                    "success": False,
                    "message": f"❌ پک استیکر '{pack_name}' از قبل وجود دارد! لطفاً نام دیگری انتخاب کنید."
                }
            
            # Create new pack
            self.user_sticker_packs[user_id][pack_name] = {
                "name": pack_name,
                "title": pack_title,
                "stickers": [],
                "created_at": None,
                "telegram_pack_name": None  # Will be set when pack is created on Telegram
            }
            
            # Set as current pack
            self.user_current_pack[user_id] = pack_name
            
            return {
                "success": True,
                "message": f"✅ پک استیکر جدید '{pack_title}' با موفقیت ساخته شد!\n\nحالا می‌توانید استیکرهای خود را ارسال کنید تا به این پک اضافه شوند."
            }
            
        except Exception as e:
            logger.error(f"Error creating sticker pack: {e}")
            return {
                "success": False,
                "message": "❌ خطا در ساخت پک استیکر! لطفاً دوباره تلاش کنید."
            }
    
    async def add_sticker_to_pack(self, user_id: int, sticker_data: Dict) -> Dict:
        """Add a sticker to user's current pack"""
        try:
            # Check if user has a current pack
            current_pack = self.user_current_pack.get(user_id)
            if not current_pack:
                return {
                    "success": False,
                    "message": "❌ شما هیچ پک استیکری فعال ندارید! ابتدا یک پک جدید بسازید."
                }
            
            # Check if pack exists
            if user_id not in self.user_sticker_packs or current_pack not in self.user_sticker_packs[user_id]:
                return {
                    "success": False,
                    "message": "❌ پک استیکر پیدا نشد! لطفاً یک پک جدید بسازید."
                }
            
            # Add sticker to pack
            pack = self.user_sticker_packs[user_id][current_pack]
            sticker_info = {
                "file_id": sticker_data.get("file_id"),
                "emoji": sticker_data.get("emoji", "😊"),
                "added_at": None
            }
            
            pack["stickers"].append(sticker_info)
            
            return {
                "success": True,
                "message": f"✅ استیکر با موفقیت به پک '{pack['title']}' اضافه شد!\n\nتعداد استیکرها: {len(pack['stickers'])} 📊"
            }
            
        except Exception as e:
            logger.error(f"Error adding sticker to pack: {e}")
            return {
                "success": False,
                "message": "❌ خطا در اضافه کردن استیکر به پک! لطفاً دوباره تلاش کنید."
            }
    
    async def get_user_packs(self, user_id: int) -> List[Dict]:
        """Get all sticker packs for a user"""
        if user_id not in self.user_sticker_packs:
            return []
        
        packs = []
        for pack_name, pack_data in self.user_sticker_packs[user_id].items():
            packs.append({
                "name": pack_data["name"],
                "title": pack_data["title"],
                "sticker_count": len(pack_data["stickers"]),
                "is_current": pack_name == self.user_current_pack.get(user_id)
            })
        
        return packs
    
    async def set_current_pack(self, user_id: int, pack_name: str) -> Dict:
        """Set a pack as the current active pack for user"""
        try:
            if user_id not in self.user_sticker_packs or pack_name not in self.user_sticker_packs[user_id]:
                return {
                    "success": False,
                    "message": "❌ پک استیکر پیدا نشد!"
                }
            
            self.user_current_pack[user_id] = pack_name
            pack = self.user_sticker_packs[user_id][pack_name]
            
            return {
                "success": True,
                "message": f"✅ پک '{pack['title']}' به عنوان پک فعلی انتخاب شد.\n\nاکنون می‌توانید استیکرها را به این پک اضافه کنید."
            }
            
        except Exception as e:
            logger.error(f"Error setting current pack: {e}")
            return {
                "success": False,
                "message": "❌ خطا در انتخاب پک! لطفاً دوباره تلاش کنید."
            }
    
    def get_pack_management_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get keyboard for pack management"""
        keyboard = []
        
        # Add current pack info if exists
        current_pack = self.user_current_pack.get(user_id)
        if current_pack and user_id in self.user_sticker_packs:
            pack_info = self.user_sticker_packs[user_id][current_pack]
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 پک فعلی: {pack_info['title']} ({len(pack_info['stickers'])} استیکر)", 
                    callback_data="pack_info"
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ ساخت پک جدید", callback_data="create_new_pack")],
            [InlineKeyboardButton("📋 مشاهده پک‌ها", callback_data="list_packs")],
            [InlineKeyboardButton("🔧 انتخاب پک فعلی", callback_data="select_current_pack")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_packs_list_keyboard(self, user_id: int):
        """Get keyboard with user's sticker packs"""
        if user_id not in self.user_sticker_packs:
            return None
        
        packs = self.user_sticker_packs[user_id]
        if not packs:
            return None
        
        keyboard = []
        for pack_name, pack_data in packs.items():
            is_current = pack_name == self.user_current_pack.get(user_id)
            status = " ✅" if is_current else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {pack_data['title']} ({len(pack_data['stickers'])}){status}", 
                    callback_data=f"select_pack_{pack_name}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="sticker_pack_menu")])
        return InlineKeyboardMarkup(keyboard)

# Initialize handlers
sticker_pack_handler = StickerPackHandler()

class TelegramBotFeatures:
    """Complete bot features class"""
    
    def __init__(self):
        self.user_data = {}
        self.coupons = self.load_coupons()
        self.music_data = self.load_music_data()
        
    def load_coupons(self):
        return [
            {"code": "SAVE10", "discount": "10%", "category": "electronics"},
            {"code": "FOOD20", "discount": "20%", "category": "food"},
            {"code": "STYLE15", "discount": "15%", "category": "fashion"},
            {"code": "TECH25", "discount": "25%", "category": "technology"},
            {"code": "HOME30", "discount": "30%", "category": "home"},
        ]
    
    def load_music_data(self):
        return {
            "pop": ["Artist1 - Song1", "Artist2 - Song2", "Artist3 - Song3"],
            "rock": ["Band1 - Track1", "Band2 - Track2", "Band3 - Track3"],
            "classical": ["Composer1 - Piece1", "Composer2 - Piece2", "Composer3 - Piece3"],
            "jazz": ["JazzArtist1 - JazzSong1", "JazzArtist2 - JazzSong2", "JazzArtist3 - JazzSong3"],
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """🎉 به ربات من خوش آمدید! 🎉

🎮 **بازی‌ها و سرگرمی‌ها:**
• 🎲 حدس عدد - یک عدد بین ۱ تا ۱۰۰ را حدس بزنید
• ✂️ سنگ کاغذ قیچی - بازی کلاسیک
• 📝 بازی کلمات - حدس کلمات
• 🧠 بازی حافظه - تست حافظه شما
• 🎲 بازی تصادفی - شانس خود را امتحان کنید

🎨 **سازنده استیکر:**
• 🖼️ استیکر سریع با دستور /sticker <متن>
• 🎨 استیکر سفارشی با دستور /customsticker
• 📦 مدیریت پک استیکر

📚 **راهنما:**
/help - دیدن تمام دستورات

انتخاب کنید:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎲 حدس عدد", callback_data="guess_number")],
            [InlineKeyboardButton("✂️ سنگ کاغذ قیچی", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("📝 بازی کلمات", callback_data="word_game")],
            [InlineKeyboardButton("🧠 بازی حافظه", callback_data="memory_game")],
            [InlineKeyboardButton("🎲 بازی تصادفی", callback_data="random_game")],
            [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator")],
            [InlineKeyboardButton("📦 پک استیکر", callback_data="sticker_pack_menu")],
            [InlineKeyboardButton("📚 راهنما", callback_data="help")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """📚 **راهنمای کامل ربات:**

🎮 **بازی‌ها:**
/guess - شروع بازی حدس عدد
/rps - سنگ کاغذ قیچی
/word - بازی کلمات
/memory - بازی حافظه
/random - بازی تصادفی

🎨 **استیکر ساز:**
/sticker <متن> - ساخت استیکر سریع
/customsticker - منوی استیکر ساز سفارشی
/pack - مدیریت پک استیکر

📝 **مثال استیکر:**
/sticker سلام دنیا! 🌍

❓ برای هر سوال از منوی اصلی استفاده کنید!"""
        
        await update.message.reply_text(help_text)
    
    async def create_sticker(self, text, bg_color="white"):
        """Create a simple text sticker"""
        try:
            # Create image
            img_size = (512, 512)
            img = Image.new('RGB', img_size, bg_color)
            draw = ImageDraw.Draw(img)
            
            # Try to use default font
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            # Calculate text position
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(text) * 10
                text_height = 20
            
            x = (img_size[0] - text_width) // 2
            y = (img_size[1] - text_height) // 2
            
            # Draw text
            text_color = "black" if bg_color == "white" else "white"
            draw.text((x, y), text, fill=text_color, font=font)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            logger.error(f"Error creating sticker: {e}")
            return None
    
    async def custom_sticker_menu(self):
        """Show custom sticker menu"""
        keyboard = [
            [
                InlineKeyboardButton("⚪ سفید", callback_data="sticker_bg_white"),
                InlineKeyboardButton("⚫ سیاه", callback_data="sticker_bg_black")
            ],
            [
                InlineKeyboardButton("🔵 آبی", callback_data="sticker_bg_blue"),
                InlineKeyboardButton("🔴 قرمز", callback_data="sticker_bg_red")
            ],
            [
                InlineKeyboardButton("🟢 سبز", callback_data="sticker_bg_green"),
                InlineKeyboardButton("🟡 زرد", callback_data="sticker_bg_yellow")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        message = "🎨 **سازنده استیکر سفارشی!**\n\nرنگ پس‌زمینه را انتخاب کنید:"
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return {"message": message, "reply_markup": reply_markup}

# Initialize bot features
bot_features = TelegramBotFeatures()

# Handler functions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    user_states[user_id] = {"mode": "main"}
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await bot_features.help_command(update, context)

async def sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sticker command"""
    if context.args:
        text = ' '.join(context.args)
        sticker_bytes = await bot_features.create_sticker(text)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.png")
            )
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
    else:
        await update.message.reply_text("❌ لطفاً متن استیکر را وارد کنید:\nمثال: /sticker سلام دنیا")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "back_to_main":
        await bot_features.start_command(update, context)
        return
    
    elif callback_data == "sticker_pack_menu":
        keyboard = sticker_pack_handler.get_pack_management_keyboard(user_id)
        current_pack = sticker_pack_handler.user_current_pack.get(user_id)
        
        if current_pack and user_id in sticker_pack_handler.user_sticker_packs:
            pack_info = sticker_pack_handler.user_sticker_packs[user_id][current_pack]
            message = f"📦 **مدیریت پک استیکر**\n\n" \
                     f"پک فعلی: {pack_info['title']}\n" \
                     f"تعداد استیکرها: {len(pack_info['stickers'])} 📊\n\n" \
                     f"یکی از گزینه‌ها را انتخاب کنید:"
        else:
            message = "📦 **مدیریت پک استیکر**\n\n" \
                     "شما در حال حاضر هیچ پک فعالی ندارید!\n\n" \
                     "برای شروع، یک پک جدید بسازید:"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard
        )
    
    elif callback_data == "create_new_pack":
        keyboard = [[
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📝 **ساخت پک استیکر جدید**\n\n" \
            "لطفاً نام پک استیکر را وارد کنید (مثلاً: my_custom_pack):\n\n" \
            "سپس عنوان پک را وارد کنید (مثلاً: استیکرهای شخصی من)",
            reply_markup=reply_markup
        )
        
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["waiting_for_pack_name"] = True
    
    elif callback_data == "list_packs":
        packs = await sticker_pack_handler.get_user_packs(user_id)
        
        if not packs:
            keyboard = [[
                InlineKeyboardButton("➕ ساخت پک جدید", callback_data="create_new_pack"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="sticker_pack_menu")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = "📦 **پک‌های استیکر شما**\n\n" \
                     "شما هنوز هیچ پکی نساخته‌اید!"
        else:
            keyboard = sticker_pack_handler.get_packs_list_keyboard(user_id)
            message = "📦 **پک‌های استیکر شما**\n\n" \
                     f"شما {len(packs)} پک دارید:"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard
        )
    
    elif callback_data == "select_current_pack":
        packs = await sticker_pack_handler.get_user_packs(user_id)
        
        if not packs:
            keyboard = [[
                InlineKeyboardButton("➕ ساخت پک جدید", callback_data="create_new_pack"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="sticker_pack_menu")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📦 **انتخاب پک فعلی**\n\n" \
                "شما هنوز هیچ پکی نساخته‌اید!\n\n" \
                "ابتدا یک پک جدید بسازید:",
                reply_markup=reply_markup
            )
        else:
            keyboard = sticker_pack_handler.get_packs_list_keyboard(user_id)
            await query.edit_message_text(
                "📦 **انتخاب پک فعلی**\n\n" \
                "پکی را که می‌خواهید فعال کنید انتخاب کنید:",
                reply_markup=keyboard
            )
    
    elif callback_data.startswith("select_pack_"):
        pack_name = callback_data.replace("select_pack_", "")
        result = await sticker_pack_handler.set_current_pack(user_id, pack_name)
        
        keyboard = sticker_pack_handler.get_pack_management_keyboard(user_id)
        await query.edit_message_text(
            result["message"],
            reply_markup=keyboard
        )
    
    elif callback_data == "pack_info":
        current_pack = sticker_pack_handler.user_current_pack.get(user_id)
        if current_pack and user_id in sticker_pack_handler.user_sticker_packs:
            pack_info = sticker_pack_handler.user_sticker_packs[user_id][current_pack]
            stickers_text = "\n".join([f"• {i+1}. {sticker['emoji']}" for i, sticker in enumerate(pack_info["stickers"])])
            
            if not stickers_text:
                stickers_text = "هنوز استیکری اضافه نشده است"
            
            message = f"📦 **اطلاعات پک: {pack_info['title']}**\n\n" \
                     f"📊 تعداد استیکرها: {len(pack_info['stickers'])}\n" \
                     f"📝 نام پک: {pack_info['name']}\n\n" \
                     f"🎨 استیکرها:\n{stickers_text}\n\n" \
                     f"برای اضافه کردن استیکر جدید، آن را برای ربات ارسال کنید!"
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="sticker_pack_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup
            )
    
    elif callback_data == "help":
        await bot_features.help_command(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Handle pack creation
    if user_id in user_states and user_states[user_id].get("waiting_for_pack_name"):
        parts = text.split('\n')
        if len(parts) >= 2:
            pack_name = parts[0].strip()
            pack_title = parts[1].strip()
            
            result = await sticker_pack_handler.create_new_sticker_pack(user_id, pack_name, pack_title)
            await update.message.reply_text(result["message"])
            
            # Ask for next step or show pack management
            if result["success"]:
                keyboard = sticker_pack_handler.get_pack_management_keyboard(user_id)
                await update.message.reply_text(
                    "حالا استیکرهای خود را برای افزودن به پک ارسال کنید، یا از منوی زیر استفاده کنید:",
                    reply_markup=keyboard
                )
            
            user_states[user_id]["waiting_for_pack_name"] = False
        else:
            await update.message.reply_text(
                "❌ لطفاً نام و عنوان پک را در دو خط جداگانه وارد کنید:\n\n" \
                "مثال:\nmy_pack\nعنوان پک من"
            )
    
    # Handle sticker text
    elif user_id in user_states and user_states[user_id].get("waiting_for_sticker_text"):
        bg_color = user_states[user_id].get("sticker_bg", "white")
        sticker_bytes = await bot_features.create_sticker(text, bg_color)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.png")
            )
            await update.message.reply_text("✅ استیکر شما با موفقیت ساخته شد!")
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
        
        user_states[user_id]["waiting_for_sticker_text"] = False
    
    # Default message
    else:
        await update.message.reply_text(
            "🤖 ربات شما پیام را دریافت کرد! برای دیدن دستورات، /help را وارد کنید.\n\n"
            "دستورات موجود:\n"
            "/start - شروع ربات\n"
            "/help - راهنما\n"
            "/sticker <متن> - ساخت استیکر سریع\n"
            "/pack - مدیریت پک استیکر\n"
            "و بسیار دیگر..."
        )

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sticker messages"""
    user_id = update.effective_user.id
    sticker = update.message.sticker
    
    # Try to add sticker to current pack
    sticker_data = {
        "file_id": sticker.file_id,
        "emoji": "😊"  # Default emoji, you could ask user for this
    }
    
    result = await sticker_pack_handler.add_sticker_to_pack(user_id, sticker_data)
    await update.message.reply_text(result["message"])

def setup_application(application):
    """Setup all handlers for the application"""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sticker", sticker_command))
    application.add_handler(CommandHandler("pack", lambda u, c: button_callback(u, c)))
    
    # Callback and message handlers
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.STICKER, handle_sticker))

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
        application = None
else:
    logger.error("No Telegram token found in environment variables")

# Import Flask
from flask import Flask, request, jsonify

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running! All handlers are active."

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == 'POST':
        try:
            update_data = request.get_json()
            logger.info(f"Received webhook data: {update_data}")
            
            if application:
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)
            else:
                logger.warning("Telegram application not initialized")

            return jsonify({"status": "ok"}), 200
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error"}), 400

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "handlers": "active", "telegram_app": application is not None})

# For local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))