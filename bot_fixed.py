
import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve
from io import BytesIO
import logging
import time

# \u062a\u0646\u0638\u06cc\u0645 \u0644\u0627\u06af\u06cc\u0646\u06af \u0628\u0631\u0627\u06cc \u0639\u06cc\u0628\u200c\u06cc\u0627\u0628\u06cc \u0628\u0647\u062a\u0631
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("\u274c BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")  # \u06cc\u0648\u0632\u0631\u0646\u06cc\u0645 \u0631\u0628\u0627\u062a (\u0628\u062f\u0648\u0646 @)
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# \u062f\u06cc\u062a\u0627\u0628\u06cc\u0633 \u0633\u0627\u062f\u0647
user_data = {}

app = Flask(__name__)

@app.route("/")
def home():
    return "\u2705 Bot is running!"

@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    try:
        update = request.get_json(force=True, silent=True) or {}
        msg = update.get("message")

        if not msg:
            return "ok"

        chat_id = msg["chat"]["id"]

        # \u0645\u062a\u0646
        if "text" in msg:
            text = msg["text"]

            if text == "/start":
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None}
                show_main_menu(chat_id)
                return "ok"

            if text == "\ud83c\udf81 \u062a\u0633\u062a \u0631\u0627\u06cc\u06af\u0627\u0646":
                user_data[chat_id] = {"mode": "free", "count": 0, "step": "pack_name", "pack_name": None, "background": None}
                send_message(chat_id, "\ud83d\udcdd \u0644\u0637\u0641\u0627\u064b \u06cc\u06a9 \u0646\u0627\u0645 \u0628\u0631\u0627\u06cc \u067e\u06a9 \u0627\u0633\u062a\u06cc\u06a9\u0631 \u062e\u0648\u062f \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646:")
                return "ok"

            state = user_data.get(chat_id, {})
            if state.get("mode") == "free":
                step = state.get("step")

                if step == "pack_name":
                    pack_name = text.replace(" ", "_")
                    user_data[chat_id]["pack_name"] = f"{pack_name}_by_{BOT_USERNAME}"
                    user_data[chat_id]["step"] = "background"
                    send_message(chat_id, "\ud83d\udcf7 \u062d\u0627\u0644\u0627 \u06cc\u06a9 \u0639\u06a9\u0633 \u0628\u0631\u0627\u06cc \u0628\u06a9\u06af\u0631\u0627\u0646\u062f \u0627\u0633\u062a\u06cc\u06a9\u0631\u062a \u0628\u0641\u0631\u0633\u062a:")
                    return "ok"

                if step == "text":
                    text_sticker = text
                    send_message(chat_id, "\u2699\ufe0f \u062f\u0631 \u062d\u0627\u0644 \u0633\u0627\u062e\u062a \u0627\u0633\u062a\u06cc\u06a9\u0631...")
                    try:
                        background_file_id = user_data[chat_id].get("background")
                        send_as_sticker(chat_id, text_sticker, background_file_id)
                        user_data[chat_id]["count"] += 1
                        send_message(chat_id, f"\u2705 \u0627\u0633\u062a\u06cc\u06a9\u0631 \u0634\u0645\u0627\u0631\u0647 {user_data[chat_id]['count']} \u0633\u0627\u062e\u062a\u0647 \u0634\u062f.")
                    except Exception as e:
                        logger.error(f"Error creating sticker: {e}")
                        send_message(chat_id, f"\u274c \u062e\u0637\u0627 \u062f\u0631 \u0633\u0627\u062e\u062a \u0627\u0633\u062a\u06cc\u06a9\u0631: {str(e)[:100]}")
                    return "ok"

            if text == "\u2b50 \u0627\u0634\u062a\u0631\u0627\u06a9":
                send_message(chat_id, "\ud83d\udcb3 \u0628\u062e\u0634 \u0627\u0634\u062a\u0631\u0627\u06a9 \u0628\u0639\u062f\u0627\u064b \u0641\u0639\u0627\u0644 \u062e\u0648\u0627\u0647\u062f \u0634\u062f.")
                return "ok"

            elif text == "\ud83d\udcc2 \u067e\u06a9 \u0645\u0646":
                pack_name = user_data.get(chat_id, {}).get("pack_name")
                if pack_name:
                    pack_url = f"https://t.me/addstickers/{pack_name}"
                    send_message(chat_id, f"\ud83d\uddc2 \u067e\u06a9 \u0627\u0633\u062a\u06cc\u06a9\u0631\u062a \u0627\u06cc\u0646\u062c\u0627\u0633\u062a:\
{pack_url}")
                else:
                    send_message(chat_id, "\u274c \u0647\u0646\u0648\u0632 \u067e\u06a9\u06cc \u0628\u0631\u0627\u06cc\u062a \u0633\u0627\u062e\u062a\u0647 \u0646\u0634\u062f\u0647.")
                return "ok"

            elif text == "\u2139\ufe0f \u062f\u0631\u0628\u0627\u0631\u0647":
                send_message(chat_id, "\u2139\ufe0f \u0627\u06cc\u0646 \u0631\u0628\u0627\u062a \u0628\u0631\u0627\u06cc \u0633\u0627\u062e\u062a \u0627\u0633\u062a\u06cc\u06a9\u0631 \u0645\u062a\u0646\u06cc \u0627\u0633\u062a. \u0646\u0633\u062e\u0647 \u0641\u0639\u0644\u06cc \u0631\u0627\u06cc\u06af\u0627\u0646 \u0627\u0633\u062a.")
                return "ok"

            elif text == "\ud83d\udcde \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc":
                support_id = os.environ.get("SUPPORT_ID", "@YourSupportID")
                send_message(chat_id, f"\ud83d\udcde \u0628\u0631\u0627\u06cc \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc \u0628\u0627 {support_id} \u062f\u0631 \u062a\u0645\u0627\u0633 \u0628\u0627\u0634.")
                return "ok"

        elif "photo" in msg:
            state = user_data.get(chat_id, {})
            if state.get("mode") == "free" and state.get("step") == "background":
                file_id = msg["photo"][-1]["file_id"]
                user_data[chat_id]["background"] = file_id
                user_data[chat_id]["step"] = "text"
                send_message(chat_id, "\u270d\ufe0f \u062d\u0627\u0644\u0627 \u0645\u062a\u0646 \u0627\u0633\u062a\u06cc\u06a9\u0631\u062a \u0631\u0648 \u0628\u0641\u0631\u0633\u062a:")
                return "ok"

        return "ok"
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "error", 500

