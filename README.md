# Telegram Sticker Bot

A Telegram bot for creating text stickers with custom backgrounds and advanced design options.

## Features

- 🎁 Free test mode (5 stickers per day)
- 🎨 Advanced design options (colors, fonts, sizes, positions)
- 📚 Ready-made templates
- 📷 Custom background images
- 🌍 Persian/Arabic and English text support
- 📊 Usage tracking and limits

## Environment Variables

Set these environment variables in your deployment platform:

```
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_SECRET=your_webhook_secret
APP_URL=your_app_url
BOT_USERNAME=your_bot_username
CHANNEL_LINK=@your_channel
SUPPORT_ID=@your_support
```

## Deployment

This bot is configured for deployment on platforms like Railway, Heroku, or similar services.

### Files included:
- `bot.py` - Main bot code
- `requirements.txt` - Python dependencies
- `nixpacks.toml` - Nixpacks configuration
- `Procfile` - Process configuration
- `runtime.txt` - Python version specification

## Usage

1. Start the bot with `/start`
2. Choose "🎁 تست رایگان" for free testing
3. Enter a pack name
4. Send a background image
5. Send your text to create stickers

## Requirements

- Python 3.11+
- Flask
- PIL (Pillow)
- requests
- arabic-reshaper
- python-bidi
- waitress
