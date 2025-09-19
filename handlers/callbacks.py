from utils.telegram_api import send_message, edit_message_text, answer_callback_query
from utils.logger import logger

def handle_callback_query(callback_query):
    """پردازش کالبک کوئری‌ها"""
    try:
        query_id = callback_query["id"]
        chat_id = callback_query["message"]["chat"]["id"]
        message_id = callback_query["message"]["message_id"]
        data = callback_query["data"]
        
        
        logger.info(f"Callback data: {data}")
# پردازش دکمه‌های منو
        if data == "new_sticker":
            handle_sticker_maker_toggle(chat_id, message_id, ai_manager, api)
            api.api.answer_callback_query(query_id)
            return
            
        elif data == "show_subscription":
            menu_manager.show_subscription_menu(chat_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        elif data == "show_free_trial":
            menu_manager.show_free_trial_menu(chat_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        elif data == "show_templates":
            menu_manager.show_templates_menu(chat_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        elif data == "back_to_main":
            send_main_menu(chat_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        elif data.startswith("sub_"):
            plan_id = data[4:]
            handle_subscription_purchase(chat_id, plan_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        elif data == "activate_trial":
            handle_trial_activation(chat_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        elif data.startswith("template_"):
            template_id = data[9:]
            handle_template_selection(chat_id, template_id, message_id)
            api.api.answer_callback_query(query_id)
            return
            
        # پردازش دکمه‌های استیکر
        elif AI_INTEGRATION_AVAILABLE:
            from sticker_handlers import process_callback_query
            process_callback_query(
                callback_query, 
                ai_manager=ai_manager, 
                answer_callback_query=api.answer_callback_query, 
                edit_message=api.edit_message_text
            )
            return
            
        else:
            api.api.answer_callback_query(query_id, "⚠️ این قابلیت در حال حاضر در دسترس نیست.")
            return
            
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        api.api.answer_callback_query(query_id, f"⚠️ خطایی رخ داد: {str(e)}")

# --- توابع منو ---
