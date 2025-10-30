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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputSticker
import re
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ In-memory Storage ============
USERS: dict[int, dict] = {}
SESSIONS: dict[int, dict] = {}

def user(uid: int) -> dict:
    if uid not in USERS:
        USERS[uid] = { "packs": [], "current_pack": None, "daily_limit": 3, "ai_used": 0, "day_start": 0 }
    return USERS[uid]

def sess(uid: int) -> dict:
    if uid not in SESSIONS:
        SESSIONS[uid] = { "mode": "main", "sticker_data": {} }
    return SESSIONS[uid]

def reset_mode(uid: int):
    SESSIONS[uid] = { "mode": "main", "sticker_data": {} }

# ============ Sticker Pack Management ============
def get_user_packs(uid: int) -> list:
    return user(uid).get("packs", [])

def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    packs = user(uid).get("packs", [])
    if not any(p['short_name'] == pack_short_name for p in packs):
        packs.append({"name": pack_name, "short_name": pack_short_name})
    user(uid)["packs"] = packs
    user(uid)["current_pack"] = pack_short_name

def set_current_pack(uid: int, pack_short_name: str):
    user(uid)["current_pack"] = pack_short_name

from datetime import datetime, timezone

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp())

def _reset_daily_if_needed(u: dict):
    day_start = u.get("day_start", 0)
    today = _today_start_ts()
    if day_start < today:
        u["day_start"] = today
        u["ai_used"] = 0

def _quota_left(uid: int) -> int:
    u = user(uid)
    _reset_daily_if_needed(u)
    limit = u.get("daily_limit", 3)
    return max(0, limit - u.get("ai_used", 0))

CHANNEL_USERNAME = "@redoxbot_sticker"

async def require_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass  # Ignore errors (e.g., bot not admin in channel)

    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")]
    ]

    text = f"برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید:\n{CHANNEL_USERNAME}"

    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return False


def get_current_pack_short_name(uid: int) -> str | None:
    return user(uid).get("current_pack")

async def check_pack_exists(bot, short_name: str) -> bool:
    try:
        await bot.get_sticker_set(name=short_name)
        return True
    except Exception:
        return False

def is_valid_pack_name(name: str) -> bool:
    if not (1 <= len(name) <= 50):
        return False
    if not name[0].isalpha():
        return False
    if name.endswith('_'):
        return False
    if '__' in name:
        return False
    for char in name:
        if not (char.isalnum() or char == '_'):
            return False
    return True

# Global variables for user states
user_states = {}

# ============ Font and Rendering Logic ============
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
LOCAL_FONT_FILES = {
    "Vazirmatn": "Vazirmatn-Regular.ttf",
    "Sahel": "Sahel.ttf",
    "IRANSans": "IRANSans.ttf",
    "Roboto": "Roboto-Regular.ttf",
    "Default": "Vazirmatn-Regular.ttf",
}

_LOCAL_FONTS = {
    key: os.path.join(FONT_DIR, path)
    for key, path in LOCAL_FONT_FILES.items()
    if os.path.isfile(os.path.join(FONT_DIR, path))
}

def _prepare_text(text: str) -> str:
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def resolve_font_path(font_key: str, text: str = "") -> str:
    return _LOCAL_FONTS.get(font_key, _LOCAL_FONTS.get("Default", ""))

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return size
        size -= 1
    return max(size, 12)

def _parse_hex(hx: str) -> tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3:
        r, g, b = [int(c * 2, 16) for c in hx]
    else:
        r = int(hx[0:2], 16)
        g = int(hx[2:4], 16)
        b = int(hx[4:6], 16)
    return (r, g, b, 255)