def send_as_sticker(chat_id, text, background_file_id=None):
    try:
        sticker_path = f"sticker_{chat_id}_{int(time.time())}.png"
        make_text_sticker(text, sticker_path, background_file_id)

        pack_name = user_data[chat_id].get("pack_name", f"pack{abs(chat_id)}_by_{BOT_USERNAME}")
        pack_title = f"Sticker Pack {chat_id}"

        logger.info(f"Creating sticker for chat_id: {chat_id}, pack_name: {pack_name}")
        
        resp = requests.get(API + f"getStickerSet?name={pack_name}").json()

        if not resp.get("ok"):
            logger.info(f"Creating new sticker set: {pack_name}")
            with open(sticker_path, "rb") as f:
                files = {"png_sticker": f}
                data = {
                    "user_id": chat_id,
                    "name": pack_name,
                    "title": pack_title,
                    "emojis": "\ud83d\udd25"
                }
                create_response = requests.post(API + "createNewStickerSet", data=data, files=files)
                logger.info(f"Create sticker set response: {create_response.json()}")
                if not create_response.json().get("ok"):
                    raise Exception(f"Failed to create sticker set: {create_response.json()}")
        else:
            logger.info(f"Adding to existing sticker set: {pack_name}")
            with open(sticker_path, "rb") as f:
                files = {"png_sticker": f}
                data = {
                    "user_id": chat_id,
                    "name": pack_name,
                    "emojis": "\ud83d\udd25"
                }
                add_response = requests.post(API + "addStickerToSet", data=data, files=files)
                logger.info(f"Add sticker response: {add_response.json()}")
                if not add_response.json().get("ok"):
                    raise Exception(f"Failed to add sticker: {add_response.json()}")

        # \u067e\u0627\u06a9\u0633\u0627\u0632\u06cc \u0641\u0627\u06cc\u0644 \u0645\u0648\u0642\u062a
        try:
            os.remove(sticker_path)
        except:
            pass

        final = requests.get(API + f"getStickerSet?name={pack_name}").json()
        if final.get("ok"):
            stickers = final["result"]["stickers"]
            if stickers:
                file_id = stickers[-1]["file_id"]
                requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})
    except Exception as e:
        logger.error(f"Error in send_as_sticker: {e}")
        raise

