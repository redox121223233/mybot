import logging
from utils.settings_manager import get_user_settings

logger = logging.getLogger(__name__)

def generate_sticker(prompt, user_id):
    # 🔮 اینجا بعدا میشه وصل کرد به مدل هوش مصنوعی یا API های تصویرسازی
    logger.info(f"✨ Generating sticker for {user_id}: {prompt}")

    settings = get_user_settings(user_id)
    # الان فقط شبیه‌سازی می‌کنیم
    return f"[استیکر ساخته شد بر اساس متن: {prompt} | تنظیمات: {settings}]"
