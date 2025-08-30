
import os
import logging
import time
import traceback
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve
from io import BytesIO

# \u062a\u0646\u0638\u06cc\u0645 \u0644\u0627\u06af\u06cc\u0646\u06af \u0628\u0627 \u062c\u0632\u0626\u06cc\u0627\u062a \u0628\u06cc\u0634\u062a\u0631
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# \u062a\u0646\u0638\u06cc\u0645\u0627\u062a \u0627\u0635\u0644\u06cc
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set!")
    raise ValueError("\u274c BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# \u062f\u06cc\u062a\u0627\u0628\u06cc\u0633 \u0633\u0627\u062f\u0647
user_data = {}

app = Flask(__name__)

@app.route("/")
def home():
    logger.info("Home endpoint accessed")
    return "\u2705 Bot is running!"

@app.route("/ping")
def ping():
    return "pong"

@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    try:
        logger.info("Webhook called")
        update = request.get_json(force=True, silent=True)
        if not update:
            logger.warning("Empty update received")
            return "ok"
        
        logger.info(f"Update received: {update}")
        
        # \u0628\u0631\u0631\u0633\u06cc \u0648\u062c\u0648\u062f \u067e\u06cc\u0627\u0645
        msg = update.get("message")
        if not msg:
            logger.info("No message in update")
            return "ok"

        chat_id = msg["chat"]["id"]
        logger.info(f"Processing message for chat_id: {chat_id}")

        # \u067e\u0631\u062f\u0627\u0632\u0634 \u0645\u062a\u0646
        if "text" in msg:
            text = msg["text"]
            logger.info(f"Text message received: {text}")

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
                        success = send_as_sticker(chat_id, text_sticker, background_file_id)
                        if success:
                            user_data[chat_id]["count"] += 1
                            send_message(chat_id, f"\u2705 \u0627\u0633\u062a\u06cc\u06a9\u0631 \u0634\u0645\u0627\u0631\u0647 {user_data[chat_id]['count']} \u0633\u0627\u062e\u062a\u0647 \u0634\u062f.")
                        else:
                            send_message(chat_id, "\u274c \u0645\u0634\u06a9\u0644\u06cc \u062f\u0631 \u0633\u0627\u062e\u062a \u0627\u0633\u062a\u06cc\u06a9\u0631 \u067e\u06cc\u0634 \u0622\u0645\u062f. \u0644\u0637\u0641\u0627\u064b \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f.")
                    except Exception as e:
                        logger.error(f"Error creating sticker: {e}")
                        logger.error(traceback.format_exc())
                        send_message(chat_id, f"\u274c \u062e\u0637\u0627 \u062f\u0631 \u0633\u0627\u062e\u062a \u0627\u0633\u062a\u06cc\u06a9\u0631. \u0644\u0637\u0641\u0627\u064b \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f.")
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
            
            else:
                # \u0627\u06af\u0631 \u062f\u0631 \u0647\u06cc\u0686 \u062d\u0627\u0644\u062a\u06cc \u0646\u0628\u0648\u062f\u060c \u0645\u0646\u0648\u06cc \u0627\u0635\u0644\u06cc \u0631\u0627 \u0646\u0634\u0627\u0646 \u0628\u062f\u0647
                show_main_menu(chat_id)
                return "ok"

        # \u067e\u0631\u062f\u0627\u0632\u0634 \u0639\u06a9\u0633
        elif "photo" in msg:
            logger.info("Photo message received")
            state = user_data.get(chat_id, {})
            if state.get("mode") == "free" and state.get("step") == "background":
                file_id = msg["photo"][-1]["file_id"]
                user_data[chat_id]["background"] = file_id
                user_data[chat_id]["step"] = "text"
                send_message(chat_id, "\u270d\ufe0f \u062d\u0627\u0644\u0627 \u0645\u062a\u0646 \u0627\u0633\u062a\u06cc\u06a9\u0631\u062a \u0631\u0648 \u0628\u0641\u0631\u0633\u062a:")
                return "ok"
            else:
                # \u0627\u06af\u0631 \u06a9\u0627\u0631\u0628\u0631 \u062f\u0631 \u062d\u0627\u0644\u062a \u062f\u0631\u06cc\u0627\u0641\u062a \u0628\u06a9\u06af\u0631\u0627\u0646\u062f \u0646\u0628\u0648\u062f\u060c \u0645\u0646\u0648\u06cc \u0627\u0635\u0644\u06cc \u0631\u0627 \u0646\u0634\u0627\u0646 \u0628\u062f\u0647
                show_main_menu(chat_id)
                return "ok"

        # \u0627\u06af\u0631 \u067e\u06cc\u0627\u0645 \u0646\u0647 \u0645\u062a\u0646 \u0628\u0648\u062f \u0648 \u0646\u0647 \u0639\u06a9\u0633
        else:
            logger.info("Unsupported message type")
            show_main_menu(chat_id)
            return "ok"

    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        logger.error(traceback.format_exc())
        return "ok"  # \u0647\u0645\u06cc\u0634\u0647 "ok" \u0628\u0631\u06af\u0631\u062f\u0627\u0646 \u062a\u0627 \u062a\u0644\u06af\u0631\u0627\u0645 \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u0646\u06a9\u0646\u062f

def send_as_sticker(chat_id, text, background_file_id=None):
    try:
        sticker_path = f"sticker_{chat_id}_{int(time.time())}.png"
        logger.info(f"Creating sticker image at {sticker_path}")
        
        if not make_text_sticker(text, sticker_path, background_file_id):
            logger.error("Failed to create sticker image")
            return False

        pack_name = user_data[chat_id].get("pack_name", f"pack{abs(chat_id)}_by_{BOT_USERNAME}")
        pack_title = f"Sticker Pack {chat_id}"

        logger.info(f"Checking if sticker pack exists: {pack_name}")
        resp = requests.get(API + f"getStickerSet?name={pack_name}")
        
        if resp.status_code != 200:
            logger.error(f"Error checking sticker pack: Status code {resp.status_code}")
            return False
            
        resp_json = resp.json()
        
        if not resp_json.get("ok"):
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
                logger.info(f"Create sticker set response: {create_response.text}")
                if not create_response.json().get("ok"):
                    logger.error(f"Failed to create sticker set: {create_response.text}")
                    return False
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
                logger.info(f"Add sticker response: {add_response.text}")
                if not add_response.json().get("ok"):
                    logger.error(f"Failed to add sticker: {add_response.text}")
                    return False

        # \u067e\u0627\u06a9\u0633\u0627\u0632\u06cc \u0641\u0627\u06cc\u0644 \u0645\u0648\u0642\u062a
        try:
            os.remove(sticker_path)
            logger.info(f"Removed temporary file: {sticker_path}")
        except Exception as e:
            logger.warning(f"Could not remove temporary file: {e}")

        logger.info(f"Getting updated sticker set: {pack_name}")
        final = requests.get(API + f"getStickerSet?name={pack_name}")
        if final.status_code != 200:
            logger.error(f"Error getting updated sticker set: Status code {final.status_code}")
            return False
            
        final_json = final.json()
        
        if final_json.get("ok"):
            stickers = final_json["result"]["stickers"]
            if stickers:
                file_id = stickers[-1]["file_id"]
                logger.info(f"Sending sticker with file_id: {file_id}")
                sticker_response = requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})
                logger.info(f"Send sticker response: {sticker_response.status_code}")
                return sticker_response.status_code == 200
        
        return False
    except Exception as e:
        logger.error(f"Error in send_as_sticker: {e}")
        logger.error(traceback.format_exc())
        return False

