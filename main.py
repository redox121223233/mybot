import os
import logging
import time
from flask import Flask, request
from waitress import serve

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sticker_bot")

# --- ماژول‌های داخلی ---
try:
    # مدیریت دیتابیس
    from database_manager import DatabaseManager
    
    # مدیریت API تلگرام
    from api_handlers import TelegramAPI
    
    # مدیریت منوها
    from menu_handlers import MenuManager
    
    # مدیریت اشتراک‌ها
    from subscription_handlers import SubscriptionManager
    
    # مدیریت استیکرها
    from sticker_handlers import (
        handle_sticker_maker_toggle, 
        handle_sticker_maker_input, 
        process_callback_query,
        create_sticker_from_text,
        send_sticker_from_data
    )
    
    # هوش مصنوعی (اختیاری)
    try:
        from ai_integration import (
            should_ai_respond, 
            AIManager, 
            check_ai_status, 
            activate_ai, 
            deactivate_ai, 
            toggle_ai
        )
        AI_INTEGRATION_AVAILABLE = True
        logger.info("✅ AI Integration available")
    except ImportError:
        AI_INTEGRATION_AVAILABLE = False
        logger.warning("⚠️ AI Integration not available")
    
except ImportError as e:
    logger.error(f"❌ Error importing modules: {e}")
    raise

# --- تنظیمات اصلی ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret").strip()
APP_URL = os.environ.get("APP_URL")
if APP_URL:
    APP_URL = APP_URL.strip().rstrip('/')
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")  # یوزرنیم ربات بدون @
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")  # لینک کانال اجباری

# --- تنظیمات ادمین ---
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6053579919"))  # ایدی ادمین اصلی
SUPPORT_ID = os.environ.get("SUPPORT_ID", "@onedaytoalive")  # ایدی پشتیبانی

# --- تنظیمات پرداخت ---
CARD_NUMBER = os.environ.get("CARD_NUMBER", "1234-5678-9012-3456")  # شماره کارت
CARD_NAME = os.environ.get("CARD_NAME", "نام شما")  # نام صاحب کارت

# --- مسیرهای فایل ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ایجاد نمونه‌های کلاس‌های اصلی ---
# مدیریت دیتابیس
db_manager = DatabaseManager(BASE_DIR)

# API تلگرام
api = TelegramAPI(BOT_TOKEN)

# مدیریت منوها
menu_manager = MenuManager(f"https://api.telegram.org/bot{BOT_TOKEN}/", BOT_TOKEN)

# مدیریت اشتراک‌ها
subscription_manager = SubscriptionManager(
    os.path.join(BASE_DIR, "subscriptions.json"),
    db_manager
)

# هوش مصنوعی (اختیاری)
ai_manager = None
if AI_INTEGRATION_AVAILABLE:
    try:
        ai_manager = AIManager()
        logger.info("✅ AI Manager initialized successfully")
    except Exception as e:
        AI_INTEGRATION_AVAILABLE = False
        logger.error(f"❌ Failed to initialize AI Manager: {e}")

# --- توابع کمکی ---
def is_subscribed(user_id):
    """بررسی اشتراک کاربر"""
    return subscription_manager.is_subscribed(user_id)

def get_subscription_info(user_id):
    """دریافت اطلاعات اشتراک کاربر"""
    return subscription_manager.get_subscription_info(user_id)

def has_used_trial(user_id):
    """بررسی استفاده قبلی از دوره آزمایشی"""
    return subscription_manager.has_used_trial(user_id)

def get_lang(chat_id):
    """دریافت زبان کاربر"""
    return db_manager.data.get('users', {}).get(str(chat_id), {}).get("lang", "fa")

def tr(chat_id, key, fallback_text):
    """ترجمه متن بر اساس زبان کاربر"""
    lang = get_lang(chat_id)
    locales = db_manager.data.get('locales', {})
    return locales.get(lang, {}).get(key, fallback_text)

def check_sticker_limit(chat_id):
    """بررسی محدودیت روزانه ساخت استیکر"""
    chat_id = str(chat_id)
    users = db_manager.data.get('users', {})
    
    if chat_id not in users:
        users[chat_id] = {"sticker_usage": [], "last_reset": time.time()}
    
    user = users[chat_id]
    current_time = time.time()
    
    # محاسبه زمان ریست بعدی (نیمه شب)
    last_reset = user.get("last_reset", current_time)
    next_reset = last_reset + 86400  # 24 ساعت
    
    # اگر زمان ریست گذشته، ریست کن
    if current_time > next_reset:
        user["sticker_usage"] = []
        user["last_reset"] = current_time
        next_reset = current_time + 86400
        db_manager.save_data('users')
    
    # تعداد استیکرهای استفاده شده امروز
    usage_today = len(user.get("sticker_usage", []))
    
    # محدودیت روزانه (برای کاربران رایگان)
    daily_limit = 5
    
    return daily_limit - usage_today, next_reset

