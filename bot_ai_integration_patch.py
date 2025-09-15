"""
این فایل شامل کدهایی است که باید به بات اصلی شما اضافه شود
برای فعال کردن سیستم کنترل هوش مصنوعی
"""

# اضافه کردن این import ها به ابتدای فایل bot.py
from ai_integration import should_ai_respond, AIManager, check_ai_status, activate_ai, deactivate_ai, toggle_ai

# ایجاد نمونه مدیر هوش مصنوعی (اضافه کردن بعد از تعریف متغیرهای کلی)
ai_manager = AIManager()

def handle_ai_control_commands(chat_id, text):
    """مدیریت دستورات کنترل هوش مصنوعی - اضافه کردن این تابع به bot.py"""
    
    # فقط ادمین می‌تواند کنترل کند
    if chat_id != ADMIN_ID:
        return False
    
    if text == "/ai_status":
        # نمایش وضعیت هوش مصنوعی
        status_info = ai_manager.get_status()
        if status_info:
            status_text = 'فعال ✅' if status_info['active'] else 'غیرفعال ❌'
            message = f"""🤖 وضعیت هوش مصنوعی
            
📊 وضعیت: {status_text}
⏰ آخرین به‌روزرسانی: {status_info['formatted_time']}
👤 به‌روزرسانی شده توسط: {status_info['updated_by']}

🔧 دستورات کنترل:
/ai_on - فعال کردن هوش مصنوعی
/ai_off - غیرفعال کردن هوش مصنوعی  
/ai_toggle - تغییر وضعیت
/ai_panel - باز کردن پنل کنترل"""
        else:
            message = "❌ خطا در دریافت وضعیت هوش مصنوعی"
        
        send_message(chat_id, message)
        return True
    
    elif text == "/ai_on":
        # فعال کردن هوش مصنوعی
        success, message = activate_ai()
        if success:
            send_message(chat_id, f"✅ {message}")
        else:
            send_message(chat_id, f"❌ خطا: {message}")
        return True
    
    elif text == "/ai_off":
        # غیرفعال کردن هوش مصنوعی
        success, message = deactivate_ai()
        if success:
            send_message(chat_id, f"✅ {message}")
        else:
            send_message(chat_id, f"❌ خطا: {message}")
        return True
    
    elif text == "/ai_toggle":
        # تغییر وضعیت هوش مصنوعی
        success, message, new_status = toggle_ai()
        if success:
            status_emoji = '✅' if new_status else '❌'
            send_message(chat_id, f"{status_emoji} {message}")
        else:
            send_message(chat_id, f"❌ خطا: {message}")
        return True
    
    elif text == "/ai_panel":
        # ارسال لینک پنل کنترل
        panel_url = os.environ.get('AI_CONTROL_URL', 'http://localhost:5000')
        message = f"""🎛️ پنل کنترل هوش مصنوعی

🔗 لینک پنل: {panel_url}

از این پنل می‌توانید:
• وضعیت هوش مصنوعی را مشاهده کنید
• هوش مصنوعی را فعال/غیرفعال کنید
• تاریخچه تغییرات را ببینید

💡 نکته: این لینک فقط برای ادمین در دسترس است."""
        
        send_message(chat_id, message)
        return True
    
    return False

def should_process_ai_message(chat_id, text):
    """بررسی اینکه آیا پیام باید توسط هوش مصنوعی پردازش شود"""
    
    # اگر هوش مصنوعی غیرفعال است، پردازش نکن
    if not should_ai_respond(chat_id, text):
        return False
    
    # دستورات ربات همیشه پردازش می‌شوند
    if text and text.startswith('/'):
        return True
    
    # سایر قوانین...
    return True

# تغییرات مورد نیاز در تابع webhook اصلی:
"""
در تابع webhook اصلی، بعد از خط:
    if "text" in msg:
        text = msg["text"]

این کد را اضافه کنید:

        # بررسی دستورات کنترل هوش مصنوعی
        if handle_ai_control_commands(chat_id, text):
            return "ok"
        
        # بررسی اینکه آیا باید پیام پردازش شود
        if not should_process_ai_message(chat_id, text):
            # اگر هوش مصنوعی غیرفعال است، فقط لاگ کن و پاسخ نده
            logger.info(f"AI is inactive - ignoring message from {chat_id}: {text[:50]}")
            return "ok"
"""

# تابع کمکی برای اضافه کردن دکمه کنترل هوش مصنوعی به منوی ادمین
def add_ai_control_to_admin_menu():
    """اضافه کردن دکمه‌های کنترل هوش مصنوعی به منوی ادمین"""
    return """
🤖 دستورات کنترل هوش مصنوعی:
/ai_status - وضعیت هوش مصنوعی
/ai_on - فعال کردن
/ai_off - غیرفعال کردن  
/ai_toggle - تغییر وضعیت
/ai_panel - پنل کنترل
"""

# مثال استفاده در تابع handle_admin_command موجود:
"""
در تابع handle_admin_command، بعد از بررسی سایر دستورات، این کد را اضافه کنید:

    # بررسی دستورات کنترل هوش مصنوعی
    if handle_ai_control_commands(chat_id, text):
        return True
    
    # اضافه کردن راهنمای هوش مصنوعی به help
    elif command == "help":
        existing_help_message += add_ai_control_to_admin_menu()
"""

# تابع برای نمایش وضعیت هوش مصنوعی در آمار
def get_ai_status_for_stats():
    """دریافت وضعیت هوش مصنوعی برای نمایش در آمار"""
    try:
        status = check_ai_status()
        status_text = "فعال ✅" if status else "غیرفعال ❌"
        return f"🤖 هوش مصنوعی: {status_text}"
    except:
        return "🤖 هوش مصنوعی: خطا در بررسی وضعیت"

# مثال اضافه کردن به آمار در دستور /admin stats:
"""
در قسمت آمار، این خط را اضافه کنید:
        
        ai_status_line = get_ai_status_for_stats()
        message += f"\n{ai_status_line}\n"
"""

# تابع برای لاگ کردن فعالیت هوش مصنوعی
def log_ai_activity(chat_id, message_text, ai_responded):
    """لاگ کردن فعالیت هوش مصنوعی"""
    status = "responded" if ai_responded else "ignored"
    logger.info(f"AI Activity - User: {chat_id}, Message: {message_text[:30]}..., Status: {status}")

# نمونه کد کامل برای اضافه کردن به webhook:
webhook_integration_code = '''
# در ابتدای تابع webhook، بعد از دریافت chat_id:

    # بررسی دستورات کنترل هوش مصنوعی (فقط برای ادمین)
    if "text" in msg and msg["text"].startswith("/ai_"):
        if handle_ai_control_commands(chat_id, msg["text"]):
            return "ok"
    
    # بررسی وضعیت هوش مصنوعی برای پیام‌های عادی
    if "text" in msg:
        text = msg["text"]
        
        # اگر دستور ربات نیست و هوش مصنوعی غیرفعال است، پردازش نکن
        if not text.startswith('/') and not should_ai_respond(chat_id, text):
            log_ai_activity(chat_id, text, False)
            return "ok"
        
        # ادامه پردازش عادی...
        log_ai_activity(chat_id, text, True)
'''

print("✅ فایل patch برای یکپارچه‌سازی هوش مصنوعی آماده شد")
print("📋 برای اعمال تغییرات، کدهای بالا را به فایل bot.py اضافه کنید")