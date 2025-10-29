"""
Bot Features with Glassmorphism Design
تبدیل ربات به طراحی شیشه‌ای مدرن
"""
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display
import re

logger = logging.getLogger(__name__)

# Global user data storage
user_data = {}

def _prepare_text(text: str) -> str:
    """آماده‌سازی متن فارسی برای نمایش صحیح"""
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def _create_glassmorphism_bg(size=(512, 512), color_scheme="blue") -> Image.Image:
    """ایجاد پس‌زمینه شیشه‌ای با گرادیانت"""
    w, h = size
    
    # طرح‌های رنگی مختلف
    schemes = {
        "blue": [(56, 189, 248), (99, 102, 241)],
        "purple": [(147, 51, 234), (79, 70, 229)],
        "green": [(34, 197, 94), (16, 185, 129)],
        "red": [(244, 63, 94), (239, 68, 68)],
        "orange": [(251, 146, 60), (245, 158, 11)],
        "pink": [(236, 72, 153), (219, 39, 119)]
    }
    
    top_color, bottom_color = schemes.get(color_scheme, schemes["blue"])
    
    # ایجاد پس‌زمینه گرادیانتی
    img = Image.new("RGBA", size, (20, 20, 35, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        t = y / (h - 1)
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
    
    # افزودن افکت شیشه‌ای
    img = img.filter(ImageFilter.GaussianBlur(1))
    
    # افزودن لایه شیشه‌ای
    glass_layer = Image.new("RGBA", size, (255, 255, 255, 15))
    img.paste(glass_layer, (0, 0), glass_layer)
    
    return img

def _create_stylish_text_image(text: str, color_scheme="blue", font_size=48) -> Image.Image:
    """ایجاد تصویر متنی با استایل مدرن"""
    if not text:
        text = "Hello!"
    
    bg = _create_glassmorphism_bg(color_scheme=color_scheme)
    draw = ImageDraw.Draw(bg)
    
    # تلاش برای بارگذاری فونت فارسی
    try:
        font = ImageFont.truetype("fonts/Vazirmatn-Regular.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # آماده‌سازی متن فارسی
    prepared_text = _prepare_text(text)
    
    # محاسبه موقعیت متن
    bbox = draw.textbbox((0, 0), prepared_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    # رسم متن با سایه
    draw.text((x+2, y+2), prepared_text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), prepared_text, font=font, fill=(255, 255, 255, 255))
    
    return bg

def create_glassmorphism_keyboard(buttons_data, color_scheme="blue"):
    """ایجاد کیبورد شیشه‌ای"""
    keyboard = []
    
    # طرح‌های رنگی برای دکمه‌ها
    button_colors = {
        "blue": "🔵",
        "purple": "🟣", 
        "green": "🟢",
        "red": "🔴",
        "orange": "🟠",
        "pink": "🩷"
    }
    
    color_emoji = button_colors.get(color_scheme, "🔵")
    
    for row_data in buttons_data:
        row = []
        for button_text, callback_data in row_data:
            # افزودن ایموجی رنگی به ابتدای دکمه
            styled_text = f"{color_emoji} {button_text}"
            row.append(InlineKeyboardButton(styled_text, callback_data=callback_data))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# Functions for existing features
async def start_command(update: Update, context: CallbackContext) -> None:
    """دستور /start با طراحی شیشه‌ای"""
    welcome_text = """
🌟 **به ربات استیکر ساز شیشه‌ای خوش آمدید!**

✨ با طراحی مدرن و زیبا
🎨 امکانات بی‌نظیر و خلاقانه
🚀 سرعت و کیفیت بالا

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
    """
    
    buttons_data = [
        [("🎮 شروع بازی‌ها", "start_games"), ("🎨 ساخت استیکر", "create_sticker")],
        [("📚 راهنما", "help_command"), ("⚙️ تنظیمات", "settings")],
        [("🎲 بازی تصادفی", "random_game"), ("🏆 امتیازات", "scores")],
        [("🔙 بازگشت به منو", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "blue")
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: CallbackContext) -> None:
    """دستور /help با طراحی شیشه‌ای"""
    help_text = """
📖 **راهنمای ربات شیشه‌ای**

🎮 **بازی‌ها:**
• حدس عدد - حدس عدد مورد نظر ربات
• سنگ کاغذ قیچی - بازی کلاسیک
• بازی کلمات - چالش هوش
• بازی حافظه - تقویت حافظه

🎨 **ساخت استیکر:**
• استیکر متنی - با متن دلخواه شما
• استیکر رنگی - با طرح‌های زیبا
• استیکر شخصی‌سازی شده

⚙️ **امکانات:**
• سرعت بالا
• طراحی مدرن
• رابط کاربری ساده
• پشتیبانی 24/7

❓ **سوال دارید؟**
از دکمه راهنما استفاده کنید یا با پشتیبانی تماس بگیرید.
    """
    
    buttons_data = [
        [("🎮 بازی‌ها", "games_menu"), ("🎨 استیکرها", "stickers_menu")],
        [("🏠 منوی اصلی", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "green")
    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def create_sticker(text: str, color_scheme="blue"):
    """ساخت استیکر با طراحی شیشه‌ای"""
    try:
        # ساخت تصویر با طراحی شیشه‌ای
        sticker_img = _create_stylish_text_image(text, color_scheme)
        
        # تبدیل به فرمت WEBP برای تلگرام
        buffer = BytesIO()
        sticker_img.save(buffer, format='WEBP')
        buffer.seek(0)
        
        return buffer
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return None

async def sticker_color_menu():
    """منوی انتخاب رنگ استیکر"""
    text = """
🎨 **انتخاب طرح رنگی استیکر**

طرح مورد نظر خود را انتخاب کنید:
    """
    
    buttons_data = [
        [("🔵 آبی", "sticker_color_blue"), ("🟣 بنفش", "sticker_color_purple")],
        [("🟢 سبز", "sticker_color_green"), ("🔴 قرمز", "sticker_color_red")],
        [("🟠 نارنجی", "sticker_color_orange"), ("🩷 صورتی", "sticker_color_pink")],
        [("🔙 بازگشت", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "blue")
    return {"message": text, "reply_markup": reply_markup}

# Game functions with glassmorphism design
async def guess_number_game():
    """بازی حدس عدد با طراحی شیشه‌ای"""
    import random
    number = random.randint(1, 100)
    user_data['guess_number'] = number
    
    text = f"""
🎮 **بازی حدس عدد**

🎯 عددی بین 1 تا 100 انتخاب کرده‌ام!
🔢 حدس خود را وارد کنید

💡 برای راهنمایی از دکمه زیر استفاده کنید
    """
    
    buttons_data = [
        [("💡 راهنمایی", "guess_hint"), ("🔙 بازگشت", "back_to_main")],
        [("📊 آمار بازی", "game_stats")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "purple")
    return {"message": text, "reply_markup": reply_markup}

async def check_guess(guess: int):
    """بررسی حدس کاربر"""
    if 'guess_number' not in user_data:
        return {"message": "❌ بازی شروع نشده است!", "reply_markup": None}
    
    number = user_data['guess_number']
    
    if guess == number:
        text = f"""
🎉 **تبریک! شما برنده شدید!**

✅ عدد صحیح: {number}
🏆 امتیاز شما +10

🎮 برای بازی دوباره کلیک کنید
        """
        buttons_data = [
            [("🔄 بازی دوباره", "guess_number"), ("🏠 منوی اصلی", "back_to_main")]
        ]
        color_scheme = "green"
    elif guess < number:
        text = f"""
🔼 **عدد بزرگتری انتخاب کنید**

❌ حدس شما: {guess}
📈 عدد مورد نظر بزرگتر است

🎯 دوباره تلاش کنید
        """
        buttons_data = [
            [("💡 راهنمایی", "guess_hint"), ("🔙 بازگشت", "back_to_main")]
        ]
        color_scheme = "orange"
    else:
        text = f"""
🔽 **عدد کوچکتر انتخاب کنید**

❌ حدس شما: {guess}
📉 عدد مورد نظر کوچکتر است

🎯 دوباره تلاش کنید
        """
        buttons_data = [
            [("💡 راهنمایی", "guess_hint"), ("🔙 بازگشت", "back_to_main")]
        ]
        color_scheme = "red"
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, color_scheme)
    return {"message": text, "reply_markup": reply_markup}

async def rock_paper_scissors_game():
    """بازی سنگ کاغذ قیچی با طراحی شیشه‌ای"""
    text = """
🎮 **بازی سنگ کاغذ قیچی**

✊ سنگ
📄 کاغذ
✂️ قیچی

🎯 انتخاب خود را کنید:
    """
    
    buttons_data = [
        [("✊ سنگ", "rps_choice_rock"), ("📄 کاغذ", "rps_choice_paper"), ("✂️ قیچی", "rps_choice_scissors")],
        [("📊 آمار بازی", "rps_stats"), ("🔙 بازگشت", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "blue")
    return {"message": text, "reply_markup": reply_markup}

async def check_rps_choice(user_choice: str):
    """بررسی انتخاب کاربر در بازی سنگ کاغذ قیچی"""
    import random
    
    choices = {"rock": "✊ سنگ", "paper": "📄 کاغذ", "scissors": "✂️ قیچی"}
    bot_choice = random.choice(list(choices.keys()))
    
    # منطق بازی
    if user_choice == bot_choice:
        result_text = "🤝 مساوی!"
        color_scheme = "orange"
    elif (
        (user_choice == "rock" and bot_choice == "scissors") or
        (user_choice == "paper" and bot_choice == "rock") or
        (user_choice == "scissors" and bot_choice == "paper")
    ):
        result_text = "🎉 شما برنده شدید!"
        color_scheme = "green"
    else:
        result_text = "😔 ربات برنده شد!"
        color_scheme = "red"
    
    text = f"""
🎮 **نتیجه بازی**

انتخاب شما: {choices[user_choice]}
انتخاب ربات: {choices[bot_choice]}

{result_text}

🔄 برای بازی دوباره کلیک کنید
    """
    
    buttons_data = [
        [("🔄 بازی دوباره", "rock_paper_scissors"), ("🏠 منوی اصلی", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, color_scheme)
    return {"message": text, "reply_markup": reply_markup}

async def word_game():
    """بازی کلمات با طراحی شیشه‌ای"""
    words = ["پایتون", "برنامه‌نویسی", "تلگرام", "ربات", "موبایل", "کامپیوتر", "هوش مصنوعی", "اینترنت"]
    import random
    
    word = random.choice(words)
    user_data['word_game'] = {'word': word, 'hints': 0}
    
    text = f"""
🎮 **بازی حدس کلمه**

📝 یک کلمه انتخاب کرده‌ام
🔤 تعداد حروف: {len(word)}
💭 حدس خود را وارد کنید

💡 برای راهنمایی از دکمه زیر استفاده کنید
    """
    
    buttons_data = [
        [("💡 راهنمایی", "word_hint"), ("🔙 بازگشت", "back_to_main")],
        [("📊 امار بازی", "word_stats")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "purple")
    return {"message": text, "reply_markup": reply_markup}

async def memory_game():
    """بازی حافظه با طراحی شیشه‌ای"""
    text = """
🧠 **بازی حافظه**

🎯 چند عدد به شما نشان می‌دهم
⏰ 3 ثانیه فرصت دارید
🧠 سپس باید آن‌ها را به خاطر بیاورید

🚀 آماده‌اید؟
    """
    
    buttons_data = [
        [("🚀 شروع بازی", "memory_start"), ("🔙 بازگشت", "back_to_main")],
        [("📊 آمار بازی", "memory_stats")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "green")
    return {"message": text, "reply_markup": reply_markup}

async def random_game():
    """بازی تصادفی با طراحی شیشه‌ای"""
    import random
    
    games = [
        ("guess_number", "🎯 حدس عدد"),
        ("rock_paper_scissors", "✂️ سنگ کاغذ قیچی"),
        ("word_game", "📝 حدس کلمه"),
        ("memory_game", "🧠 بازی حافظه")
    ]
    
    game_name, game_emoji = random.choice(games)
    
    text = f"""
🎲 **بازی تصادفی**

🎯 بازی انتخاب شده: {game_emoji} {game_name.replace('_', ' ').title()}

🚀 آماده شروع هستید؟
    """
    
    buttons_data = [
        [("🚀 شروع بازی", game_name), ("🎲 دوباره انتخاب", "random_game")],
        [("🏠 منوی اصلی", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "orange")
    return {"message": text, "reply_markup": reply_markup}

async def custom_sticker_menu():
    """منوی استیکر ساز سفارشی با طراحی شیشه‌ای"""
    text = """
🎨 **استیکر ساز شیشه‌ای**

✨ با طراحی مدرن و زیبا
🎫 متن دلخواه خود را وارد کنید
🌈 رنگ مورد نظر را انتخاب کنید

🚀 ساخت استیکر شروع می‌شود...
    """
    
    buttons_data = [
        [("🔵 طرح آبی", "sticker_bg_blue"), ("🟣 طرح بنفش", "sticker_bg_purple")],
        [("🟢 طرح سبز", "sticker_bg_green"), ("🔴 طرح قرمز", "sticker_bg_red")],
        [("🟠 طرح نارنجی", "sticker_bg_orange"), ("🩷 طرح صورتی", "sticker_bg_pink")],
        [("✏️ نوشتن متن", "sticker_text"), ("🔙 بازگشت", "back_to_main")]
    ]
    
    reply_markup = create_glassmorphism_keyboard(buttons_data, "blue")
    return {"message": text, "reply_markup": reply_markup}