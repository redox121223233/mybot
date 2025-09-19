# handlers/messages.py
from utils.logger import logger
from services import legacy

def process_message(msg):
    """
    پیام‌های متنی و دستورات ربات
    همه چیز به legacy وصل میشه
    """
    try:
        return legacy.process_message(msg)
    except Exception as e:
        logger.error(f"Error in process_message (handlers/messages.py): {e}")
        return "error"
