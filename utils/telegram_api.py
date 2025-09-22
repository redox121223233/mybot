import requests
import logging
from config import API, CHANNEL_LINK

logger = logging.getLogger(__name__)

def check_channel_membership(user_id: int) -> bool:
    """بررسی عضویت کاربر در کانال اجباری"""
    try:
        channel_username = CHANNEL_LINK.replace("@", "")
        resp = requests.get(API + "getChatMember", params={
            "chat_id": f"@{channel_username}",
            "user_id": user_id
        }).json()

        if resp.get("ok"):
            status = resp["result"]["status"]
            return status in ["member", "administrator", "creator"]
        else:
            logger.error(f"❌ Error checking membership: {resp}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception in check_channel_membership: {e}")
        return False


def send_membership_required_message(chat_id: int):
    """ارسال پیام عضویت اجباری"""
    message = f"""🔒 عضویت در کانال اجباری است!

برای استفاده از ربات، ابتدا باید عضو کانال شوید:

📢 {CHANNEL_LINK}

بعد از عضویت، دوباره /start را بزنید ✅"""

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "📢 عضویت در کانال",
                "url": f"https://t.me/{CHANNEL_LINK.replace('@', '')}"
            }
        ]]
    }

    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": message,
        "reply_markup": keyboard
    })
