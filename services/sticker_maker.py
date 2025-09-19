import os
from utils.logger import logger
from services import ai, designer

def create_sticker_from_file(chat_id, file_id, ai_mode=False, design_opts=None):
    """
    ایجاد استیکر از فایل تلگرام.
    ai_mode: اگر True باشه هوش مصنوعی اعمال می‌شه
    design_opts: شامل متن/فونت/تمپلیت
    """
    try:
        logger.info(f"Creating sticker for chat_id={chat_id}, file_id={file_id}, ai_mode={ai_mode}")

        # TODO: دانلود فایل از تلگرام و ذخیره در مسیر temp
        file_path = f"/tmp/{file_id}.jpg"

        # مرحله ۱: AI (اختیاری)
        if ai_mode:
            file_path = ai.process_ai_sticker(file_path, options={"style": "default"})

        # مرحله ۲: طراحی پیشرفته (اختیاری)
        if design_opts:
            file_path = designer.apply_design(
                file_path,
                text=design_opts.get("text"),
                font=design_opts.get("font"),
                template=design_opts.get("template")
            )

        logger.info(f"Sticker created successfully: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Sticker maker error: {e}")
        return False