async def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: bytes | None = None, as_webp: bool = False) -> bytes:
    W, H = (512, 512)
    if bg_photo:
        try:
            img = Image.open(io.BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except Exception:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if bg_mode == "transparent" else (255, 255, 255, 255))

    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)

    font_path = resolve_font_path(font_key, text)
    txt = _prepare_text(text)
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)

    try:
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if v_pos == "top": y = padding
    elif v_pos == "bottom": y = H - padding - text_height
    else: y = (H - text_height) / 2

    if h_pos == "left": x = padding
    elif h_pos == "right": x = W - padding - text_width
    else: x = W / 2

    draw.text((x, y), txt, font=font, fill=color, anchor="mm" if h_pos == "center" else "lm", stroke_width=2, stroke_fill=(0, 0, 0, 220))

    buf = io.BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ============ Bot Features Class ============
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
        welcome_text = """🎉 به ربات استیکر ساز خوش آمدید! 🎉

از منوی زیر یکی از گزینه‌ها را انتخاب کنید:
"""
        
        keyboard = [
            [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator")],
            [InlineKeyboardButton("🎮 بازی و سرگرمی", callback_data="games_menu")],
            [InlineKeyboardButton("📚 راهنما", callback_data="help"), InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Check if the message is from a callback query
        if update.callback_query:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """📚 **راهنمای کامل ربات:**

🎨 **استیکر ساز:**
برای ساخت استیکر، از دکمه "استیکر ساز" در منوی اصلی استفاده کنید. شما باید یک پک استیکر بسازید یا یکی از پک‌های موجود خود را انتخاب کنید. سپس می‌توانید استیکرهای ساده یا پیشرفته بسازید.

🎮 **بازی‌ها:**
برای سرگرمی، می‌توانید از منوی "بازی و سرگرمی" یکی از بازی‌های موجود را انتخاب کنید.

 پشتیبانی:**
در صورت بروز مشکل، با پشتیبانی در تماس باشید.

"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(help_text, reply_markup=reply_markup)
    
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
    if not await require_channel_membership(update, context):
        return
    user_id = update.effective_user.id
    reset_mode(user_id)
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if not await require_channel_membership(update, context):
        return
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

    if callback_data == "check_membership":
        if await require_channel_membership(update, context):
            await query.message.delete()
            await bot_features.start_command(update, context)
        else:
            await query.answer("شما هنوز عضو کانال نیستید.", show_alert=True)
        return

    if not await require_channel_membership(update, context):
        return
    
    if callback_data == "back_to_main":
        await bot_features.start_command(update, context)
        return

    elif callback_data == "games_menu":
        games_text = "🎮 **بازی‌ها و سرگرمی‌ها** 🎮\n\nیکی از بازی‌های زیر را انتخاب کنید:"
        keyboard = [
            [InlineKeyboardButton("🔢 حدس عدد", callback_data="guess_number")],
            [InlineKeyboardButton("✂️ سنگ کاغذ قیچی", callback_data="rock_paper_scissors")],
            [InlineKeyboardButton("📝 بازی کلمات", callback_data="word_game")],
            [InlineKeyboardButton("🧠 بازی حافظه", callback_data="memory_game")],
            [InlineKeyboardButton("🎲 بازی تصادفی", callback_data="random_game")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(games_text, reply_markup=reply_markup)
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
        # Start the pack selection/creation flow
        packs = get_user_packs(user_id)
        if packs:
            kb = InlineKeyboardBuilder()
            for pack in packs:
                kb.button(text=f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}")
            kb.button(text="➕ ساخت پک جدید", callback_data="pack:new")
            kb.adjust(1)
            await query.edit_message_text(
                "یک پک استیکر را برای اضافه کردن انتخاب کنید، یا یک پک جدید بسازید:",
                reply_markup=kb.as_markup()
            )
        else:
            sess(user_id)["mode"] = "pack_create_start"
            await query.edit_message_text(
                """نام پک را بنویس (مثال: my_stickers):

• فقط حروف انگلیسی، عدد و زیرخط
• باید با حرف شروع شود
• نباید با زیرخط تمام شود
• نباید دو زیرخط پشت سر هم داشته باشد
• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"""
            )

    # --- Sticker Pack Flow ---
    elif callback_data.startswith("pack:select:"):
        pack_short_name = callback_data.split(":")[-1]
        set_current_pack(user_id, pack_short_name)
        # Now ask for sticker type
        keyboard = [
            [InlineKeyboardButton("🖼 استیکر ساده", callback_data="sticker:simple")],
            [InlineKeyboardButton("✨ استیکر پیشرفته", callback_data="sticker:advanced")]
        ]
        await query.edit_message_text("نوع استیکر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif callback_data == "pack:new":
        sess(user_id)["mode"] = "pack_create_start"
        await query.edit_message_text("""نام پک را بنویس (مثال: my_stickers):

• فقط حروف انگلیسی، عدد و زیرخط
• باید با حرف شروع شود
• نباید با زیرخط تمام شود
• نباید دو زیرخط پشت سر هم داشته باشد
• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)""")

    # --- Sticker Simple Flow ---
    elif callback_data == "sticker:simple":
        sess(user_id)['sticker_mode'] = 'simple'
        sess(user_id)['sticker_data'] = {}
        await query.edit_message_text("لطفاً متن استیکر ساده را ارسال کنید:")

    # --- Sticker Advanced Flow ---
    elif callback_data == "sticker:advanced":
        if _quota_left(user_id) <= 0:
            await query.answer("سهمیه استیکر پیشرفته شما برای امروز به پایان رسیده است.", show_alert=True)
            return

        sess(user_id)['sticker_mode'] = 'advanced'
        sess(user_id)['sticker_data'] = {
            "v_pos": "center", "h_pos": "center", "font": "Default",
            "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
        }
        await query.edit_message_text("لطفاً متن استیکر پیشرفته را ارسال کنید:")

    elif callback_data.startswith("sticker_adv:"): # Advanced Sticker Options
        parts = callback_data.split(':')
        action = parts[1]

        sticker_data = sess(user_id).get('sticker_data', {})

        if action == 'vpos':
            sticker_data['v_pos'] = parts[2]
            # Next step: Horizontal position
            keyboard = [
                [InlineKeyboardButton("چپ", callback_data="sticker_adv:hpos:left")],
                [InlineKeyboardButton("وسط", callback_data="sticker_adv:hpos:center")],
                [InlineKeyboardButton("راست", callback_data="sticker_adv:hpos:right")]
            ]
            await query.edit_message_text("موقعیت افقی متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif action == 'hpos':
            sticker_data['h_pos'] = parts[2]
            # Next step: Color
            keyboard = [
                [InlineKeyboardButton("سفید", callback_data="sticker_adv:color:#FFFFFF"), InlineKeyboardButton("مشکی", callback_data="sticker_adv:color:#000000")],
                [InlineKeyboardButton("قرمز", callback_data="sticker_adv:color:#F43F5E"), InlineKeyboardButton("آبی", callback_data="sticker_adv:color:#3B82F6")]
            ]
            await query.edit_message_text("رنگ متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif action == 'color':
            sticker_data['color'] = parts[2]
            # Next step: Size
            keyboard = [
                [InlineKeyboardButton("کوچک", callback_data="sticker_adv:size:small")],
                [InlineKeyboardButton("متوسط", callback_data="sticker_adv:size:medium")],
                [InlineKeyboardButton("بزرگ", callback_data="sticker_adv:size:large")]
            ]
            await query.edit_message_text("اندازه فونت را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif action == 'size':
            sticker_data['size'] = parts[2]
            # Final step: Preview
            img_bytes = await render_image(
                text=sticker_data.get("text", "پیش‌نمایش"),
                v_pos=sticker_data["v_pos"],
                h_pos=sticker_data["h_pos"],
                font_key=sticker_data["font"],
                color_hex=sticker_data["color"],
                size_key=sticker_data["size"],
                as_webp=False
            )
            await query.message.reply_photo(
                photo=InputFile(img_bytes, filename="preview.png"),
                caption="این هم پیش‌نمایش استیکر شما. آیا آن را تایید می‌کنید؟",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ بله، تایید می‌کنم", callback_data="sticker:confirm"),
                    InlineKeyboardButton("✏️ نه، ویرایش می‌کنم", callback_data="sticker:advanced:edit")
                ]])
            )

    elif callback_data == "sticker:advanced:edit":
        # Go back to the first step of advanced customization
        keyboard = [
            [InlineKeyboardButton("بالا", callback_data="sticker_adv:vpos:top")],
            [InlineKeyboardButton("وسط", callback_data="sticker_adv:vpos:center")],
            [InlineKeyboardButton("پایین", callback_data="sticker_adv:vpos:bottom")]
        ]
        await query.edit_message_text(
            "موقعیت عمودی متن را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif callback_data == "sticker:confirm":
        sticker_data = sess(user_id).get('sticker_data', {})
        pack_short_name = get_current_pack_short_name(user_id)

        if not pack_short_name:
            await query.edit_message_text("خطا: پکی انتخاب نشده است. لطفاً دوباره شروع کنید.")
            return

        # Decrement quota if it was an advanced sticker
        if sess(user_id).get("sticker_mode") == "advanced":
            u = user(user_id)
            u["ai_used"] = u.get("ai_used", 0) + 1

        img_bytes = await render_image(
            text=sticker_data.get("text", "استیکر"),
            v_pos=sticker_data.get("v_pos", "center"),
            h_pos=sticker_data.get("h_pos", "center"),
            font_key=sticker_data.get("font", "Default"),
            color_hex=sticker_data.get("color", "#FFFFFF"),
            size_key=sticker_data.get("size", "medium"),
            as_webp=True
        )

        try:
            sticker_to_add = InputSticker(sticker=InputFile(img_bytes, filename="sticker.webp"), emoji_list=["😃"])
            await query.bot.add_sticker_to_set(user_id=user_id, name=pack_short_name, sticker=sticker_to_add)

            pack_link = f"https://t.me/addstickers/{pack_short_name}"
            await query.message.reply_sticker(sticker=InputFile(img_bytes, filename="sticker.webp"))
            await query.edit_message_text(f"استیکر با موفقیت به پک اضافه شد!\n\n{pack_link}")
        except Exception as e:
            await query.edit_message_text(f"خطا در اضافه کردن استیکر به پک: {e}")

        # Reset state
        reset_mode(user_id)
    
    elif callback_data == "help":
        await bot_features.help_command(update, context)

    elif callback_data == "support":
        await query.answer("@onedaytoalive :پشتیبانی", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    current_mode = sess(user_id).get("mode")

    # --- Pack Creation Flow ---
    if current_mode == "pack_create_start":
        if not is_valid_pack_name(text):
            await update.message.reply_text("نام پک نامعتبر است. لطفاً دوباره تلاش کنید.")
            return

        bot_username = (await context.bot.get_me()).username
        pack_short_name = f"{text}_by_{bot_username}"

        if await check_pack_exists(context.bot, pack_short_name):
            await update.message.reply_text("این پک قبلاً وجود دارد. لطفاً یک نام دیگر انتخاب کنید.")
            return

        # Create a dummy sticker to create the pack
        dummy_sticker = await render_image("اولین", "center", "center", "Default", "#FFFFFF", "medium", as_webp=True)

        try:
            await context.bot.create_new_sticker_set(
                user_id=user_id,
                name=pack_short_name,
                title=text,
                stickers=[InputSticker(sticker=InputFile(dummy_sticker, "dummy.webp"), emoji_list=["🎉"])],
                sticker_format="static"
            )
            add_user_pack(user_id, text, pack_short_name)
            set_current_pack(user_id, pack_short_name)

            keyboard = [
                [InlineKeyboardButton("🖼 استیکر ساده", callback_data="sticker:simple")],
                [InlineKeyboardButton("✨ استیکر پیشرفته", callback_data="sticker:advanced")]
            ]
            await update.message.reply_text(
                f"پک «{text}» با موفقیت ساخته شد! حالا نوع استیکر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            reset_mode(user_id)
        except Exception as e:
            await update.message.reply_text(f"خطا در ساخت پک: {e}")
        return

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
    
    # Handle sticker creation text input
    elif sess(user_id).get("sticker_mode") in ["simple", "advanced"]:
        mode = sess(user_id)["sticker_mode"]
        sticker_data = sess(user_id).get("sticker_data", {})
        sticker_data["text"] = text
        sess(user_id)["sticker_data"] = sticker_data

        if mode == "simple":
            # For simple mode, generate preview immediately
            img_bytes = await render_image(
                text=text, v_pos="center", h_pos="center", font_key="Default",
                color_hex="#FFFFFF", size_key="medium", as_webp=False
            )
            await update.message.reply_photo(
                photo=InputFile(img_bytes, filename="preview.png"),
                caption="این هم پیش‌نمایش استیکر شما. آیا آن را تایید می‌کنید؟",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ بله، تایید می‌کنم", callback_data="sticker:confirm"),
                    InlineKeyboardButton("✏️ نه، ویرایش می‌کنم", callback_data="sticker:simple:edit")
                ]])
            )
        elif mode == "advanced":
            # For advanced mode, start the customization flow
            keyboard = [
                [InlineKeyboardButton("بالا", callback_data="sticker_adv:vpos:top")],
                [InlineKeyboardButton("وسط", callback_data="sticker_adv:vpos:center")],
                [InlineKeyboardButton("پایین", callback_data="sticker_adv:vpos:bottom")]
            ]
            await update.message.reply_text(
                "متن دریافت شد. حالا موقعیت عمودی متن را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # ... inside button_callback ...
    elif callback_data == "sticker:simple:edit":
        sess(user_id)['sticker_mode'] = 'simple'
        await query.edit_message_text("لطفاً متن جدید استیکر ساده را ارسال کنید:")
    
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
    application.add_handler(CommandHandler("guess", guess_command))
    application.add_handler(CommandHandler("rps", rps_command))
    application.add_handler(CommandHandler("word", word_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("customsticker", customsticker_command))
    
    # Callback and message handlers
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Import Flask
from flask import Flask, request, jsonify

# Get Telegram token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running! All handlers are active."

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handles incoming Telegram updates."""
    if not TELEGRAM_TOKEN:
        logger.error("No Telegram token found!")
        return jsonify({"status": "error", "message": "Bot token not configured"}), 500

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    setup_application(application)

    try:
        await application.initialize()

        update_data = request.get_json()
        logger.info(f"Received webhook data: {update_data}")

        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)

        await application.shutdown()

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Ensure shutdown is called even on error
        if application.is_initialized:
            await application.shutdown()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    is_token_present = TELEGRAM_TOKEN is not None
    return jsonify({
        "status": "healthy",
        "handlers": "active",
        "telegram_token_present": is_token_present
    })

# For local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))