import os
import json
import time
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger("subscription_handlers")

class SubscriptionManager:
    """مدیریت اشتراک‌های کاربران"""
    
    def __init__(self, subscription_file: str, db_manager=None):
        self.subscription_file = subscription_file
        self.db_manager = db_manager
        self.subscriptions = self._load_subscriptions()
        
        # طرح‌های اشتراک
        self.plans = {
            "1month": {"price": 100, "days": 30, "title": "یک ماهه"},
            "3month": {"price": 250, "days": 90, "title": "سه ماهه"},
            "6month": {"price": 450, "days": 180, "title": "شش ماهه"},
            "12month": {"price": 800, "days": 365, "title": "یک ساله"}
        }
    
    def _load_subscriptions(self) -> Dict:
        """بارگذاری اطلاعات اشتراک‌ها از فایل"""
        if self.db_manager:
            return self.db_manager.data.get('subscriptions', {})
            
        try:
            if os.path.exists(self.subscription_file):
                with open(self.subscription_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading subscriptions: {e}")
            return {}
    
    def _save_subscriptions(self) -> None:
        """ذخیره اطلاعات اشتراک‌ها در فایل"""
        if self.db_manager:
            self.db_manager.data['subscriptions'] = self.subscriptions
            self.db_manager.save_data('subscriptions')
            return
            
        try:
            with open(self.subscription_file, 'w', encoding='utf-8') as f:
                json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving subscriptions: {e}")
    
    def is_subscribed(self, user_id: Union[int, str]) -> bool:
        """بررسی اشتراک کاربر"""
        user_id = str(user_id)
        if user_id not in self.subscriptions:
            return False
            
        subscription = self.subscriptions[user_id]
        if not subscription.get("active", False):
            return False
            
        expiry = subscription.get("expiry", 0)
        return expiry > time.time()
    
    def get_subscription_info(self, user_id: Union[int, str]) -> Dict:
        """دریافت اطلاعات اشتراک کاربر"""
        user_id = str(user_id)
        if user_id not in self.subscriptions:
            return {"active": False, "days_left": 0}
            
        subscription = self.subscriptions[user_id]
        if not subscription.get("active", False):
            return {"active": False, "days_left": 0}
            
        expiry = subscription.get("expiry", 0)
        current_time = time.time()
        
        if expiry <= current_time:
            subscription["active"] = False
            self._save_subscriptions()
            return {"active": False, "days_left": 0}
            
        days_left = int((expiry - current_time) / (24 * 3600))
        return {
            "active": True,
            "days_left": days_left,
            "plan": subscription.get("plan", ""),
            "start_date": subscription.get("start_date", 0),
            "expiry": expiry
        }
    
    def activate_subscription(self, user_id: Union[int, str], plan_id: str) -> Dict:
        """فعال‌سازی اشتراک برای کاربر"""
        user_id = str(user_id)
        
        if plan_id not in self.plans:
            return {"success": False, "message": "طرح اشتراک نامعتبر است."}
            
        plan = self.plans[plan_id]
        days = plan["days"]
        
        current_time = time.time()
        
        # اگر کاربر قبلاً اشتراک داشته و هنوز فعال است، تمدید می‌کنیم
        if user_id in self.subscriptions and self.subscriptions[user_id].get("active", False):
            expiry = self.subscriptions[user_id].get("expiry", current_time)
            if expiry > current_time:
                new_expiry = expiry + (days * 24 * 3600)
            else:
                new_expiry = current_time + (days * 24 * 3600)
        else:
            new_expiry = current_time + (days * 24 * 3600)
        
        self.subscriptions[user_id] = {
            "active": True,
            "plan": plan_id,
            "start_date": current_time,
            "expiry": new_expiry
        }
        
        self._save_subscriptions()
        
        return {
            "success": True,
            "message": f"اشتراک {plan['title']} با موفقیت فعال شد.",
            "days": days
        }
    
    def activate_trial(self, user_id: Union[int, str]) -> Dict:
        """فعال‌سازی دوره آزمایشی رایگان"""
        user_id = str(user_id)
        
        # بررسی استفاده قبلی از دوره آزمایشی
        if self.has_used_trial(user_id):
            return {"success": False, "message": "شما قبلاً از دوره آزمایشی استفاده کرده‌اید."}
        
        current_time = time.time()
        trial_days = 3  # دوره آزمایشی 3 روزه
        
        self.subscriptions[user_id] = {
            "active": True,
            "plan": "trial",
            "start_date": current_time,
            "expiry": current_time + (trial_days * 24 * 3600),
            "trial_used": True
        }
        
        self._save_subscriptions()
        
        return {
            "success": True,
            "message": "دوره آزمایشی رایگان با موفقیت فعال شد.",
            "days": trial_days
        }
    
    def has_used_trial(self, user_id: Union[int, str]) -> bool:
        """بررسی استفاده قبلی از دوره آزمایشی"""
        user_id = str(user_id)
        
        if user_id not in self.subscriptions:
            return False
            
        return self.subscriptions[user_id].get("trial_used", False)
    
    def cancel_subscription(self, user_id: Union[int, str]) -> Dict:
        """لغو اشتراک کاربر"""
        user_id = str(user_id)
        
        if user_id not in self.subscriptions:
            return {"success": False, "message": "شما اشتراک فعالی ندارید."}
            
        if not self.subscriptions[user_id].get("active", False):
            return {"success": False, "message": "شما اشتراک فعالی ندارید."}
            
        self.subscriptions[user_id]["active"] = False
        self._save_subscriptions()
        
        return {"success": True, "message": "اشتراک شما با موفقیت لغو شد."}
    
    def get_all_plans(self) -> Dict:
        """دریافت تمام طرح‌های اشتراک"""
        return self.plans