from utils.logger import logger

def apply_design(file_path, text=None, font=None, template=None):
    """
    متن/فونت/تمپلیت رو روی عکس اعمال می‌کنه.
    """
    try:
        logger.info(f"Designer applying text={text}, font={font}, template={template} on {file_path}")
        # TODO: با Pillow یا cairo متن و تمپلیت اضافه کنیم
        return file_path
    except Exception as e:
        logger.error(f"Designer error: {e}")
        return file_path