def make_text_sticker(text, path, background_file_id=None):
    try:
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))  # \u062a\u0635\u0648\u06cc\u0631 \u0634\u0641\u0627\u0641 512x512

        # \u0644\u0648\u062f \u0628\u06a9\u06af\u0631\u0627\u0646\u062f
        if background_file_id:
            try:
                file_info = requests.get(API + f"getFile?file_id={background_file_id}").json()
                if file_info.get("ok"):
                    file_path = file_info["result"]["file_path"]
                    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    resp = requests.get(file_url)
                    if resp.status_code == 200:
                        bg = Image.open(BytesIO(resp.content)).convert("RGBA")
                        bg = bg.resize((512, 512))
                        img.paste(bg, (0, 0))
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        draw = ImageDraw.Draw(img)

        # \u0627\u0633\u062a\u0641\u0627\u062f\u0647 \u0627\u0632 \u0641\u0648\u0646\u062a DejaVuSans-Bold (\u0641\u0648\u0646\u062a \u0628\u0632\u0631\u06af)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        
        # \u0627\u0641\u0632\u0627\u06cc\u0634 \u0633\u0627\u06cc\u0632 \u0627\u0648\u0644\u06cc\u0647 \u0641\u0648\u0646\u062a \u0628\u0647 180 (\u0628\u0632\u0631\u06af\u062a\u0631 \u0627\u0632 \u0642\u0628\u0644)
        initial_font_size = 180
        font = ImageFont.truetype(font_path, initial_font_size)

        # \u067e\u06cc\u062f\u0627 \u06a9\u0631\u062f\u0646 \u0627\u0646\u062f\u0627\u0632\u0647 \u0645\u062a\u0646
        # \u0627\u0633\u062a\u0641\u0627\u062f\u0647 \u0627\u0632 getbbox \u0628\u0647 \u062c\u0627\u06cc textsize \u06a9\u0647 \u062f\u0631 \u0646\u0633\u062e\u0647\u200c\u0647\u0627\u06cc \u062c\u062f\u06cc\u062f\u062a\u0631 PIL \u062a\u0648\u0635\u06cc\u0647 \u0645\u06cc\u200c\u0634\u0648\u062f
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            # \u0628\u0631\u0627\u06cc \u0646\u0633\u062e\u0647\u200c\u0647\u0627\u06cc \u0642\u062f\u06cc\u0645\u06cc\u200c\u062a\u0631 PIL
            w, h = draw.textsize(text, font=font)

        # \u0627\u06af\u0631 \u0645\u062a\u0646 \u0628\u0632\u0631\u06af\u062a\u0631 \u0627\u0632 \u0627\u0646\u062f\u0627\u0632\u0647 \u0627\u0633\u062a\u06cc\u06a9\u0631 \u0628\u0648\u062f\u060c \u0633\u0627\u06cc\u0632 \u0631\u0648 \u06a9\u0645\u06cc \u06a9\u0648\u0686\u06cc\u06a9\u200c\u062a\u0631 \u0645\u06cc\u200c\u06a9\u0646\u06cc\u0645
        # \u0627\u0645\u0627 \u062d\u062f\u0627\u0642\u0644 \u0633\u0627\u06cc\u0632 \u0641\u0648\u0646\u062a \u0631\u0627 80 \u0642\u0631\u0627\u0631 \u0645\u06cc\u200c\u062f\u0647\u06cc\u0645 \u062a\u0627 \u062e\u06cc\u0644\u06cc \u06a9\u0648\u0686\u06a9 \u0646\u0634\u0648\u062f
        min_font_size = 80
        while (w > 480 or h > 480) and font.size > min_font_size:
            font = ImageFont.truetype(font_path, font.size - 5)  # \u06a9\u0627\u0647\u0634 \u0633\u0627\u06cc\u0632 \u0641\u0648\u0646\u062a \u0628\u0627 \u06af\u0627\u0645 \u06a9\u0648\u0686\u06a9\u062a\u0631
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except AttributeError:
                w, h = draw.textsize(text, font=font)

        # \u0648\u0633\u0637\u200c\u0686\u06cc\u0646 \u06a9\u0631\u062f\u0646 \u0645\u062a\u0646
        x = (512 - w) / 2
        y = (512 - h) / 2

        # \u0627\u0636\u0627\u0641\u0647 \u06a9\u0631\u062f\u0646 \u062d\u0627\u0634\u06cc\u0647 \u0633\u0641\u06cc\u062f \u0628\u0631\u0627\u06cc \u0628\u0647\u062a\u0631 \u062f\u06cc\u062f\u0647 \u0634\u062f\u0646 \u0645\u062a\u0646
        outline_range = 10  # \u0636\u062e\u06cc\u0645\u200c\u062a\u0631 \u0634\u062f\u0646 \u062d\u0627\u0634\u06cc\u0647
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                if dx != 0 or dy != 0:
                    if dx*dx + dy*dy <= outline_range*outline_range:  # \u0627\u06cc\u062c\u0627\u062f \u062d\u0627\u0634\u06cc\u0647 \u062f\u0627\u06cc\u0631\u0647\u200c\u0627\u06cc \u0628\u0647 \u062c\u0627\u06cc \u0645\u0631\u0628\u0639\u06cc
                        try:
                            draw.text((x + dx, y + dy), text, font=font, fill="white")
                        except:
                            pass

        # \u0645\u062a\u0646 \u0627\u0635\u0644\u06cc
        draw.text((x, y), text, fill="black", font=font)

        img.save(path, "PNG")
    except Exception as e:
        logger.error(f"Error in make_text_sticker: {e}")
        raise

def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["\ud83c\udf81 \u062a\u0633\u062a \u0631\u0627\u06cc\u06af\u0627\u0646", "\u2b50 \u0627\u0634\u062a\u0631\u0627\u06a9"],
            ["\ud83d\udcc2 \u067e\u06a9 \u0645\u0646", "\u2139\ufe0f \u062f\u0631\u0628\u0627\u0631\u0647"],
            ["\ud83d\udcde \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "\ud83d\udc4b \u062e\u0648\u0634 \u0627\u0648\u0645\u062f\u06cc! \u06cc\u06a9\u06cc \u0627\u0632 \u06af\u0632\u06cc\u0646\u0647\u200c\u0647\u0627 \u0631\u0648 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646:",
        "reply_markup": keyboard
    })

def send_message(chat_id, text):
    requests.post(API + "sendMessage", json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        logger.info(f"Setting webhook: {resp.json()}")

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    serve(app, host="0.0.0.0", port=port)
