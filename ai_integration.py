import os
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, Tuple
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import random

logger = logging.getLogger("ai_integration")

class AIManager:
    """مدیر هوش مصنوعی پیشرفته با قابلیت پردازش تصویر"""
    
    def __init__(self):
        self.n8n_webhook_url = os.environ.get('N8N_AI_WEBHOOK_URL')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.status_file = "ai_status.json"
        self.backgrounds_cache = {}
        
        # تنظیمات پیش‌فرض برای تولید تصویر
        self.default_backgrounds = {
            "gradient": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            "solid": ["#2C3E50", "#E74C3C", "#3498DB", "#2ECC71", "#F39C12"],
            "patterns": ["dots", "stripes", "waves", "geometric"]
        }
        
        logger.info("✅ AI Manager initialized with enhanced image processing")
    
    def should_respond(self, chat_id: int, message: str) -> bool:
        """تعیین اینکه آیا هوش مصنوعی باید پاسخ دهد"""
        try:
            # بررسی وضعیت کلی
            if not self.check_status():
                return False
            
            # قوانین پاسخ‌دهی
            if message.startswith('/'):
                return False
            
            if len(message.strip()) < 2:
                return False
            
            # کلمات کلیدی که نیاز به پردازش هوش مصنوعی دارند
            ai_keywords = [
                'بساز', 'درست کن', 'تصویر', 'عکس', 'استیکر', 'بک‌گراند', 
                'رنگ', 'طراحی', 'make', 'create', 'image', 'picture', 'design'
            ]
            
            message_lower = message.lower()
            return any(keyword in message_lower for keyword in ai_keywords)
            
        except Exception as e:
            logger.error(f"Error in should_respond: {e}")
            return False
    
    def process_message(self, chat_id: int, message: str) -> Dict[str, Any]:
        """پردازش پیام با هوش مصنوعی"""
        try:
            # اول سعی کن از n8n استفاده کنی
            if self.n8n_webhook_url:
                n8n_result = self._send_to_n8n(chat_id, message)
                if n8n_result:
                    return n8n_result
            
            # اگر n8n کار نکرد، از سیستم محلی استفاده کن
            return self._process_locally(chat_id, message)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._generate_error_response(str(e))
    
    def _send_to_n8n(self, chat_id: int, message: str) -> Optional[Dict[str, Any]]:
        """ارسال به n8n با retry mechanism"""
        try:
            payload = {
                "chat_id": chat_id,
                "message": message,
                "timestamp": time.time(),
                "request_type": "sticker_generation",
                "language": "persian"
            }
            
            # ارسال با timeout و retry
            for attempt in range(3):
                try:
                    response = requests.post(
                        self.n8n_webhook_url, 
                        json=payload, 
                        timeout=30,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ N8N response received for chat_id={chat_id}")
                        return self._process_n8n_response(result)
                    else:
                        logger.warning(f"N8N returned status {response.status_code}, attempt {attempt + 1}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"N8N timeout, attempt {attempt + 1}")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"N8N request error: {e}, attempt {attempt + 1}")
                
                if attempt < 2:  # فقط برای دو تلاش اول
                    time.sleep(1)
            
            logger.error("❌ All N8N attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"Error sending to N8N: {e}")
            return None
    
    def _process_n8n_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """پردازش پاسخ n8n"""
        try:
            return {
                "create_sticker": response.get("create_sticker", True),
                "sticker_text": response.get("sticker_text", response.get("text", "")),
                "response": response.get("response", "استیکر شما آماده است!"),
                "background_type": response.get("background_type", "gradient"),
                "background_colors": response.get("background_colors", ["#FF6B6B", "#4ECDC4"]),
                "image_url": response.get("image_url"),
                "background_description": response.get("background_description"),
                "enhanced": True
            }
        except Exception as e:
            logger.error(f"Error processing N8N response: {e}")
            return self._generate_error_response("خطا در پردازش پاسخ N8N")
    
    def _process_locally(self, chat_id: int, message: str) -> Dict[str, Any]:
        """پردازش محلی پیشرفته با تولید بک‌گراند"""
        try:
            message_lower = message.lower()
            
            # تشخیص نوع درخواست
            request_analysis = self._analyze_request(message)
            
            # تولید بک‌گراند مناسب
            background_info = self._generate_background(request_analysis)
            
            # تعیین متن استیکر
            sticker_text = self._extract_sticker_text(message, request_analysis)
            
            return {
                "create_sticker": True,
                "sticker_text": sticker_text,
                "response": self._generate_response_text(request_analysis),
                "background_type": background_info["type"],
                "background_colors": background_info["colors"],
                "background_pattern": background_info.get("pattern"),
                "background_description": background_info["description"],
                "enhanced": True,
                "local_processing": True
            }
            
        except Exception as e:
            logger.error(f"Error in local processing: {e}")
            return self._generate_error_response(str(e))
    
    def _analyze_request(self, message: str) -> Dict[str, Any]:
        """تحلیل درخواست کاربر"""
        message_lower = message.lower()
        
        analysis = {
            "colors": [],
            "mood": "neutral",
            "style": "modern",
            "complexity": "simple",
            "theme": "general"
        }
        
        # تشخیص رنگ‌ها
        color_keywords = {
            "قرمز": "#E74C3C", "آبی": "#3498DB", "سبز": "#2ECC71", 
            "زرد": "#F1C40F", "نارنجی": "#E67E22", "بنفش": "#9B59B6",
            "صورتی": "#E91E63", "طوسی": "#95A5A6", "مشکی": "#2C3E50",
            "سفید": "#ECF0F1", "red": "#E74C3C", "blue": "#3498DB", 
            "green": "#2ECC71", "yellow": "#F1C40F", "orange": "#E67E22"
        }
        
        for keyword, color in color_keywords.items():
            if keyword in message_lower:
                analysis["colors"].append(color)
        
        # تشخیص حالت
        if any(word in message_lower for word in ["شاد", "خوشحال", "happy", "جشن"]):
            analysis["mood"] = "happy"
        elif any(word in message_lower for word in ["غمگین", "ناراحت", "sad", "غم"]):
            analysis["mood"] = "sad"
        elif any(word in message_lower for word in ["عاشقانه", "love", "قلب", "دوست"]):
            analysis["mood"] = "romantic"
        
        # تشخیص سبک
        if any(word in message_lower for word in ["مدرن", "modern", "جدید"]):
            analysis["style"] = "modern"
        elif any(word in message_lower for word in ["کلاسیک", "classic", "قدیمی"]):
            analysis["style"] = "classic"
        elif any(word in message_lower for word in ["هنری", "artistic", "هنر"]):
            analysis["style"] = "artistic"
        
        return analysis
    
    def _generate_background(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """تولید بک‌گراند بر اساس تحلیل"""
        try:
            # انتخاب رنگ‌ها
            if analysis["colors"]:
                colors = analysis["colors"][:3]  # حداکثر 3 رنگ
            else:
                # انتخاب رنگ بر اساس حالت
                mood_colors = {
                    "happy": ["#FFD93D", "#6BCF7F", "#4D96FF"],
                    "sad": ["#6C7B7F", "#9BB5FF", "#B8860B"],
                    "romantic": ["#FF6B9D", "#C44569", "#F8B500"],
                    "neutral": ["#667eea", "#764ba2", "#f093fb"]
                }
                colors = mood_colors.get(analysis["mood"], mood_colors["neutral"])
            
            # تعیین نوع بک‌گراند
            background_types = ["gradient", "solid", "pattern"]
            bg_type = random.choice(background_types)
            
            if bg_type == "gradient":
                return {
                    "type": "gradient",
                    "colors": colors[:2],  # گرادیان با 2 رنگ
                    "description": f"گرادیان زیبا با رنگ‌های {', '.join(colors[:2])}"
                }
            elif bg_type == "solid":
                return {
                    "type": "solid",
                    "colors": [colors[0]],
                    "description": f"بک‌گراند ساده با رنگ {colors[0]}"
                }
            else:  # pattern
                pattern = random.choice(self.default_backgrounds["patterns"])
                return {
                    "type": "pattern",
                    "colors": colors[:2],
                    "pattern": pattern,
                    "description": f"الگوی {pattern} با رنگ‌های زیبا"
                }
                
        except Exception as e:
            logger.error(f"Error generating background: {e}")
            return {
                "type": "gradient",
                "colors": ["#667eea", "#764ba2"],
                "description": "بک‌گراند پیش‌فرض"
            }
    
    def _extract_sticker_text(self, message: str, analysis: Dict[str, Any]) -> str:
        """استخراج متن مناسب برای استیکر"""
        # اگر پیام کوتاه است، همان را استفاده کن
        if len(message) <= 20:
            return message
        
        # اگر پیام طولانی است، خلاصه کن
        words = message.split()
        if len(words) <= 3:
            return message
        
        # انتخاب کلمات مهم
        important_words = []
        skip_words = ["بساز", "درست کن", "یک", "یه", "برام", "برای من", "لطفا"]
        
        for word in words:
            if word not in skip_words and len(important_words) < 3:
                important_words.append(word)
        
        return " ".join(important_words) if important_words else message[:20]
    
    def _generate_response_text(self, analysis: Dict[str, Any]) -> str:
        """تولید متن پاسخ"""
        responses = [
            "🎨 استیکر زیبای شما با هوش مصنوعی آماده شد!",
            "✨ یک استیکر فوق‌العاده برای شما طراحی کردم!",
            "🤖 هوش مصنوعی استیکر خاص شما را ساخت!",
            "🎯 استیکر شما با بهترین کیفیت آماده است!",
            "💫 استیکر هوشمند شما تکمیل شد!"
        ]
        
        return random.choice(responses)
    
    def _generate_error_response(self, error_msg: str) -> Dict[str, Any]:
        """تولید پاسخ خطا"""
        return {
            "create_sticker": False,
            "response": f"❌ متأسفانه خطایی رخ داد: {error_msg}\n\n🔄 لطفاً دوباره تلاش کنید.",
            "error": True
        }
    
    def check_status(self) -> bool:
        """بررسی وضعیت هوش مصنوعی"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                return status.get("active", False)
            return False
        except Exception as e:
            logger.error(f"Error checking AI status: {e}")
            return False
    
    def set_status(self, active: bool, updated_by: str = "system") -> bool:
        """تنظیم وضعیت هوش مصنوعی"""
        try:
            status = {
                "active": active,
                "last_updated": time.time(),
                "updated_by": updated_by
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            
            logger.info(f"AI status set to {active} by {updated_by}")
            return True
        except Exception as e:
            logger.error(f"Error setting AI status: {e}")
            return False

# توابع کمکی برای سازگاری با کد اصلی
def should_ai_respond(chat_id: int, message: str) -> bool:
    """تابع سازگاری برای کد اصلی"""
    try:
        ai_manager = AIManager()
        return ai_manager.should_respond(chat_id, message)
    except Exception as e:
        logger.error(f"Error in should_ai_respond: {e}")
        return False

def check_ai_status() -> bool:
    """بررسی وضعیت هوش مصنوعی"""
    try:
        ai_manager = AIManager()
        return ai_manager.check_status()
    except Exception as e:
        logger.error(f"Error checking AI status: {e}")
        return False

def activate_ai(updated_by: str = "system") -> bool:
    """فعال کردن هوش مصنوعی"""
    try:
        ai_manager = AIManager()
        return ai_manager.set_status(True, updated_by)
    except Exception as e:
        logger.error(f"Error activating AI: {e}")
        return False

def deactivate_ai(updated_by: str = "system") -> bool:
    """غیرفعال کردن هوش مصنوعی"""
    try:
        ai_manager = AIManager()
        return ai_manager.set_status(False, updated_by)
    except Exception as e:
        logger.error(f"Error deactivating AI: {e}")
        return False

def toggle_ai(updated_by: str = "system") -> bool:
    """تغییر وضعیت هوش مصنوعی"""
    try:
        ai_manager = AIManager()
        current_status = ai_manager.check_status()
        return ai_manager.set_status(not current_status, updated_by)
    except Exception as e:
        logger.error(f"Error toggling AI: {e}")
        return False
