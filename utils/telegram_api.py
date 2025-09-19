import requests, os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")  # توکن ربات تنظیم شد
APP_URL = os.environ.get("APP_URL")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret").strip()
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")  # یوزرنیم ربات بدون @
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")  # لینک کانال اجباری
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6053579919"))  # ایدی ادمین اصلی
SUPPORT_ID = os.environ.get("SUPPORT_ID", "@onedaytoalive")  # ایدی پشتیبانی



def send_message(chat_id, text, reply_markup=None):
    """ارسال پیام به کاربر"""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        response = requests.post(API + "sendMessage", json=data, timeout=5)
        logger.info(f"Send message response: {response.text}")
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return False



def edit_message_text(chat_id, message_id, text, reply_markup=None):
    """ویرایش متن پیام"""
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        response = requests.post(API + "editMessageText", json=data, timeout=5)
        logger.info(f"Edit message response: {response.text}")
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error in edit_message_text: {e}")
        return False


        # ارسال درخواست به API تلگرام
        response = requests.post(f"{API}answerCallbackQuery", json=data)
        result = None  # auto-fixed: was incomplete assignment
#     def handle_callback_query(update, context):
#     from menu_handlers import MenuManager
#     from sticker_handlers import start_new_sticker, ai_sticker_handler
# 
# 
#     query = update.callback_query
#     chat_id = query.message.chat_id
#     data = query.data
# 
# 
#     ogger.info(f"Callback query received: {data}")
# 
# 
#     menu = MenuManager(api_url=context.bot.api_url, bot_token=context.bot.token)
# 
# 
#     if data == "back_to_main":
#     menu.show_main_menu(chat_id, query.message.message_id)
# 
# 
#     elif data == "show_subscription":
#     menu.show_subscription_menu(chat_id, query.message.message_id)
# 
# 
#     elif data == "show_trial":
#     menu.show_free_trial_menu(chat_id, query.message.message_id)
# 
# 
#     elif data == "show_templates":
#         menu.show_templates_menu(chat_id, query.message.message_id)
# 
# 
#     elif data.startswith("sub_"):
# خرید اشتراک
#     plan_id = data.split("_")[1]
# اینجا می‌تونی تابع فعال‌سازی اشتراک رو صدا بزنی
#     query.answer(text=f"طرح {plan_id} انتخاب شد ✅", show_alert=True)
# 
# 
#     elif data == "activate_trial":
# فعال‌سازی دوره آزمایشی
#     query.answer(text="دوره آزمایشی فعال شد ✅", show_alert=True)
# 
# 
#     elif data == "new_sticker":
#     query.answer()
#     start_new_sticker(update, context)
# 
# 
#     elif data == "ai_sticker":
#     query.answer()
#     ai_sticker_handler(update, context)
# 
# 
#     elif data.startswith("template_"):
#     template_id = data.split("_")[1]
# اینجا می‌تونی هندلر مربوط به قالب‌ها رو اضافه کنی
#     query.answer(text=f"قالب {template_id} انتخاب شد ✅")
# 
# 
#     else:
#     query.answer(text="دکمه ناشناخته ❓")
# 


def register_webhook():
    """Register webhook with Telegram"""
    try:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        logger.info(f"Registering webhook: {webhook_url}")
        
        data = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        response = requests.post(f"{API}setWebhook", json=data)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Webhook registered successfully: {result}")
            return True
        else:
            logger.error(f"❌ Failed to register webhook: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Error registering webhook: {e}")
        return False