def record_sticker_usage(chat_id):
    """ثبت استفاده از استیکر"""
    chat_id = str(chat_id)
    users = db_manager.data.get('users', {})
    
    if chat_id not in users:
        users[chat_id] = {"sticker_usage": [], "last_reset": time.time()}
    
    user = users[chat_id]
    user["sticker_usage"].append(time.time())
    
    db_manager.save_data('users')

def sanitize_pack_name(name):
    """تمیز کردن نام پک استیکر"""
    # فقط حروف انگلیسی، اعداد و _
    return re.sub(r'[^a-zA-Z0-9_]', '', name)

# --- پردازش پیام‌ها ---
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
                
            elif text == "/subscription":
                menu_manager.show_subscription_menu(chat_id)
                return
                
            elif text == "/trial":
                menu_manager.show_free_trial_menu(chat_id)
                return
                
            elif text == "/templates":
                menu_manager.show_templates_menu(chat_id)
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

def handle_callback_query(callback_query):
    """پردازش کالبک کوئری‌ها"""
    try:
        query_id = callback_query["id"]
        chat_id = callback_query["message"]["chat"]["id"]
        message_id = callback_query["message"]["message_id"]
        data = callback_query["data"]
        
        # پردازش دکمه‌های منو
        if data == "show_subscription":
            menu_manager.show_subscription_menu(chat_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        elif data == "show_free_trial":
            menu_manager.show_free_trial_menu(chat_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        elif data == "show_templates":
            menu_manager.show_templates_menu(chat_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        elif data == "back_to_main":
            send_main_menu(chat_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        elif data.startswith("sub_"):
            plan_id = data[4:]
            handle_subscription_purchase(chat_id, plan_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        elif data == "activate_trial":
            handle_trial_activation(chat_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        elif data.startswith("template_"):
            template_id = data[9:]
            handle_template_selection(chat_id, template_id, message_id)
            api.answer_callback_query(query_id)
            return
            
        # پردازش دکمه‌های استیکر
        elif AI_INTEGRATION_AVAILABLE:
            process_callback_query(
                callback_query, 
                ai_manager=ai_manager, 
                answer_callback_query=api.answer_callback_query, 
                edit_message=api.edit_message_text
            )
            return
            
        else:
            api.answer_callback_query(query_id, "⚠️ این قابلیت در حال حاضر در دسترس نیست.")
            return
            
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        api.answer_callback_query(query_id, f"⚠️ خطایی رخ داد: {str(e)}")

# --- توابع منو ---
def send_welcome_message(chat_id):
    """ارسال پیام خوش‌آمدگویی"""
    text = f"👋 سلام! به ربات استیکرساز خوش آمدید!\n\n"
    text += "با این ربات می‌توانید استیکرهای زیبا بسازید.\n\n"
    text += f"🔹 برای پشتیبانی: {SUPPORT_ID}\n"
    text += f"🔹 کانال ما: {CHANNEL_LINK}"
    
    keyboard = [
        [{"text": "🎨 ساخت استیکر", "callback_data": "new_sticker"}],
        [{"text": "🖼 قالب‌های آماده", "callback_data": "show_templates"}],
        [{"text": "💎 خرید اشتراک", "callback_data": "show_subscription"}],
        [{"text": "🎁 دوره آزمایشی رایگان", "callback_data": "show_free_trial"}]
    ]
    
    if AI_INTEGRATION_AVAILABLE:
        keyboard.insert(1, [{"text": "🤖 استیکرساز هوشمند", "callback_data": "toggle_ai_sticker"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    api.send_message(chat_id, text, reply_markup)

def send_main_menu(chat_id, message_id=None):
    """ارسال منوی اصلی"""
    text = "👋 منوی اصلی\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
    
    keyboard = [
        [{"text": "🎨 ساخت استیکر", "callback_data": "new_sticker"}],
        [{"text": "🖼 قالب‌های آماده", "callback_data": "show_templates"}],
        [{"text": "💎 خرید اشتراک", "callback_data": "show_subscription"}],
        [{"text": "🎁 دوره آزمایشی رایگان", "callback_data": "show_free_trial"}]
    ]
    
    if AI_INTEGRATION_AVAILABLE:
        keyboard.insert(1, [{"text": "🤖 استیکرساز هوشمند", "callback_data": "toggle_ai_sticker"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    
    if message_id:
        api.edit_message_text(chat_id, message_id, text, reply_markup)
    else:
        api.send_message(chat_id, text, reply_markup)

def send_help_message(chat_id):
    """ارسال پیام راهنما"""
    text = "🔹 راهنمای استفاده از ربات:\n\n"
    text += "1️⃣ برای ساخت استیکر، متن خود را ارسال کنید.\n"
    text += "2️⃣ برای استفاده از قالب‌های آماده، از منوی قالب‌ها استفاده کنید.\n"
    text += "3️⃣ برای استفاده از قابلیت‌های ویژه، اشتراک تهیه کنید.\n\n"
    text += "🔸 دستورات:\n"
    text += "/start - شروع مجدد ربات\n"
    text += "/help - راهنمای استفاده\n"
    text += "/settings - تنظیمات\n"
    text += "/subscription - خرید اشتراک\n"
    text += "/trial - دوره آزمایشی رایگان\n"
    text += "/templates - قالب‌های آماده\n\n"
    text += f"🔹 برای پشتیبانی: {SUPPORT_ID}"
    
    api.send_message(chat_id, text)

def send_settings_menu(chat_id):
    """ارسال منوی تنظیمات"""
    text = "⚙️ تنظیمات\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
    
    keyboard = [
        [{"text": "🌍 تغییر زبان", "callback_data": "change_lang"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_to_main"}]
    ]
    
    reply_markup = {"inline_keyboard": keyboard}
    api.send_message(chat_id, text, reply_markup)

def process_text_input(chat_id, text):
    """پردازش متن ورودی برای ساخت استیکر"""
    # بررسی محدودیت استیکر (اگر اشتراک ندارد)
    if not is_subscribed(chat_id):
        remaining, next_reset = check_sticker_limit(chat_id)
        if remaining <= 0:
            next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
            text = f"⚠️ محدودیت روزانه شما تمام شده!\n\n"
            text += f"🕒 زمان بعدی: {next_reset_time}\n\n"
            text += "💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید."
            
            keyboard = [
                [{"text": "💎 خرید اشتراک", "callback_data": "show_subscription"}],
                [{"text": "🎁 دوره آزمایشی رایگان", "callback_data": "show_free_trial"}]
            ]
            
            reply_markup = {"inline_keyboard": keyboard}
            api.send_message(chat_id, text, reply_markup)
            return
    
    # ساخت استیکر
    try:
        sticker_data = create_sticker_from_text(text)
        if sticker_data:
            send_sticker_from_data(chat_id, sticker_data, BOT_TOKEN)
            record_sticker_usage(chat_id)
        else:
            api.send_message(chat_id, "⚠️ خطا در ساخت استیکر. لطفاً متن دیگری را امتحان کنید.")
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        api.send_message(chat_id, f"⚠️ خطایی رخ داد: {str(e)}")

def handle_subscription_purchase(chat_id, plan_id, message_id=None):
    """پردازش خرید اشتراک"""
    if plan_id not in subscription_manager.plans:
        api.send_message(chat_id, "⚠️ طرح اشتراک نامعتبر است.")
        return
    
    plan = subscription_manager.plans[plan_id]
    price = plan["price"]
    title = plan["title"]
    
    text = f"💳 پرداخت اشتراک {title}\n\n"
    text += f"💰 مبلغ: {price} هزار تومان\n\n"
    text += "🔸 روش پرداخت:\n"
    text += f"1️⃣ واریز به کارت: {CARD_NUMBER}\n"
    text += f"2️⃣ به نام: {CARD_NAME}\n\n"
    text += "3️⃣ ارسال رسید پرداخت به پشتیبانی\n"
    text += f"🔹 پشتیبانی: {SUPPORT_ID}\n\n"
    text += "⚠️ پس از تأیید پرداخت، اشتراک شما فعال خواهد شد."
    
    keyboard = [
        [{"text": "🔙 بازگشت", "callback_data": "show_subscription"}]
    ]
    
    reply_markup = {"inline_keyboard": keyboard}
    
    if message_id:
        api.edit_message_text(chat_id, message_id, text, reply_markup)
    else:
        api.send_message(chat_id, text, reply_markup)

def handle_trial_activation(chat_id, message_id=None):
    """فعال‌سازی دوره آزمایشی"""
    if has_used_trial(chat_id):
        text = "⚠️ شما قبلاً از دوره آزمایشی رایگان استفاده کرده‌اید."
        text += "\n\nبرای استفاده از امکانات ویژه، لطفاً اشتراک تهیه کنید."
        
        keyboard = [
            [{"text": "💎 خرید اشتراک", "callback_data": "show_subscription"}],
            [{"text": "🔙 بازگشت", "callback_data": "back_to_main"}]
        ]
        
        reply_markup = {"inline_keyboard": keyboard}
        
        if message_id:
            api.edit_message_text(chat_id, message_id, text, reply_markup)
        else:
            api.send_message(chat_id, text, reply_markup)
        return
    
    # فعال‌سازی دوره آزمایشی
    result = subscription_manager.activate_trial(chat_id)
    
    if result["success"]:
        text = "✅ دوره آزمایشی رایگان با موفقیت فعال شد!\n\n"
        text += f"🔹 مدت زمان: {result['days']} روز\n\n"
        text += "اکنون می‌توانید از تمام امکانات ربات استفاده کنید."
    else:
        text = f"⚠️ {result['message']}"
    
    keyboard = [
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_to_main"}]
    ]
    
    reply_markup = {"inline_keyboard": keyboard}
    
    if message_id:
        api.edit_message_text(chat_id, message_id, text, reply_markup)
    else:
        api.send_message(chat_id, text, reply_markup)

def handle_template_selection(chat_id, template_id, message_id=None):
    """انتخاب قالب برای ساخت استیکر"""
    # بررسی محدودیت استیکر (اگر اشتراک ندارد)
    if not is_subscribed(chat_id):
        remaining, next_reset = check_sticker_limit(chat_id)
        if remaining <= 0:
            next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
            text = f"⚠️ محدودیت روزانه شما تمام شده!\n\n"
            text += f"🕒 زمان بعدی: {next_reset_time}\n\n"
            text += "💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید."
            
            keyboard = [
                [{"text": "💎 خرید اشتراک", "callback_data": "show_subscription"}],
                [{"text": "🎁 دوره آزمایشی رایگان", "callback_data": "show_free_trial"}]
            ]
            
            reply_markup = {"inline_keyboard": keyboard}
            
            if message_id:
                api.edit_message_text(chat_id, message_id, text, reply_markup)
            else:
                api.send_message(chat_id, text, reply_markup)
            return
    
    # قالب‌های موجود
    templates = {
        "birthday": "تولد",
        "love": "عاشقانه",
        "funny": "خنده‌دار",
        "family": "خانوادگی",
        "party": "مهمانی",
        "work": "کاری",
        "education": "تحصیلی",
        "wedding": "عروسی",
        "exciting": "هیجان‌انگیز"
    }
    
    if template_id not in templates:
        text = "⚠️ قالب انتخابی نامعتبر است."
        
        keyboard = [
            [{"text": "🔙 بازگشت", "callback_data": "show_templates"}]
        ]
        
        reply_markup = {"inline_keyboard": keyboard}
        
        if message_id:
            api.edit_message_text(chat_id, message_id, text, reply_markup)
        else:
            api.send_message(chat_id, text, reply_markup)
        return
    
    template_name = templates[template_id]
    
    text = f"🖼 قالب {template_name} انتخاب شد.\n\n"
    text += "لطفاً متن خود را برای ساخت استیکر با این قالب ارسال کنید:"
    
    # ذخیره قالب انتخابی در داده‌های کاربر
    users = db_manager.data.get('users', {})
    if str(chat_id) in users:
        users[str(chat_id)]["selected_template"] = template_id
        db_manager.save_data('users')
    
    if message_id:
        api.edit_message_text(chat_id, message_id, text)
    else:
        api.send_message(chat_id, text)

# --- اجرای برنامه ---
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running!"

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=['POST'])
def webhook():
    """دریافت آپدیت‌های تلگرام"""
    try:
        data = request.get_json()
        logger.info(f"Received update: {data}")
        
        # پردازش کالبک کوئری‌ها
        if "callback_query" in data:
            handle_callback_query(data["callback_query"])
            return "OK"
        
        # پردازش پیام‌ها
        if "message" in data:
            process_message(data["message"])
            return "OK"
        
        return "OK"
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return "Error", 500

def register_webhook():
    """ثبت وبهوک با تلگرام"""
    if not APP_URL:
        logger.warning("⚠️ APP_URL not set, skipping webhook registration")
        return False
    
    webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
    logger.info(f"Registering webhook: {webhook_url}")
    
    result = api.set_webhook(webhook_url)
    
    if result.get("ok"):
        logger.info(f"✅ Webhook registered successfully: {result}")
        return True
    else:
        logger.error(f"❌ Failed to register webhook: {result}")
        return False

if __name__ == "__main__":
    # ثبت وبهوک
    if APP_URL:
        register_webhook()
    
    # اجرای سرور
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    
    if os.environ.get("ENVIRONMENT") == "production":
        serve(app, host="0.0.0.0", port=port)
    else:
        app.run(host="0.0.0.0", port=port, debug=True)