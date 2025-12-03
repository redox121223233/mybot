"""
Bot configuration settings.
Values are read from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# --- Telegram Bot ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_USERNAME = ""  # Will be fetched automatically

# --- Channel & Support ---
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@redoxbot_sticker")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@onedaytoalive")

# --- Admin ---
ADMIN_ID = int(os.getenv("ADMIN_ID", "6053579919"))

# --- Bot Settings ---
MAINTENANCE = False
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))

# --- Sticker Settings ---
FORBIDDEN_WORDS = ["sticker", "anim", "video"]
DEFAULT_PALETTE = [
    ("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#FF0000"), ("سبز", "#00FF00"),
    ("آبی", "#0000FF"), ("زرد", "#FFFF00"), ("صورتی", "#FFC0CB"), ("نارنجی", "#FFA500")
]
NAME_TO_HEX = {name: hx for name, hx in DEFAULT_PALETTE}
POS_WORDS = ["بالا", "وسط", "پایین", "چپ", "راست"]
SIZE_WORDS = ["کوچک", "متوسط", "بزرگ"]