def make_text_sticker(text, path, background_file_id=None):
    try:
        logger.info(f"Creating text sticker with text: {text}")
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))  # \u062a\u0635\u0648\u06cc\u0631 \u0634\u0641\u0627\u0641 512x512

        # \u0644\u0648\u062f \u0628\u06a9\u06af\u0631\u0627\u0646\u062f
        if background_file_id:
            try:
                logger.info(f"Loading background with file_id: {background_file_id}")
                file_info = requests.get(API + f"getFile?file_id={background_file_id}")
                
                if file_info.status_code != 200:
                    logger.error(f"Error getting file info: Status code {file_info.status_code}")
                    # \u0627\u062f\u0627\u0645\u0647 \u0628\u062f\u0647 \u0628\u062f\u0648\u0646 \u0628\u06a9\u06af\u0631\u0627\u0646\u062f
                else:
                    file_info_json = file_info.json()
                    if file_info_json.get("ok"):
                        file_path = file_info_json["result"]["file_path"]
                        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                        logger.info(f"Downloading background from: {file_url}")
                        resp = requests.get(file_url)
                        if resp.status_code == 200:
                            bg = Image.open(BytesIO(resp.content)).convert("RGBA")
                            bg = bg.resize((512, 512))
                            img.paste(bg, (0, 0))
                            logger.info("Background loaded successfully")
                        else:
                            logger.error(f"Error downloading background: Status code {resp.status_code}")
            except Exception as e:
                logger.error(f"Error loading background: {e}")
                logger.error(traceback.format_exc())
                # \u0627\u062f\u0627\u0645\u0647 \u0628\u062f\u0647 \u0628\u062f\u0648\u0646 \u0628\u06a9\u06af\u0631\u0627\u0646\u062f

        draw = ImageDraw.Draw(img)

        # \u0628\u0631\u0631\u0633\u06cc \u0648\u062c\u0648\u062f \u0641\u0648\u0646\u062a
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "DejaVuSans-Bold.ttf",  # \u0627\u06af\u0631 \u0641\u0648\u0646\u062a \u062f\u0631 \u062f\u0627\u06cc\u0631\u06a9\u062a\u0648\u0631\u06cc \u0641\u0639\u0644\u06cc \u0628\u0627\u0634\u062f
            "/app/DejaVuSans-Bold.ttf"  # Railway \u06cc\u0627 Heroku
        ]
        
        font_path = None
        for path_to_check in font_paths:
            if os.path.exists(path_to_check):
                font_path = path_to_check
                logger.info(f"Found font at: {font_path}")
                break
        
        if not font_path:
            logger.error("Font not found, downloading default font")
            # \u062f\u0627\u0646\u0644\u0648\u062f \u0641\u0648\u0646\u062a \u0627\u06af\u0631 \u0645\u0648\u062c\u0648\u062f \u0646\u0628\u0648\u062f
            try:
                font_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"
                font_response = requests.get(font_url)
                if font_response.status_code == 200:
                    with open("DejaVuSans-Bold.ttf", "wb") as f:
                        f.write(font_response.content)
                    font_path = "DejaVuSans-Bold.ttf"
                    logger.info("Font downloaded successfully")
                else:
                    logger.error(f"Failed to download font: {font_response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Error downloading font: {e}")
                return False
        
        # \u0627\u0641\u0632\u0627\u06cc\u0634 \u0633\u0627\u06cc\u0632 \u0627\u0648\u0644\u06cc\u0647 \u0641\u0648\u0646\u062a \u0628\u0647 200 (\u0628\u0632\u0631\u06af\u062a\u0631 \u0627\u0632 \u0642\u0628\u0644)
        initial_font_size = 200
        font = ImageFont.truetype(font_path, initial_font_size)
        logger.info(f"Using font size: {initial_font_size}")

        # \u067e\u06cc\u062f\u0627 \u06a9\u0631\u062f\u0646 \u0627\u0646\u062f\u0627\u0632\u0647 \u0645\u062a\u0646
        try:
            # \u0628\u0631\u0627\u06cc \u0646\u0633\u062e\u0647\u200c\u0647\u0627\u06cc \u062c\u062f\u06cc\u062f PIL
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            logger.info(f"Text dimensions with textbbox: {w}x{h}")
        except AttributeError:
            # \u0628\u0631\u0627\u06cc \u0646\u0633\u062e\u0647\u200c\u0647\u0627\u06cc \u0642\u062f\u06cc\u0645\u06cc\u200c\u062a\u0631 PIL
            w, h = draw.textsize(text, font=font)
            logger.info(f"Text dimensions with textsize: {w}x{h}")

        # \u0627\u06af\u0631 \u0645\u062a\u0646 \u0628\u0632\u0631\u06af\u062a\u0631 \u0627\u0632 \u0627\u0646\u062f\u0627\u0632\u0647 \u0627\u0633\u062a\u06cc\u06a9\u0631 \u0628\u0648\u062f\u060c \u0633\u0627\u06cc\u0632 \u0631\u0648 \u06a9\u0645\u06cc \u06a9\u0648\u0686\u06cc\u06a9\u200c\u062a\u0631 \u0645\u06cc\u200c\u06a9\u0646\u06cc\u0645
        # \u0627\u0645\u0627 \u062d\u062f\u0627\u0642\u0644 \u0633\u0627\u06cc\u0632 \u0641\u0648\u0646\u062a \u0631\u0627 100 \u0642\u0631\u0627\u0631 \u0645\u06cc\u200c\u062f\u0647\u06cc\u0645 \u062a\u0627 \u062e\u06cc\u0644\u06cc \u06a9\u0648\u0686\u06a9 \u0646\u0634\u0648\u062f
        min_font_size = 100
        while (w > 480 or h > 480) and font.size > min_font_size:
            new_size = font.size - 5
            logger.info(f"Reducing font size to: {new_size}")
            font = ImageFont.truetype(font_path, new_size)
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except AttributeError:
                w, h = draw.textsize(text, font=font)
            
            logger.info(f"New text dimensions: {w}x{h}")

        # \u0648\u0633\u0637\u200c\u0686\u06cc\u0646 \u06a9\u0631\u062f\u0646 \u0645\u062a\u0646
        x = (512 - w) / 2
        y = (512 - h) / 2
        logger.info(f"Text position: ({x}, {y})")

        # \u0627\u0636\u0627\u0641\u0647 \u06a9\u0631\u062f\u0646 \u062d\u0627\u0634\u06cc\u0647 \u0633\u0641\u06cc\u062f \u0628\u0631\u0627\u06cc \u0628\u0647\u062a\u0631 \u062f\u06cc\u062f\u0647 \u0634\u062f\u0646 \u0645\u062a\u0646
        outline_range = 12  # \u0636\u062e\u06cc\u0645\u200c\u062a\u0631 \u0634\u062f\u0646 \u062d\u0627\u0634\u06cc\u0647
        logger.info(f"Adding outline with range: {outline_range}")
        
        # \u0631\u0648\u0634 \u0628\u0647\u06cc\u0646\u0647\u200c\u062a\u0631 \u0628\u0631\u0627\u06cc \u0627\u06cc\u062c\u0627\u062f \u062d\u0627\u0634\u06cc\u0647
        for dx in range(-outline_range, outline_range + 1, 2):  # \u06af\u0627\u0645 2 \u0628\u0631\u0627\u06cc \u0633\u0631\u0639\u062a \u0628\u06cc\u0634\u062a\u0631
            for dy in range(-outline_range, outline_range + 1, 2):
                if dx != 0 or dy != 0:
                    if dx*dx + dy*dy <= outline_range*outline_range:  # \u0627\u06cc\u062c\u0627\u062f \u062d\u0627\u0634\u06cc\u0647 \u062f\u0627\u06cc\u0631\u0647\u200c\u0627\u06cc
                        try:
                            draw.text((x + dx, y + dy), text, font=font, fill="white")
                        except Exception as e:
                            logger.error(f"Error drawing outline: {e}")

        # \u0645\u062a\u0646 \u0627\u0635\u0644\u06cc
        logger.info("Drawing main text")
        draw.text((x, y), text, fill="black", font=font)

        logger.info(f"Saving sticker to: {path}")
        img.save(path, "PNG")
        return True
    except Exception as e:
        logger.error(f"Error in make_text_sticker: {e}")
        logger.error(traceback.format_exc())
        return False

