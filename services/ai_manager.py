import logging
import os
from PIL import Image, ImageDraw, ImageFont
from services.setting_manager import get_user_settings
from config import FONTS_DIR

logger = logging.getLogger(__name__)

def generate_sticker(prompt, user_id):
    """
    ساخت استیکر متنی هوش مصنوعی با تنظیمات کاربر
    """
    try:
        settings = get_user_settings(user_id)
        logger.info(f"🎨 Generating AI sticker: user={user_id}, prompt={prompt}, settings={settings}")

        # ساخت پس‌زمینه شفاف
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # مسیر فونت
        font_name = settings.get("font", "arial.ttf")
        font_path = os.path.join(FONTS_DIR, font_name)

        try:
            font = ImageFont.truetype(font_path, settings.get("size", 32))
        except Exception:
            logger.warning("⚠️ فونت %s پیدا نشد. استفاده از پیش‌فرض.", font_name)
            font = ImageFont.load_default()

        # متن رو خط به خط پردازش می‌کنیم
        lines = prompt.split("\n")
        color = settings.get("color", "black")
        position = settings.get("position", "center")

        y_offset = 50
        for ln in lines:
            # 🔥 اصلاح برای Pillow جدید
            bbox = draw.textbbox((0, 0), ln, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

            if position == "center":
                x = (512 - w) // 2
            elif position == "left":
                x = 20
            else:  # right
                x = 512 - w - 20

            draw.text((x, y_offset), ln, font=font, fill=color)
            y_offset += h + 10

        output_path = f"/tmp/ai_sticker_{user_id}.png"
        img.save(output_path, "PNG")
        return output_path

    except Exception as e:
        logger.error("❌ خطا در تولید استیکر", exc_info=True)
        return None
