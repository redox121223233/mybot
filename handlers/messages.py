from utils.telegram_api import send_message, edit_message_text, answer_callback_query
from utils.logger import logger
from services.database import load_user_if_missing, set_user_mode, get_user_state
from services.subscription import handle_trial_activation, show_subscription_menu
from handlers.stickers import handle_sticker_input

def process_message(message):
    """پردازش پیام‌های دریافتی"""
    try:
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        # ثبت کاربر جدید
        users = db_manager.data.get('users', {})
        if str(chat_id) not in users:
            users[str(chat_id)] = {
                "id": chat_id,
                "first_name": message["from"].get("first_name", ""),
                "username": message["from"].get("username", ""),
                "lang": "fa",
                "joined": time.time(),
                "sticker_usage": [],
                "last_reset": time.time()
            }
            db_manager.save_data('users')
            logger.info(f"New user registered: {chat_id}")
        
        # پردازش دستورات
        if "text" in message:
            text = message["text"]
            
            # دستورات اصلی
            if text == "/start":
                send_welcome_message(chat_id)
                return
                
            elif text == "/help":
                send_help_message(chat_id)
                return
                
            elif text == "/settings":
                send_settings_menu(chat_id)
                return
                
            elif text == "/subscription" or text == "⭐ اشتراک":
                menu_manager.show_subscription_menu(chat_id)
                return
                
            elif text == "/trial" or text == "🎁 تست رایگان":
                menu_manager.show_free_trial_menu(chat_id)
                return
                
            elif text == "/templates" or text == "📚 قالب‌های آماده":
                menu_manager.show_templates_menu(chat_id)
                return
                
            elif text == "/sticker" or text == "🎨 ساخت استیکر":
                handle_sticker_maker_toggle(chat_id, None, ai_manager, api)
                return
                
            elif text == "/ai_sticker" or text == "🤖 استیکرساز هوشمند" and AI_INTEGRATION_AVAILABLE:
                api.send_message(chat_id, "🤖 استیکرساز هوشمند فعال شد. لطفاً متن یا تصویر خود را ارسال کنید.")
                toggle_ai(chat_id, True, ai_manager)
                return
                
            # پردازش متن برای ساخت استیکر
            elif AI_INTEGRATION_AVAILABLE and should_ai_respond(message, ai_manager):
                handle_sticker_maker_input(chat_id, text, "text", ai_manager=ai_manager, send_message=api.send_message)
                return
            
            # پردازش متن عادی
            else:
                process_text_input(chat_id, text)
                return
                
        # پردازش عکس
        elif "photo" in message:
            photo = message["photo"][-1]  # بزرگترین سایز
            caption = message.get("caption", "")
            
            if AI_INTEGRATION_AVAILABLE:
                handle_sticker_maker_input(chat_id, photo["file_id"], "photo", caption=caption, 
                                          ai_manager=ai_manager, send_message=api.send_message)
            else:
                api.send_message(chat_id, "⚠️ پردازش تصویر در حال حاضر در دسترس نیست.")
            return
            
        # پردازش استیکر
        elif "sticker" in message:
            sticker = message["sticker"]
            
            if AI_INTEGRATION_AVAILABLE:
                handle_sticker_maker_input(chat_id, sticker["file_id"], "sticker", 
                                          ai_manager=ai_manager, send_message=api.send_message)
            else:
                api.send_message(chat_id, "⚠️ پردازش استیکر در حال حاضر در دسترس نیست.")
            return
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        api.send_message(chat_id, f"⚠️ خطایی رخ داد: {str(e)}")
