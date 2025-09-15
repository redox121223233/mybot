import requests
import json
import os
import logging

# تنظیمات سرور کنترل هوش مصنوعی
AI_CONTROL_URL = os.environ.get('AI_CONTROL_URL', 'http://localhost:5000')
AI_CONTROL_SECRET = os.environ.get('AI_CONTROL_SECRET', 'default_secret')

logger = logging.getLogger("ai_integration")

def check_ai_status():
    """بررسی وضعیت هوش مصنوعی"""
    try:
        response = requests.get(f"{AI_CONTROL_URL}/api/check", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('active', False)
        else:
            logger.error(f"خطا در دریافت وضعیت هوش مصنوعی: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در اتصال به سرور کنترل هوش مصنوعی: {e}")
        return False
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در بررسی وضعیت هوش مصنوعی: {e}")
        return False

def should_ai_respond(chat_id=None, message_text=None):
    """تعیین اینکه آیا هوش مصنوعی باید پاسخ دهد یا نه"""
    
    # بررسی وضعیت کلی هوش مصنوعی
    if not check_ai_status():
        logger.info("هوش مصنوعی غیرفعال است - پاسخ داده نمی‌شود")
        return False
    
    # قوانین اضافی (اختیاری)
    if message_text:
        # اگر پیام دستور ربات است، همیشه پاسخ بده
        if message_text.startswith('/'):
            return True
        
        # اگر پیام خیلی کوتاه است، ممکن است نیازی به پاسخ هوش مصنوعی نباشد
        if len(message_text.strip()) < 3:
            return False
    
    logger.info("هوش مصنوعی فعال است - پاسخ داده می‌شود")
    return True

def activate_ai():
    """فعال کردن هوش مصنوعی"""
    try:
        data = {
            'action': 'activate',
            'secret_key': AI_CONTROL_SECRET
        }
        response = requests.post(f"{AI_CONTROL_URL}/webhook/ai-control", 
                               json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("هوش مصنوعی با موفقیت فعال شد")
            return True, result.get('message', 'فعال شد')
        else:
            logger.error(f"خطا در فعال کردن هوش مصنوعی: {response.status_code}")
            return False, "خطا در فعال کردن"
            
    except Exception as e:
        logger.error(f"خطا در فعال کردن هوش مصنوعی: {e}")
        return False, str(e)

def deactivate_ai():
    """غیرفعال کردن هوش مصنوعی"""
    try:
        data = {
            'action': 'deactivate',
            'secret_key': AI_CONTROL_SECRET
        }
        response = requests.post(f"{AI_CONTROL_URL}/webhook/ai-control", 
                               json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("هوش مصنوعی با موفقیت غیرفعال شد")
            return True, result.get('message', 'غیرفعال شد')
        else:
            logger.error(f"خطا در غیرفعال کردن هوش مصنوعی: {response.status_code}")
            return False, "خطا در غیرفعال کردن"
            
    except Exception as e:
        logger.error(f"خطا در غیرفعال کردن هوش مصنوعی: {e}")
        return False, str(e)

def toggle_ai():
    """تغییر وضعیت هوش مصنوعی"""
    try:
        data = {
            'action': 'toggle',
            'secret_key': AI_CONTROL_SECRET
        }
        response = requests.post(f"{AI_CONTROL_URL}/webhook/ai-control", 
                               json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            new_status = result.get('active', False)
            status_text = 'فعال' if new_status else 'غیرفعال'
            logger.info(f"وضعیت هوش مصنوعی تغییر کرد: {status_text}")
            return True, f"هوش مصنوعی {status_text} شد", new_status
        else:
            logger.error(f"خطا در تغییر وضعیت هوش مصنوعی: {response.status_code}")
            return False, "خطا در تغییر وضعیت", None
            
    except Exception as e:
        logger.error(f"خطا در تغییر وضعیت هوش مصنوعی: {e}")
        return False, str(e), None

def get_ai_status_info():
    """دریافت اطلاعات کامل وضعیت هوش مصنوعی"""
    try:
        response = requests.get(f"{AI_CONTROL_URL}/api/ai-status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'active': data.get('active', False),
                'last_updated': data.get('last_updated', 0),
                'updated_by': data.get('updated_by', 'نامشخص'),
                'formatted_time': data.get('formatted_time', 'نامشخص')
            }
        else:
            logger.error(f"خطا در دریافت اطلاعات وضعیت: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات وضعیت: {e}")
        return None

# دکوریتور برای بررسی وضعیت هوش مصنوعی
def ai_required(func):
    """دکوریتور برای توابعی که نیاز به فعال بودن هوش مصنوعی دارند"""
    def wrapper(*args, **kwargs):
        if should_ai_respond():
            return func(*args, **kwargs)
        else:
            logger.info(f"تابع {func.__name__} اجرا نشد چون هوش مصنوعی غیرفعال است")
            return None
    return wrapper

# تابع کمکی برای ارسال پیام وضعیت به ادمین
def notify_admin_status_change(chat_id, old_status, new_status, api_url):
    """اطلاع‌رسانی تغییر وضعیت به ادمین"""
    try:
        status_text = 'فعال' if new_status else 'غیرفعال'
        old_status_text = 'فعال' if old_status else 'غیرفعال'
        
        message = f"""🤖 تغییر وضعیت هوش مصنوعی
        
وضعیت قبلی: {old_status_text}
وضعیت جدید: {status_text}
زمان: {json.dumps(get_ai_status_info(), ensure_ascii=False, indent=2)}
کاربر: {chat_id}"""
        
        # ارسال به ادمین (فرض کنیم ADMIN_ID در دسترس است)
        import requests
        requests.post(api_url + "sendMessage", json={
            "chat_id": 6053579919,  # ADMIN_ID از بات اصلی
            "text": message
        })
        
    except Exception as e:
        logger.error(f"خطا در اطلاع‌رسانی به ادمین: {e}")

# کلاس مدیریت هوش مصنوعی
class AIManager:
    def __init__(self, control_url=None, secret_key=None):
        self.control_url = control_url or AI_CONTROL_URL
        self.secret_key = secret_key or AI_CONTROL_SECRET
        self.last_status = None
        
    def is_active(self):
        """بررسی وضعیت فعال بودن"""
        return check_ai_status()
    
    def activate(self):
        """فعال کردن"""
        return activate_ai()
    
    def deactivate(self):
        """غیرفعال کردن"""
        return deactivate_ai()
    
    def toggle(self):
        """تغییر وضعیت"""
        return toggle_ai()
    
    def get_status(self):
        """دریافت وضعیت کامل"""
        return get_ai_status_info()
    
    def should_respond(self, chat_id=None, message=None):
        """تعیین پاسخ‌دهی"""
        return should_ai_respond(chat_id, message)

# نمونه استفاده
if __name__ == "__main__":
    # تست توابع
    print("🧪 تست سیستم کنترل هوش مصنوعی")
    
    # بررسی وضعیت
    status = check_ai_status()
    print(f"📊 وضعیت فعلی: {'فعال' if status else 'غیرفعال'}")
    
    # دریافت اطلاعات کامل
    info = get_ai_status_info()
    if info:
        print(f"📋 اطلاعات کامل: {json.dumps(info, ensure_ascii=False, indent=2)}")
    
    # تست تغییر وضعیت
    success, message, new_status = toggle_ai()
    if success:
        print(f"✅ {message} - وضعیت جدید: {'فعال' if new_status else 'غیرفعال'}")
    else:
        print(f"❌ خطا: {message}")