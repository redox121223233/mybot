import requests
from bs4 import BeautifulSoup
import random
import json
import os
from datetime import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import CallbackContext
import tempfile
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageColor
import io

class TelegramBotFeatures:
    def __init__(self):
        self.user_data = {}
        self.api_key = os.getenv('API_KEY', 'your_default_api_key')

    async def start_command(self, update: Update, context: CallbackContext):
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

    async def help_command(self, update: Update, context: CallbackContext):
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
            img.save(img_bytes, format='PNG')
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

    async def custom_sticker_menu(self):
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
        return {
            "message": "🎨 **استیکر ساز سفارشی**\n\nلطفاً رنگ پس‌زمینه را انتخاب کنید:",
            "reply_markup": reply_markup
        }

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

# ایجاد نمونه از کلاس
bot_features = TelegramBotFeatures()