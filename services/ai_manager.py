# services/ai_manager.py
import logging
from services.settings_manager import get_user_settings

logger = logging.getLogger(__name__)

def generate_sticker(prompt, user_id):
    """
    شبیه‌سازی تولید استیکر با هوش مصنوعی
    (بعداً میشه وصلش کرد به API مثل DALL·E یا Stable Diffusion)
    """
    logger.info(f"✨ Generating sticker for {user_id}: {prompt}")

    # گرفتن تنظیمات کاربر
    settings = get_user_settings(user_id)

    # شبیه‌سازی خروجی استیکر
    return f"[🎨 استیکر ساخته شد بر اساس متن: «{prompt}» | تنظیمات: {settings}]"
