#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for Advanced Sticker Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0')
ADMIN_ID = 6053579919
REQUIRED_CHANNEL = '@redoxbot_sticker'
SUPPORT_USERNAME = '@onedaytoalive'

# GitHub Configuration
GITHUB_REPO = os.getenv('GITHUB_REPO', 'your-username/your-repo')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', 'your_github_token')

# Sticker Configuration
MAX_STICKERS_PER_DAY = 5
QUOTA_RESET_HOURS = 24

# Font Configuration
FONT_PATH = 'fonts/Vazirmatn-Regular.ttf'
DEFAULT_FONT_SIZE = 60  # Increased default font size
MIN_FONT_SIZE = 40
MAX_FONT_SIZE = 120

# Sticker Dimensions
STICKER_WIDTH = 512
STICKER_HEIGHT = 512

# Text Positions
TEXT_POSITIONS = {
    'center': (0.5, 0.5),
    'top': (0.5, 0.2),
    'bottom': (0.5, 0.8),
    'left': (0.2, 0.5),
    'right': (0.8, 0.5)
}

# Background Types
BACKGROUND_TYPES = ['default', 'transparent', 'custom']

# File Paths
DATA_DIR = 'data'
TEMP_DIR = 'temp'
FONTS_DIR = 'fonts'

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