def show_main_menu(chat_id):
    try:
        logger.info(f"Showing main menu to chat_id: {chat_id}")
        keyboard = {
            "keyboard": [
                ["\ud83c\udf81 \u062a\u0633\u062a \u0631\u0627\u06cc\u06af\u0627\u0646", "\u2b50 \u0627\u0634\u062a\u0631\u0627\u06a9"],
                ["\ud83d\udcc2 \u067e\u06a9 \u0645\u0646", "\u2139\ufe0f \u062f\u0631\u0628\u0627\u0631\u0647"],
                ["\ud83d\udcde \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc"]
            ],
            "resize_keyboard": True
        }
        response = requests.post(API + "sendMessage", json={
            "chat_id": chat_id,
            "text": "\ud83d\udc4b \u062e\u0648\u0634 \u0627\u0648\u0645\u062f\u06cc! \u06cc\u06a9\u06cc \u0627\u0632 \u06af\u0632\u06cc\u0646\u0647\u200c\u0647\u0627 \u0631\u0648 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646:",
            "reply_markup": keyboard
        })
        logger.info(f"Main menu response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")
        logger.error(traceback.format_exc())
        return False

def send_message(chat_id, text):
    try:
        logger.info(f"Sending message to {chat_id}: {text}")
        response = requests.post(API + "sendMessage", json={"chat_id": chat_id, "text": text})
        logger.info(f"Send message response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        logger.error(traceback.format_exc())
        return False

@app.route("/set_webhook")
def set_webhook():
    if not APP_URL:
        return "APP_URL is not set", 400
        
    webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
    resp = requests.get(API + f"setWebhook?url={webhook_url}")
    logger.info(f"Setting webhook to {webhook_url}: {resp.json()}")
    return f"Webhook set to {webhook_url}: {resp.json()}"

@app.route("/get_webhook_info")
def get_webhook_info():
    resp = requests.get(API + "getWebhookInfo")
    logger.info(f"Webhook info: {resp.json()}")
    return f"Webhook info: {resp.json()}"

if __name__ == "__main__":
    # \u0628\u0631\u0631\u0633\u06cc \u0627\u062a\u0635\u0627\u0644 \u0628\u0647 API \u062a\u0644\u06af\u0631\u0627\u0645
    try:
        me = requests.get(API + "getMe")
        if me.status_code == 200 and me.json().get("ok"):
            bot_info = me.json()["result"]
            logger.info(f"Bot connected successfully: @{bot_info.get('username')}")
        else:
            logger.error(f"Failed to connect to Telegram API: {me.text}")
    except Exception as e:
        logger.error(f"Error connecting to Telegram API: {e}")

    # \u062a\u0646\u0638\u06cc\u0645 webhook \u0627\u06af\u0631 APP_URL \u062a\u0646\u0638\u06cc\u0645 \u0634\u062f\u0647 \u0628\u0627\u0634\u062f
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        try:
            resp = requests.get(API + f"setWebhook?url={webhook_url}")
            logger.info(f"Setting webhook: {resp.json()}")
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    serve(app, host="0.0.0.0", port=port)
