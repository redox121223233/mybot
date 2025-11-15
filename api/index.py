#!/usr/bin/env python3
"""
Enhanced Telegram Sticker Bot - Vercel Fixed Version with Correct Static File Serving
"""
import os
import json
import logging
import asyncio
import io
import re
import base64
from typing import Dict, Any, Optional

from flask import Flask, request, send_from_directory, jsonify
from telegram import Update, WebAppInfo, InputSticker
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Correctly configure Flask to serve static files from the `public` directory
# The path is relative to the `api` directory where this script is located.
app = Flask(__name__, static_folder='../public', static_url_path='')

ADMIN_ID = 6053579919

bot_token = os.environ.get("BOT_TOKEN")
if not bot_token:
    logger.error("BOT_TOKEN not found in environment variables")
application = Application.builder().token(bot_token).build()

def create_sticker(text: str, image_data: Optional[bytes] = None) -> bytes:
    try:
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        if image_data:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            canvas.paste(img, (int((512 - img.width) / 2), int((512 - img.height) / 2)), img)
        
        draw = ImageDraw.Draw(canvas)
        if re.search(r'[\u0600-\u06FF]', text):
            text = arabic_reshaper.reshape(text)
            text = get_display(text)
        
        font_path = os.path.join(os.path.dirname(__file__), '../public/fonts/Vazirmatn-Regular.ttf')
        font = ImageFont.truetype(font_path, 60)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        pos = ((512 - text_width) / 2, (512 - text_height) / 2)
        draw.text((pos[0] + 2, pos[1] + 2), text, font=font, fill="#000000")
        draw.text(pos, text, font=font, fill="#FFFFFF")
        
        output = io.BytesIO()
        canvas.save(output, format='WebP', quality=80, optimize=True)
        output.seek(0)
        
        # Check file size and compress further if needed
        file_size = len(output.getvalue())
        if file_size > 64 * 1024:  # If larger than 64KB
            logger.warning(f"Sticker size {file_size} bytes, compressing further...")
            canvas.save(output, format='WebP', quality=60, optimize=True, method=6)
            output.seek(0)
            file_size = len(output.getvalue())
            logger.info(f"Compressed to {file_size} bytes")
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error in create_sticker: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[{"text": "ورود به مینی اپ", "web_app": {"url": "https://mybot32.vercel.app"}}]]
    reply_markup = {"inline_keyboard": keyboard}
    await update.message.reply_text("برای کار با ربات به مینی اپ بروید.", reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    async def handle_update():
        await application.initialize()
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
        finally:
            await application.shutdown()
    asyncio.run(handle_update())
    return "OK", 200

@app.route('/api/add-sticker-to-pack', methods=['POST'])
def add_sticker_to_pack_api():
    async def _add_sticker():
        await application.initialize()
        try:
            data = request.get_json()
            user_id, pack_name, sticker_b64 = data.get('user_id'), data.get('pack_name'), data.get('sticker', '').split(',')[1]
            sticker_bytes = base64.b64decode(sticker_b64)
            if not all([user_id, pack_name, sticker_bytes]):
                return jsonify({"error": "Missing required data"}), 400

            bot = application.bot
            full_pack_name = f"{pack_name}_by_{bot.username}"

            sticker_to_add = InputSticker(sticker=sticker_bytes, emoji_list=["😀"])

            try:
                await bot.get_sticker_set(full_pack_name)
                await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=sticker_to_add)
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                await bot.send_message(user_id, f"✅ استیکر با موفقیت به پک شما اضافه شد:\n{pack_url}")
            except Exception:
                await bot.create_new_sticker_set(user_id=user_id, name=full_pack_name, title=pack_name, stickers=[sticker_to_add])
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                await bot.send_message(user_id, f"🎉 پک استیکر شما با موفقیت ساخته شد:\n{pack_url}")
            return jsonify({"success": True, "message": "Sticker added successfully"}), 200
        except Exception as e:
            logger.error(f"Add sticker API error: {e}")
            return jsonify({"error": "Server error"}), 500
        finally:
            await application.shutdown()
    return asyncio.run(_add_sticker())

@app.route('/api/log', methods=['POST'])
def log_event():
    data = request.get_json()
    logger.info(f"Frontend Log: [{data.get('level', 'INFO').upper()}] {data.get('message', '')}")
    return jsonify({"status": "logged"}), 200
