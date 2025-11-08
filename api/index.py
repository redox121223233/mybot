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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageColor
import http.server
import socketserver
import threading

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
        welcome_message = """
🎮 **به ربات بازی و استیکر ساز خوش آمدید!** 🎨

من یک ربات ساده با قابلیت‌های زیر هستم:

🎮 **بازی‌ها:**
• 🎯 حدس عدد
• ✂️ سنگ کاغذ قیچی
• 📝 بازی کلمات
• 🧠 بازی حافظه

🎨 **استیکر ساز:**
• 📸 ساخت استیکر متنی
• 🎨 انتخاب رنگ و فونت
• ⚡ ساخت سریع استیکر

برای شروع، یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎯 حدس عدد", callback_data="guess_number"),
             InlineKeyboardButton("✂️ سنگ کاغذ قیچی", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("📝 بازی کلمات", callback_data="word_game"),
             InlineKeyboardButton("🧠 بازی حافظه", callback_data="memory_game")],
            [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator"),
             InlineKeyboardButton("🎲 بازی تصادفی", callback_data="random_game")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 **راهنمای کامل ربات:**

🎯 **حدس عدد:**
• /guess - شروع بازی حدس عدد

✂️ **سنگ کاغذ قیچی:**
• /rps - شروع بازی سنگ کاغذ قیچی

📝 **بازی کلمات:**
• /word - شروع بازی با کلمات

🧠 **بازی حافظه:**
• /memory - شروع بازی حافظه

🎨 **استیکر ساز:**
• /sticker <متن> - ساخت استیکر متنی
• /customsticker - ساخت استیکر سفارشی

🎲 **بازی تصادفی:**
• /random - بازی تصادفی

برای هر دستور می‌توانید از منوی هم استفاده کنید!
        """
        await update.message.reply_text(help_text)
    
    async def create_sticker(self, text: str, bg_color: str = "white", font_size: int = 40, text_color: str = "black"):
        try:
            # ایجاد تصویر استیکر
            img = Image.new('RGBA', (512, 512), bg_color)
            draw = ImageDraw.Draw(img)
            
            # تلاش برای استفاده از فونت فارسی
            try:
                # تلاش برای فونت‌های مختلف
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Arial.ttf",
                    "arial.ttf"
                ]
                font = None
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue

                if font is None:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # محاسبه موقعیت متن
            lines = []
            words = text.split()
            current_line = []

            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < 400:  # عرض مجاز
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)

            if current_line:
                lines.append(' '.join(current_line))
            
            # رسم متن
            total_height = len(lines) * (font_size + 10)
            start_y = (512 - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (512 - text_width) // 2
                y = start_y + i * (font_size + 10)

                # افزودن سایه برای خوانایی بهتر
                draw.text((x + 2, y + 2), line, fill="gray", font=font)
                draw.text((x, y), line, fill=text_color, font=font)
            
            # ذخیره تصویر
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='WEBP')
            img_bytes.seek(0)
            
            return img_bytes
        except Exception as e:
            print(f"Error creating sticker: {e}")
            return None
    
    async def guess_number_game(self):
        number = random.randint(1, 100)
        self.user_data['guess_number'] = number
        self.user_data['guess_attempts'] = 0
        
        keyboard = [
            [InlineKeyboardButton("🎯 حدس بزن", callback_data="guess_prompt")],
            [InlineKeyboardButton("🔢 راهنمایی", callback_data="guess_hint")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return {
            "message": f"🎯 **بازی حدس عدد شروع شد!**\n\nمن یک عدد بین 1 تا 100 انتخاب کردم.\nتلاش کن حدس بزنی!\n\nتعداد تلاش‌ها: {self.user_data['guess_attempts']}",
            "reply_markup": reply_markup
        }
    
    async def check_guess(self, guess: int):
        if 'guess_number' not in self.user_data:
            return {"message": "❌ بازی شروع نشده! لطفاً دوباره بازی را شروع کنید."}
        
        self.user_data['guess_attempts'] += 1
        number = self.user_data['guess_number']
        attempts = self.user_data['guess_attempts']
        
        keyboard = [
            [InlineKeyboardButton("🎯 حدس بعدی", callback_data="guess_prompt")],
            [InlineKeyboardButton("🔢 راهنمایی", callback_data="guess_hint")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if guess == number:
            del self.user_data['guess_number']
            del self.user_data['guess_attempts']
            return {
                "message": f"🎉 **تبریک! برنده شدی!**\n\nعدد صحیح {number} بود!\nتعداد تلاش‌ها: {attempts}",
                "reply_markup": reply_markup
            }
        elif guess < number:
            return {
                "message": f"📈 **بالاتر برو!**\n\nعدد بزرگتری انتخاب کن!\nتعداد تلاش‌ها: {attempts}",
                "reply_markup": reply_markup
            }
        else:
            return {
                "message": f"📉 **پایینتر بیا!**\n\nعدد کوچکتری انتخاب کن!\nتعداد تلاش‌ها: {attempts}",
                "reply_markup": reply_markup
            }
    
    async def rock_paper_scissors_game(self):
        choices = ["سنگ", "کاغذ", "قیچی"]
        bot_choice = random.choice(choices)
        self.user_data['rps_bot_choice'] = bot_choice
        
        keyboard = []
        for choice in choices:
            keyboard.append([InlineKeyboardButton(choice, callback_data=f"rps_choice_{choice}")])
        keyboard.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return {
            "message": "✂️ **سنگ کاغذ قیچی**\n\nانتخاب خود را انجام دهید:",
            "reply_markup": reply_markup
        }
    
    async def check_rps_choice(self, user_choice: str):
        if 'rps_bot_choice' not in self.user_data:
            return {"message": "❌ بازی شروع نشده! لطفاً دوباره بازی را شروع کنید."}
        
        bot_choice = self.user_data['rps_bot_choice']
        del self.user_data['rps_bot_choice']
        
        keyboard = [
            [InlineKeyboardButton("🔄 بازی دوباره", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if user_choice == bot_choice:
            return {
                "message": f"🤝 **مساوی!**\n\nشما: {user_choice}\nربات: {bot_choice}",
                "reply_markup": reply_markup
            }
        elif (
            (user_choice == "سنگ" and bot_choice == "قیچی") or
            (user_choice == "کاغذ" and bot_choice == "سنگ") or
            (user_choice == "قیچی" and bot_choice == "کاغذ")
        ):
            return {
                "message": f"🎉 **شما برنده شدید!**\n\nشما: {user_choice}\nربات: {bot_choice}",
                "reply_markup": reply_markup
            }
        else:
            return {
                "message": f"😔 **ربات برنده شد!**\n\nشما: {user_choice}\nربات: {bot_choice}",
                "reply_markup": reply_markup
            }
    
    async def word_game(self):
        words = [
            {"word": "پردیس", "hint": "نام یک دانشگاه در تهران"},
            {"word": "رود", "hint": "آب در حال حرکت"},
            {"word": "کتاب", "hint": "وسیله مطالعه"},
            {"word": "شمشیر", "hint": "سلاح سرد"},
            {"word": "آفتاب", "hint": "منبع نور و گرما"},
        ]
        
        word_data = random.choice(words)
        self.user_data['word_game'] = word_data

        # نمایش کلمه با حروف مخفی
        hidden_word = " ".join(["_" if char != " " else " " for char in word_data["word"]])
        
        keyboard = [
            [InlineKeyboardButton("🔤 حدس حرف", callback_data="word_guess_letter")],
            [InlineKeyboardButton("💡 راهنمایی", callback_data="word_hint")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return {
            "message": f"📝 **بازی کلمات**\n\nکلمه: {hidden_word}\n\nراهنمایی: {word_data['hint']}\n\nحدس حرف مورد نظر خود را بزنید:",
            "reply_markup": reply_markup
        }
    
    async def memory_game(self):
        # ایجاد کارت‌های حافظه
        symbols = ["🎮", "🎨", "🎯", "🎲", "🎪", "🎭", "🎸", "🎺"]
        cards = symbols * 2
        random.shuffle(cards)
        
        self.user_data['memory_game'] = {
            "cards": cards,
            "revealed": [False] * len(cards),
            "matched": [False] * len(cards),
            "attempts": 0
        }
        
        # نمایش کارت‌ها
        board = ""
        for i in range(0, len(cards), 4):
            row = ""
            for j in range(4):
                if i + j < len(cards):
                    row += f"❓{i+j+1} " if i + j < 9 else f"❓{i+j+1} "
            board += row + "\n"
        
        keyboard = [
            [InlineKeyboardButton("🔍 انتخاب کارت", callback_data="memory_pick_card")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return {
            "message": f"🧠 **بازی حافظه**\n\n{board}\n\nتعداد تلاش‌ها: {self.user_data['memory_game']['attempts']}\n\nکارت مورد نظر خود را انتخاب کنید (1-16):",
            "reply_markup": reply_markup
        }

    async def custom_sticker_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("⚪ سفید", callback_data="sticker_bg_white"),
             InlineKeyboardButton("⚫ مشکی", callback_data="sticker_bg_black")],
            [InlineKeyboardButton("🔵 آبی", callback_data="sticker_bg_blue"),
             InlineKeyboardButton("🔴 قرمز", callback_data="sticker_bg_red")],
            [InlineKeyboardButton("🟢 سبز", callback_data="sticker_bg_green"),
             InlineKeyboardButton("🟡 زرد", callback_data="sticker_bg_yellow")],
            [InlineKeyboardButton("✏️ نوشتن متن", callback_data="sticker_text")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "🎨 **استیکر ساز سفارشی**\n\nلطفاً رنگ پس‌زمینه را انتخاب کنید:",
            reply_markup=reply_markup
        )
    
    async def random_game(self):
        games = [
            ("🎯 حدس عدد", "guess_number"),
            ("✂️ سنگ کاغذ قیچی", "rock_paper_scissors"),
            ("📝 بازی کلمات", "word_game"),
            ("🧠 بازی حافظه", "memory_game")
        ]

        game_name, game_callback = random.choice(games)

        keyboard = [
            [InlineKeyboardButton(f"🎲 {game_name}", callback_data=game_callback)],
            [InlineKeyboardButton("🔄 بازی دیگر", callback_data="random_game")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return {
            "message": f"🎲 **بازی تصادفی انتخاب شد:**\n\n{game_name}\n\nبرای شروع بازی کلیک کنید:",
            "reply_markup": reply_markup
        }

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
                sticker=InputFile(sticker_bytes, filename="sticker.webp")
            )
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
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["waiting_for_pack_name"] = True
        await query.edit_message_text("لطفا نام پک استیکر خود را وارد کنید:")
    
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
        user_states[user_id]["sticker_bg"] = bg_.color
        
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
    
    if user_id in user_states and user_states[user_id].get("waiting_for_pack_name"):
        user_states[user_id]["pack_name"] = text
        user_states[user_id]["waiting_for_pack_name"] = False
        await bot_features.custom_sticker_menu(update, context)

    # Handle waiting for guess
    elif user_id in user_states and user_states[user_id].get("waiting_for_guess"):
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
        sticker_bytes = await bot_features.create_sticker(text, bg_color)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            pack_name = user_states[user_id].get("pack_name")
            bot_username = (await context.bot.get_me()).username
            full_pack_name = f"{pack_name}_by_{bot_username}"

            try:
                await context.bot.add_sticker_to_set(
                    user_id=user_id,
                    name=full_pack_name,
                    sticker={'sticker': sticker_bytes, 'emoji_list': ["❤️‍🔥"]}
                )
                await update.message.reply_text("✅ استیکر شما با موفقیت به پک اضافه شد!")
            except Exception as e:
                logger.error(f"Error adding sticker to set: {e}")
                sticker_bytes.seek(0)
                try:
                    await context.bot.create_new_sticker_set(
                        user_id=user_id,
                        name=full_pack_name,
                        title=pack_name,
                        stickers=[{'sticker': sticker_bytes, 'emoji_list': ["❤️‍🔥"]}],
                        sticker_format="static"
                    )
                    await update.message.reply_text("✅ پک استیکر شما با موفقیت ساخته شد و استیکر شما به آن اضافه شد!")
                except Exception as e2:
                    logger.error(f"Error creating new sticker set: {e2}")
                    await update.message.reply_text("❌ خطا در ساخت پک استیکر یا اضافه کردن استیکر به آن!")
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
        
        user_states[user_id]["waiting_for_sticker_text"] = False
    
    # Handle quick sticker command
    elif text.startswith("/sticker "):
        sticker_text = text.replace("/sticker ", "")
        sticker_bytes = await bot_features.create_sticker(sticker_text)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.webp")
            )
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
    
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
class VercelHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        try:
            update_data = json.loads(body.decode('utf-8'))
            logger.info(f"Received webhook data: {update_data}")
            
            if application:
                asyncio.run(self.process_update(update_data))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            else:
                logger.warning("Telegram application not initialized")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Application not initialized"}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

    async def process_update(self, update_data):
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello, world!")
