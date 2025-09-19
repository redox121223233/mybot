import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("menu_handlers")

class MenuManager:
    """مدیریت منوها و دکمه‌های ربات"""
    
    def __init__(self, api_url: str, bot_token: str):
        self.api_url = api_url
        self.bot_token = bot_token
    
    def show_subscription_menu(self, chat_id: int, message_id: Optional[int] = None):
        """نمایش منوی اشتراک"""
        from bot import is_subscribed, get_subscription_info, api
        
        # بررسی وضعیت اشتراک کاربر
        if is_subscribed(chat_id):
            # نمایش اطلاعات اشتراک فعلی
            sub_info = get_subscription_info(chat_id)
            days_left = sub_info.get("days_left", 0)
            
            text = f"🔹 اشتراک شما فعال است\n\n"
            text += f"🔸 {days_left} روز باقیمانده از اشتراک\n\n"
            text += "برای تمدید اشتراک یکی از گزینه‌های زیر را انتخاب کنید:"
        else:
            # نمایش گزینه‌های خرید اشتراک
            text = "💎 خرید اشتراک\n\n"
            text += "با خرید اشتراک به تمام امکانات ربات دسترسی خواهید داشت.\n\n"
            text += "لطفاً یکی از طرح‌های زیر را انتخاب کنید:"
        
        # ساخت دکمه‌های طرح‌های اشتراک
        keyboard = []
        from bot import subscription_manager
        for plan_id, plan in subscription_manager.plans.items():
            title = plan["title"]
            price = plan["price"]
            days = plan["days"]
            keyboard.append([{"text": f"✅ {title} - {price} هزار تومان", "callback_data": f"sub_{plan_id}"}])
        
        # دکمه بازگشت
        keyboard.append([{"text": "🔙 بازگشت", "callback_data": "back_to_main"}])
        
        reply_markup = {"inline_keyboard": keyboard}
        
        # ارسال یا ویرایش پیام
        if message_id:
            return self._edit_message(chat_id, message_id, text, reply_markup)
        else:
            return send_message(chat_id, text, reply_markup)
    
    def show_free_trial_menu(self, chat_id: int, message_id: Optional[int] = None):
        """نمایش منوی دوره آزمایشی رایگان"""
        from bot import has_used_trial, send_message
        
        if has_used_trial(chat_id):
            text = "⚠️ شما قبلاً از دوره آزمایشی رایگان استفاده کرده‌اید."
            text += "\n\nبرای استفاده از امکانات ویژه، لطفاً اشتراک تهیه کنید."
            
            keyboard = [
                [{"text": "💎 خرید اشتراک", "callback_data": "show_subscription"}],
                [{"text": "🔙 بازگشت", "callback_data": "back_to_main"}]
            ]
        else:
            text = "🎁 دوره آزمایشی رایگان\n\n"
            text += "با فعال‌سازی دوره آزمایشی رایگان، به مدت 3 روز به تمام امکانات ربات دسترسی خواهید داشت."
            
            keyboard = [
                [{"text": "✅ فعال‌سازی دوره آزمایشی", "callback_data": "activate_trial"}],
                [{"text": "🔙 بازگشت", "callback_data": "back_to_main"}]
            ]
        
        reply_markup = {"inline_keyboard": keyboard}
        
        # ارسال یا ویرایش پیام
        if message_id:
            return self._edit_message(chat_id, message_id, text, reply_markup)
        else:
            return send_message(chat_id, text, reply_markup)
    
    def show_templates_menu(self, chat_id: int, message_id: Optional[int] = None):
        """نمایش منوی قالب‌های آماده"""
        from bot import send_message
        
        text = "🖼 قالب‌های آماده\n\n"
        text += "از قالب‌های آماده زیر برای ساخت استیکر استفاده کنید:"
        
        # قالب‌های موجود
        templates = [
            ("تولد", "birthday"),
            ("عاشقانه", "love"),
            ("خنده‌دار", "funny"),
            ("خانوادگی", "family"),
            ("مهمانی", "party"),
            ("کاری", "work"),
            ("تحصیلی", "education"),
            ("عروسی", "wedding"),
            ("هیجان‌انگیز", "exciting")
        ]
        
        # ساخت دکمه‌ها
        keyboard = []
        row = []
        
        for i, (title, template_id) in enumerate(templates):
            row.append({"text": title, "callback_data": f"template_{template_id}"})
            
            # هر ردیف 3 دکمه
            if (i + 1) % 3 == 0 or i == len(templates) - 1:
                keyboard.append(row)
                row = []
        
        # دکمه بازگشت
        keyboard.append([{"text": "🔙 بازگشت", "callback_data": "back_to_main"}])
        
        reply_markup = {"inline_keyboard": keyboard}
        
        # ارسال یا ویرایش پیام
        if message_id:
            return self._edit_message(chat_id, message_id, text, reply_markup)
        else:
            return send_message(chat_id, text, reply_markup)
    
    def _edit_message(self, chat_id: int, message_id: int, text: str, reply_markup: Dict) -> Dict:
        """ویرایش پیام با استفاده از API تلگرام"""
        import requests
        
        url = f"{self.api_url}editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "reply_markup": json.dumps(reply_markup),
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return {"ok": False, "description": str(e)}