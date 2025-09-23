import os
from PIL import Image, ImageDraw, ImageFont
from config import TELEGRAM_TOKEN
from utils.state_manager import set_state, get_state

def resize_to_sticker_size(input_path, output_path, text=None):
    img = Image.open(input_path).convert("RGBA")
    img.thumbnail((512, 512))

    if text:
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("arial.ttf", 40)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = ((img.width - text_w) // 2, img.height - text_h - 10)
        draw.text(pos, text, font=font, fill="white")

    img.save(output_path, "PNG")

def handle_sticker_upload(api, chat_id, file_id):
    file_info = api.get_file(file_id)
    file_path = file_info["file_path"]

    input_path = f"/tmp/{chat_id}_in.png"
    output_path = f"/tmp/{chat_id}_out.png"

    api.download_file(file_path, input_path)

    set_state(chat_id, "awaiting_text_choice")
    api.send_message(
        chat_id,
        "✍️ میخوای روی استیکرت متن هم بذارم؟",
        reply_markup={
            "keyboard": [[{"text": "بله ✍️"}], [{"text": "خیر 🚫"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        },
    )

def handle_text_choice(api, chat_id, choice):
    if choice.startswith("بله"):
        set_state(chat_id, "awaiting_text")
        api.send_message(chat_id, "✍️ متنتو بفرست تا بذارم روی استیکر.")
    else:
        finalize_sticker(api, chat_id)

def handle_text_input(api, chat_id, text):
    finalize_sticker(api, chat_id, text)

def finalize_sticker(api, chat_id, text=None):
    input_path = f"/tmp/{chat_id}_in.png"
    output_path = f"/tmp/{chat_id}_out.png"

    resize_to_sticker_size(input_path, output_path, text=text)

    with open(output_path, "rb") as f:
        api.send_sticker(chat_id, f)

    set_state(chat_id, None)
