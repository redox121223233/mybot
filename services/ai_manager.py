import os
import logging
from datetime import datetime
from config import DATA_DIR, FONTS_DIR
from services.setting_manager import get_user_settings

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 📁 مسیر خروجی استیکرهای ساخته‌شده
AI_OUTPUT_DIR = os.path.join(DATA_DIR, "ai_stickers")
os.makedirs(AI_OUTPUT_DIR, exist_ok=True)


def generate_sticker(prompt: str, user_id: int | None = None) -> str:
    """
    تولید استیکر بر اساس متن کاربر و تنظیمات شخصی‌سازی‌شده.
    خروجی: مسیر فایل PNG ذخیره‌شده
    """

    # 🛠 گرفتن تنظیمات کاربر
    settings = get_user_settings(user_id)
    text_color = settings.get("text_color", "#000000")
    font_size = int(settings.get("font_size", 32))
    font_name = settings.get("font_name", "arial.ttf")
    position = settings.get("position", "center")

    logger.info(f"🎨 Generating AI sticker: user={user_id}, prompt={prompt}, settings={settings}")

    # مسیر فایل خروجی
    fname = f"sticker_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    out_path = os.path.join(AI_OUTPUT_DIR, fname)

    try:
        # 📐 اندازه تصویر پایه
        W, H = 512, 512
        img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # 📂 لود کردن فونت انتخاب‌شده
        font_path = os.path.join(FONTS_DIR, font_name)
        if not os.path.exists(font_path):
            logger.warning(f"⚠️ فونت {font_name} پیدا نشد. استفاده از پیش‌فرض.")
            font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(font_path, font_size)

        # ✍️ تقسیم متن به چند خط
        words = prompt.split()
        lines = []
        line = ""
        max_chars = 25
        for w in words:
            if len(line + " " + w) > max_chars:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            lines.append(line)

        # 📍 موقعیت متن
        total_height = len(lines) * (font_size + 5)
        if position == "top":
            y = 10
        elif position == "bottom":
            y = H - total_height - 10
        else:  # center
            y = (H - total_height) // 2

        # 🖌 کشیدن متن روی تصویر
        for ln in lines:
            w, h = draw.textsize(ln, font=font)
            x = (W - w) // 2
            draw.text((x, y), ln, font=font, fill=text_color)
            y += font_size + 5

        # 💾 ذخیره تصویر
        img.save(out_path)
        logger.info(f"✅ Sticker saved: {out_path}")

        return out_path

    except Exception as e:
        logger.exception("❌ خطا در تولید استیکر")
        return f"[خطا در تولید استیکر برای متن: {prompt}]"
