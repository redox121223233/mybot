"""
Bot configuration settings based on the reference bot script.
Values are read from environment variables.
"""
import os

# --- Telegram Bot ---
# This value MUST be set in the Vercel environment variables.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# This will be fetched automatically at runtime.
BOT_USERNAME = ""

# --- Channel, Support & Admin ---
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@redoxbot_sticker")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@onedaytoalive")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6053579919"))

# --- Bot Settings ---
MAINTENANCE = os.getenv("MAINTENANCE", "False").lower() == "true"
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))

# --- Word Filter ---
# A space-separated string of forbidden words, read from env variables.
FORBIDDEN_WORDS_STR = os.getenv("FORBIDDEN_WORDS", "kos kir kon koss kiri koon")
FORBIDDEN_WORDS = FORBIDDEN_WORDS_STR.split()

# --- Sticker Settings ---
DEFAULT_PALETTE = [
    ("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#F43F5E"), ("آبی", "#3B82F6"),
    ("سبز", "#22C55E"), ("زرد", "#EAB308"), ("بنفش", "#8B5CF6"), ("نارنجی", "#F97316"),
]
