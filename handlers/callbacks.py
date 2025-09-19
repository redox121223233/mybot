from utils.telegram_api import send_message, answer_callback_query
from utils.logger import logger
from services.subscription import handle_subscription_purchase, handle_trial_activation, handle_template_selection, show_subscription_menu

def handle_callback(cb):
    try:
        callback_query_id = cb.get("id")
        message = cb.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        data = cb.get("data", "")
        logger.info(f"Callback received: {data} from chat {chat_id}")
        if data == "new_sticker":
            send_message(chat_id, "✨ شروع ساخت استیکر ...")
            answer_callback_query(callback_query_id)
            return
        if data == "show_subscription":
            show_subscription_menu(chat_id, message_id)
            answer_callback_query(callback_query_id)
            return
        if data == "show_free_trial":
            handle_trial_activation(chat_id, message_id)
            answer_callback_query(callback_query_id)
            return
        if data == "show_templates":
            # template id could be encoded like template_<id>
            tid = data.split("_",1)[-1] if "_" in data else data
            handle_template_selection(chat_id, tid, message_id)
            answer_callback_query(callback_query_id)
            return
        if data == "ai_activate":
            try:
                from services.ai import toggle as ai_toggle
                ai_toggle(chat_id, True)
                answer_callback_query(callback_query_id, "هوش مصنوعی فعال شد ✅")
            except Exception as e:
                logger.error("AI toggle failed: %s", e)
                answer_callback_query(callback_query_id, "خطا در فعال‌سازی AI")
            return
        if data == "toggle_ai_sticker":
            send_message(chat_id, "تغییر وضعیت استیکر هوش مصنوعی...")
            answer_callback_query(callback_query_id)
            return
        if data == "change_lang":
            send_message(chat_id, "🌐 انتخاب زبان:\n🇮🇷 فارسی | 🇬🇧 English")
            answer_callback_query(callback_query_id)
            return
        answer_callback_query(callback_query_id, "عملیات انجام شد")
    except Exception as e:
        logger.error(f"Error in callbacks.handle_callback: {e}")
        try:
            answer_callback_query(cb.get('id'), "⚠️ خطا در پردازش")
        except: pass
