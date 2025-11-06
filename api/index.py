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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, StickerSet
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
• 🔢 حدس عدد - یک عدد بین ۱ تا ۱۰۰ را حدس بزنید
• ✂️ سنگ کاغذ قیچی - بازی کلاسیک
• 📝 بازی کلمات - حدس کلمات
• 🧠 بازی حافظه - تست حافظه شما
• 🎲 بازی تصادفی - شانس خود را امتحان کنید

🎨 **سازنده استیکر:**
• 🖼️ استیکر سریع با دستور /sticker <متن>
• 🎨 استیکر سفارشی با دستور /customsticker

📚 **راهنما:**
/help - دیدن تمام دستورات

انتخاب کنید:
"""
        
        keyboard = [
            [InlineKeyboardButton("🔢 حدس عدد", callback_data="guess_number")],
            [InlineKeyboardButton("✂️ سنگ کاغذ قیچی", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("📝 بازی کلمات", callback_data="word_game")],
            [InlineKeyboardButton("🧠 بازی حافظه", callback_data="memory_game")],
            [InlineKeyboardButton("🎲 بازی تصادفی", callback_data="random_game")],
            [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator")],
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

💬 **سایر:**
/start - منوی اصلی
/help - این راهنما

مثال استیکر:
/sticker سلام دنیا! 🌍

❓ برای هر سوالی از منوی اصلی استفاده کنید!"""
        
        await update.message.reply_text(help_text)
    
    async def create_sticker_webp(self, text, bg_color="white"):
        """Create a WebP sticker for Telegram"""
        try:
            # Create image with RGBA (transparency support)
            img_size = (512, 512)
            img = Image.new('RGBA', img_size, bg_color)
            draw = ImageDraw.Draw(img)

            # Try to use default font with larger size
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 60)
                except:
                    font = ImageFont.load_default()

            # Split text into multiple lines if needed
            words = text.split()
            lines = []
            current_line = []

            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < 450:  # Max width
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)

            if current_line:
                lines.append(' '.join(current_line))

            # Calculate total height
            line_height = 70
            total_height = len(lines) * line_height
            start_y = (img_size[1] - total_height) // 2

            # Draw text with shadow for better visibility
            text_color = "black" if bg_color in ["white", "#f1c40f", "#2ecc71"] else "white"
            shadow_color = "white" if text_color == "black" else "black"

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (img_size[0] - text_width) // 2
                y = start_y + i * line_height

                # Draw shadow
                draw.text((x + 2, y + 2), line, fill=shadow_color, font=font)
                # Draw text
                draw.text((x, y), line, fill=text_color, font=font)

            # Save as WebP format (required by Telegram for stickers)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='WEBP', quality=95)
            img_bytes.seek(0)

            return img_bytes

        except Exception as e:
            logger.error(f"Error creating sticker: {e}")
            return None

    async def create_sticker_png(self, text, bg_color="white"):
        """Create a PNG sticker (fallback)"""
        try:
            img_size = (512, 512)
            img = Image.new('RGBA', img_size, bg_color)
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 60)
                except:
                    font = ImageFont.load_default()

            words = text.split()
            lines = []
            current_line = []

            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < 450:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)

            if current_line:
                lines.append(' '.join(current_line))

            line_height = 70
            total_height = len(lines) * line_height
            start_y = (img_size[1] - total_height) // 2

            text_color = "black" if bg_color in ["white", "#f1c40f", "#2ecc71"] else "white"
            shadow_color = "white" if text_color == "black" else "black"

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (img_size[0] - text_width) // 2
                y = start_y + i * line_height

                draw.text((x + 2, y + 2), line, fill=shadow_color, font=font)
                draw.text((x, y), line, fill=text_color, font=font)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            return img_bytes

        except Exception as e:
            logger.error(f"Error creating PNG sticker: {e}")
            return None
    
    async def guess_number_game(self):
        """Setup guess number game"""
        number = random.randint(1, 100)
        self.user_data['guess_number'] = number
        self.user_data['guess_attempts'] = 0
        
        keyboard = [
            [InlineKeyboardButton("💭 حدس بزن", callback_data="guess_prompt")],
            [InlineKeyboardButton("💡 راهنمایی", callback_data="guess_hint")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        message = "🔢 **بازی حدس عدد!**\n\nمن یک عدد بین ۱ تا ۱۰۰ انتخاب کردم. حدس شما چیه؟"
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return {"message": message, "reply_markup": reply_markup}
    
    async def check_guess(self, guess):
        """Check user's guess"""
        if 'guess_number' not in self.user_data:
            return {"message": "بازی شروع نشده! /guess رو بزنید", "reply_markup": None}
        
        number = self.user_data['guess_number']
        self.user_data['guess_attempts'] += 1
        attempts = self.user_data['guess_attempts']
        
        keyboard = [
            [InlineKeyboardButton("💭 حدس دوباره", callback_data="guess_prompt")],
            [InlineKeyboardButton("💡 راهنمایی", callback_data="guess_hint")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if guess == number:
            message = f"🎉 **آفرین!**\n\nعدد {number} بود!\nتعداد تلاش‌ها: {attempts}"
            del self.user_data['guess_number']
            del self.user_data['guess_attempts']
            keyboard = [[InlineKeyboardButton("🎮 بازی دوباره", callback_data="guess_number")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        elif guess < number:
            message = f"📈 **برو بالاتر!**\n\nحدس شما ({guess}) کوچکتره\nتعداد تلاش‌ها: {attempts}"
        else:
            message = f"📉 **برو پایین‌تر!**\n\nحدس شما ({guess}) بزرگتره\nتعداد تلاش‌ها: {attempts}"
        
        return {"message": message, "reply_markup": reply_markup}
    
    async def rock_paper_scissors_game(self):
        """Setup rock paper scissors game"""
        keyboard = [
            [
                InlineKeyboardButton("✊ سنگ", callback_data="rps_choice_rock"),
                InlineKeyboardButton("📄 کاغذ", callback_data="rps_choice_paper"),
                InlineKeyboardButton("✂️ قیچی", callback_data="rps_choice_scissors")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        message = "✂️ **سنگ کاغذ قیچی!**\n\nانتخاب کنید:"
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return {"message": message, "reply_markup": reply_markup}
    
    async def check_rps_choice(self, user_choice):
        """Check RPS choice"""
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)
        
        choice_emoji = {"rock": "✊", "paper": "📄", "scissors": "✂️"}
        choice_text = {"rock": "سنگ", "paper": "کاغذ", "scissors": "قیچی"}
        
        user_emoji = choice_emoji[user_choice]
        bot_emoji = choice_emoji[bot_choice]
        
        keyboard = [
            [InlineKeyboardButton("🎮 بازی دوباره", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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
        
        message = f"{result}\n\nشما: {user_emoji} {choice_text[user_choice]}\nمن: {bot_emoji} {choice_text[bot_choice]}"
        
        return {"message": message, "reply_markup": reply_markup}
    
    async def word_game(self):
        """Setup word game"""
        words = ["پرتقال", "موز", "سیب", "هلو", "انگور", "توت", "گیلاس", "آلبالو"]
        word = random.choice(words)
        self.user_data['word_game'] = {'word': word, 'attempts': 0, 'max_attempts': 6}
        
        display = "_ " * len(word)
        
        keyboard = [
            [InlineKeyboardButton("💡 راهنمایی", callback_data="word_hint")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        message = f"📝 **بازی کلمات!**\n\nکلمه: {display}\nتعداد حدس‌ها: 6"
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return {"message": message, "reply_markup": reply_markup}
    
    async def memory_game(self):
        """Setup memory game"""
        # Simple memory game implementation
        numbers = [str(random.randint(1, 9)) for _ in range(5)]
        self.user_data['memory_game'] = {'sequence': numbers, 'showing': True}
        
        sequence_str = " - ".join(numbers)
        
        message = f"🧠 **بازی حافظه!**\n\nاین اعداد رو حفظ کن:\n{sequence_str}\n\n5 ثانیه فرصت داری!"
        reply_markup = None
        
        return {"message": message, "reply_markup": reply_markup}
    
    async def random_game(self):
        """Setup random game"""
        games = [
            {"name": "تاس", "emoji": "🎲", "result": str(random.randint(1, 6))},
            {"name": "شیر یا خط", "emoji": "🪙", "result": random.choice(["شیر", "خط"])},
            {"name": "کارت", "emoji": "🃏", "result": random.choice(["آس", "شاه", "بیبی", "دو", "سه", "چهار"])},
        ]
        
        selected = random.choice(games)
        
        keyboard = [
            [InlineKeyboardButton("🎲 دوباره", callback_data="random_game")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        message = f"🎲 **بازی تصادفی!**\n\n{selected['emoji']} {selected['name']}\nنتیجه: {selected['result']}"
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return {"message": message, "reply_markup": reply_markup}
    
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
    """Handle /sticker command with sticker pack support"""
    if context.args:
        text = ' '.join(context.args)
        user_id = update.effective_user.id

        # Create sticker in WebP format
        sticker_webp = await bot_features.create_sticker_webp(text)

        if sticker_webp:
            try:
                # Try to add to sticker pack
                pack_name = f"user_{user_id}_pack_by_{context.bot.username}"
                pack_title = f"استیکرهای {update.effective_user.first_name}"

                sticker_webp.seek(0)

                # Try to get existing sticker set
                try:
                    sticker_set = await context.bot.get_sticker_set(pack_name)
                    # Add to existing set
                    await context.bot.add_sticker_to_set(
                        user_id=user_id,
                        name=pack_name,
                        sticker=InputFile(sticker_webp, filename="sticker.webp"),
                        emojis="😊"
                    )
                    await update.message.reply_text(
                        f"✅ استیکر به پک اضافه شد!\n\n"
                        f"🔗 لینک پک: https://t.me/addstickers/{pack_name}"
                    )
                except TelegramError as e:
                    # Pack doesn't exist, create new one
                    if "STICKERSET_INVALID" in str(e) or "not found" in str(e).lower():
                        sticker_webp.seek(0)
                        await context.bot.create_new_sticker_set(
                            user_id=user_id,
                            name=pack_name,
                            title=pack_title,
                            stickers=[
                                {
                                    "sticker": InputFile(sticker_webp, filename="sticker.webp"),
                                    "emoji_list": ["😊"]
                                }
                            ]
                        )
                        await update.message.reply_text(
                            f"✅ پک استیکر جدید ساخته شد!\n\n"
                            f"🔗 لینک پک: https://t.me/addstickers/{pack_name}"
                        )
                    else:
                        # Other error, send as regular sticker
                        logger.error(f"Sticker pack error: {e}")
                        sticker_webp.seek(0)
                        await update.message.reply_document(
                            document=InputFile(sticker_webp, filename="sticker.webp"),
                            caption="⚠️ نتوانستم به پک اضافه کنم. استیکر به صورت فایل ارسال شد."
                        )

            except Exception as e:
                logger.error(f"Error adding to sticker pack: {e}")
                # Fallback: send as image
                sticker_png = await bot_features.create_sticker_png(text)
                if sticker_png:
                    sticker_png.seek(0)
                    await update.message.reply_photo(
                        photo=InputFile(sticker_png, filename="sticker.png"),
                        caption="⚠️ خطا در افزودن به پک. تصویر به صورت عکس ارسال شد."
                    )
                else:
                    await update.message.reply_text("❌ خطا در ساخت استیکر!")
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
    else:
        await update.message.reply_text("❌ لطفاً متن استیکر را وارد کنید:\nمثال: /sticker سلام دنیا")

async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /guess command"""
    game_data = await bot_features.guess_number_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def rps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rps command"""
    game_data = await bot_features.rock_paper_scissors_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /word command"""
    game_data = await bot_features.word_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /memory command"""
    game_data = await bot_features.memory_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /random command"""
    game_data = await bot_features.random_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def customsticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /customsticker command"""
    menu_data = await bot_features.custom_sticker_menu()
    await update.message.reply_text(
        menu_data["message"],
        reply_markup=menu_data["reply_markup"]
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "back_to_main":
        await bot_features.start_command(update, context)
        return
    
    elif callback_data == "guess_number":
        game_data = await bot_features.guess_number_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "guess_prompt":
        keyboard = [[
            InlineKeyboardButton("ارسال عدد", callback_data="guess_send_number")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔢 لطفاً عدد مورد نظر خود را به صورت پیام متنی ارسال کنید (بین 1 تا 100):",
            reply_markup=reply_markup
        )
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["waiting_for_guess"] = True
    
    elif callback_data == "guess_hint":
        if 'guess_number' in bot_features.user_data:
            number = bot_features.user_data['guess_number']
            hint = "بزرگتر از 50" if number > 50 else "کوچکتر از 50"
            await query.edit_message_text(
                f"💡 **راهنمایی:** عدد {hint} است!\n\nدوباره تلاش کنید:",
                reply_markup=query.message.reply_markup
            )
    
    elif callback_data == "rock_paper_scissors":
        game_data = await bot_features.rock_paper_scissors_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data.startswith("rps_choice_"):
        user_choice = callback_data.replace("rps_choice_", "")
        result = await bot_features.check_rps_choice(user_choice)
        await query.edit_message_text(
            result["message"],
            reply_markup=result["reply_markup"]
        )
    
    elif callback_data == "word_game":
        game_data = await bot_features.word_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "word_hint":
        if 'word_game' in bot_features.user_data:
            word = bot_features.user_data['word_game']['word']
            first_letter = word[0]
            last_letter = word[-1]
            await query.edit_message_text(
                f"💡 **راهنمایی:**\n\nحرف اول: {first_letter}\nحرف آخر: {last_letter}\n\nتعداد حروف: {len(word)}",
                reply_markup=query.message.reply_markup
            )
    
    elif callback_data == "memory_game":
        game_data = await bot_features.memory_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "random_game":
        game_data = await bot_features.random_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "sticker_creator":
        menu_data = await bot_features.custom_sticker_menu()
        await query.edit_message_text(
            menu_data["message"],
            reply_markup=menu_data["reply_markup"]
        )
    
    elif callback_data.startswith("sticker_bg_"):
        color = callback_data.replace("sticker_bg_", "")
        color_map = {
            "white": "white",
            "black": "black", 
            "blue": "#3498db",
            "red": "#e74c3c",
            "green": "#2ecc71",
            "yellow": "#f1c40f"
        }
        
        bg_color = color_map.get(color, "white")
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["sticker_bg"] = bg_color
        
        keyboard = [[
            InlineKeyboardButton("✏️ نوشتن متن", callback_data="sticker_text")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ رنگ پس‌زمینه انتخاب شد!\n\nحالا متن استیکر خود را بنویسید:",
            reply_markup=reply_markup
        )
    
    elif callback_data == "sticker_text":
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["waiting_for_sticker_text"] = True
        
        await query.edit_message_text(
            "✏️ لطفاً متن مورد نظر خود را برای استیکر بنویسید:"
        )
    
    elif callback_data == "help":
        await bot_features.help_command(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Handle waiting for guess
    if user_id in user_states and user_states[user_id].get("waiting_for_guess"):
        try:
            guess = int(text)
            if 1 <= guess <= 100:
                result = await bot_features.check_guess(guess)
                await update.message.reply_text(
                    result["message"],
                    reply_markup=result["reply_markup"]
                )
                user_states[user_id]["waiting_for_guess"] = False
            else:
                await update.message.reply_text("❌ لطفاً عددی بین 1 تا 100 وارد کنید!")
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد صحیح وارد کنید!")
    
    # Handle waiting for sticker text
    elif user_id in user_states and user_states[user_id].get("waiting_for_sticker_text"):
        bg_color = user_states[user_id].get("sticker_bg", "white")
        sticker_webp = await bot_features.create_sticker_webp(text, bg_color)

        if sticker_webp:
            try:
                pack_name = f"user_{user_id}_pack_by_{context.bot.username}"
                pack_title = f"استیکرهای {update.effective_user.first_name}"

                sticker_webp.seek(0)

                try:
                    sticker_set = await context.bot.get_sticker_set(pack_name)
                    await context.bot.add_sticker_to_set(
                        user_id=user_id,
                        name=pack_name,
                        sticker=InputFile(sticker_webp, filename="sticker.webp"),
                        emojis="😊"
                    )
                    await update.message.reply_text(
                        f"✅ استیکر با رنگ {bg_color} به پک اضافه شد!\n\n"
                        f"🔗 لینک پک: https://t.me/addstickers/{pack_name}"
                    )
                except TelegramError as e:
                    if "STICKERSET_INVALID" in str(e) or "not found" in str(e).lower():
                        sticker_webp.seek(0)
                        await context.bot.create_new_sticker_set(
                            user_id=user_id,
                            name=pack_name,
                            title=pack_title,
                            stickers=[
                                {
                                    "sticker": InputFile(sticker_webp, filename="sticker.webp"),
                                    "emoji_list": ["😊"]
                                }
                            ]
                        )
                        await update.message.reply_text(
                            f"✅ پک استیکر جدید ساخته شد!\n\n"
                            f"🔗 لینک پک: https://t.me/addstickers/{pack_name}"
                        )
                    else:
                        logger.error(f"Sticker pack error: {e}")
                        sticker_webp.seek(0)
                        await update.message.reply_document(
                            document=InputFile(sticker_webp, filename="sticker.webp"),
                            caption="⚠️ نتوانستم به پک اضافه کنم. استیکر به صورت فایل ارسال شد."
                        )

            except Exception as e:
                logger.error(f"Error in custom sticker: {e}")
                sticker_png = await bot_features.create_sticker_png(text, bg_color)
                if sticker_png:
                    sticker_png.seek(0)
                    await update.message.reply_photo(
                        photo=InputFile(sticker_png, filename="sticker.png"),
                        caption="⚠️ خطا در افزودن به پک. تصویر به صورت عکس ارسال شد."
                    )
                else:
                    await update.message.reply_text("❌ خطا در ساخت استیکر!")
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
            "/guess - بازی حدس عدد\n"
            "/rps - سنگ کاغذ قیچی\n"
            "/word - بازی کلمات\n"
            "/memory - بازی حافظه\n"
            "/random - بازی تصادفی\n"
            "/sticker <متن> - ساخت استیکر سریع\n"
            "/customsticker - استیکر ساز سفارشی\n"
            "و بسیار دیگر..."
        )

def setup_application(application):
    """Setup all handlers for the application"""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sticker", sticker_command))
    application.add_handler(CommandHandler("guess", guess_command))
    application.add_handler(CommandHandler("rps", rps_command))
    application.add_handler(CommandHandler("word", word_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("customsticker", customsticker_command))
    
    # Callback and message handlers
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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