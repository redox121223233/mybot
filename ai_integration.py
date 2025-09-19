import os
import json
import time
import base64
import logging
import random
from io import BytesIO
from PIL import Image
import requests

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sticker_maker")

# مسیر فایل تنظیمات
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_settings.json")

# تنظیمات پیش‌فرض استیکرساز
DEFAULT_AI_SETTINGS = {
    "enabled": False,  # غیرفعال به صورت پیش‌فرض
    "greeting_message": "سلام! من دستیار هوشمند استیکرساز هستم. چطور می‌توانم به شما کمک کنم؟",
    "confirmation_message": "آیا می‌خواهید این را به استیکر تبدیل کنم؟",
    "sticker_styles": ["ساده", "کارتونی", "پیکسلی", "نئون"],
    "default_style": "ساده"
}

# پاسخ‌های آماده برای استیکرساز
STICKER_RESPONSES = [
    "استیکر شما آماده شد! 🎉",
    "بفرمایید استیکر جدید شما! ✨",
    "استیکر ساخته شد! امیدوارم خوشتون بیاد! 😊",
    "تمام شد! استیکر جدید شما آماده است! 🌟",
    "استیکر شما با موفقیت ساخته شد! 🎨"
]

# پاسخ‌های خوش‌آمدگویی
GREETING_RESPONSES = [
    "سلام! من استیکرساز هستم. می‌توانم برای شما استیکرهای جذاب بسازم! 🎨",
    "درود! استیکرساز فعال شد. متن یا تصویری ارسال کنید تا برایتان استیکر بسازم! ✨",
    "سلام دوست من! من اینجا هستم تا برایتان استیکرهای زیبا بسازم! 🌟",
    "به استیکرساز خوش آمدید! آماده‌ام تا محتوای شما را به استیکرهای جذاب تبدیل کنم! 🎭"
]

class AIManager:
    """مدیریت هوش مصنوعی استیکرساز"""
    
    def __init__(self):
        """مقداردهی اولیه مدیر استیکرساز"""
        self.settings = self._load_settings()
        self.enabled = self.settings.get("enabled", False)
        self.waiting_for_confirmation = {}  # ذخیره وضعیت انتظار برای تأیید کاربران
        logger.info(f"Sticker Maker initialized. Enabled: {self.enabled}")
    
    def _load_settings(self):
        """بارگذاری تنظیمات از فایل"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    logger.info("Sticker maker settings loaded from file")
                    return settings
        except Exception as e:
            logger.error(f"Error loading sticker maker settings: {e}")
        
        # استفاده از تنظیمات پیش‌فرض
        logger.info("Using default sticker maker settings")
        return DEFAULT_AI_SETTINGS
    
    def _save_settings(self):
        """ذخیره تنظیمات در فایل"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            logger.info("Sticker maker settings saved to file")
        except Exception as e:
            logger.error(f"Error saving sticker maker settings: {e}")
    
    def toggle_ai(self, enabled=None):
        """فعال یا غیرفعال کردن استیکرساز"""
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = not self.enabled
        
        self.settings["enabled"] = self.enabled
        self._save_settings()
        
        return self.enabled
    
    def get_greeting(self):
        """دریافت پیام خوش‌آمدگویی تصادفی"""
        if not self.enabled:
            return None
        
        return random.choice(GREETING_RESPONSES)
    
    def process_input(self, input_data, input_type, user_id, caption=None):
        """پردازش ورودی کاربر (متن، تصویر، گیف، استیکر)"""
        if not self.enabled:
            logger.info("Sticker maker is disabled")
            return None, None
        
        # بررسی آیا کاربر در حالت انتظار تأیید است
        if user_id in self.waiting_for_confirmation:
            # حذف از لیست انتظار
            del self.waiting_for_confirmation[user_id]
            return None, "درخواست قبلی شما لغو شد. لطفاً محتوای جدیدی ارسال کنید."
        
        try:
            # آماده‌سازی داده‌ها برای تبدیل به استیکر
            if input_type == "text":
                # متن را برای تبدیل به استیکر آماده می‌کنیم
                preview_text = input_data[:20] + "..." if len(input_data) > 20 else input_data
                self.waiting_for_confirmation[user_id] = {
                    "type": "text",
                    "data": input_data,
                    "style": self.settings.get("default_style", "ساده")
                }
                return None, f"{self.settings.get('confirmation_message', 'آیا می‌خواهید این را به استیکر تبدیل کنم؟')}\n\n\"{preview_text}\""
            
            elif input_type in ["image", "gif", "sticker"]:
                # تصویر را برای تبدیل به استیکر آماده می‌کنیم
                if isinstance(input_data, bytes):
                    # ذخیره موقت تصویر
                    self.waiting_for_confirmation[user_id] = {
                        "type": input_type,
                        "data": input_data,
                        "caption": caption,
                        "style": self.settings.get("default_style", "ساده")
                    }
                    return None, f"{self.settings.get('confirmation_message', 'آیا می‌خواهید این را به استیکر تبدیل کنم؟')}"
                else:
                    return None, "خطا در پردازش تصویر. لطفاً دوباره تلاش کنید."
            
            else:
                return None, "این نوع محتوا پشتیبانی نمی‌شود. لطفاً متن، تصویر، گیف یا استیکر ارسال کنید."
                
        except Exception as e:
            logger.error(f"Error in processing input: {e}")
            return None, "خطا در پردازش ورودی. لطفاً دوباره تلاش کنید."
    
    def confirm_sticker_creation(self, user_id, style=None):
        """تأیید ساخت استیکر توسط کاربر"""
        if not self.enabled or user_id not in self.waiting_for_confirmation:
            return None, "درخواستی برای تأیید وجود ندارد. لطفاً ابتدا محتوایی ارسال کنید."
        
        try:
            # دریافت اطلاعات ذخیره شده
            request_data = self.waiting_for_confirmation[user_id]
            input_type = request_data["type"]
            input_data = request_data["data"]
            
            # اگر سبک جدید انتخاب شده، آن را جایگزین می‌کنیم
            if style and style in self.settings.get("sticker_styles", ["ساده"]):
                request_data["style"] = style
            
            # ساخت استیکر بر اساس نوع ورودی
            if input_type == "text":
                sticker_data = self._create_text_sticker(input_data, request_data["style"])
            else:  # image, gif, sticker
                caption = request_data.get("caption", "")
                sticker_data = self._create_image_sticker(input_data, caption, request_data["style"])
            
            # حذف از لیست انتظار
            del self.waiting_for_confirmation[user_id]
            
            # پاسخ موفقیت‌آمیز
            return sticker_data, random.choice(STICKER_RESPONSES)
            
        except Exception as e:
            logger.error(f"Error in creating sticker: {e}")
            # حذف از لیست انتظار در صورت خطا
            if user_id in self.waiting_for_confirmation:
                del self.waiting_for_confirmation[user_id]
            return None, "خطا در ساخت استیکر. لطفاً دوباره تلاش کنید."
    
    def cancel_sticker_creation(self, user_id):
        """لغو ساخت استیکر توسط کاربر"""
        if user_id in self.waiting_for_confirmation:
            del self.waiting_for_confirmation[user_id]
            return "درخواست ساخت استیکر لغو شد."
        return "درخواستی برای لغو وجود ندارد."
    
    def get_available_styles(self):
        """دریافت سبک‌های موجود برای استیکر"""
        return self.settings.get("sticker_styles", ["ساده"])
    
    def _create_text_sticker(self, text, style="ساده"):
        """ساخت استیکر از متن"""
        try:
            # ایجاد یک تصویر خالی
            width, height = 512, 512
            background_color = (255, 255, 255)
            
            if style == "نئون":
                background_color = (0, 0, 0)  # پس‌زمینه سیاه برای نئون
            
            image = Image.new('RGBA', (width, height), background_color)
            
            # تبدیل به استیکر و بازگرداندن
            output = BytesIO()
            image.save(output, format='PNG')
            output.seek(0)
            
            return output
            
        except Exception as e:
            logger.error(f"Error creating text sticker: {e}")
            raise
    
    def _create_image_sticker(self, image_data, caption=None, style="ساده"):
        """ساخت استیکر از تصویر"""
        try:
            # تبدیل داده‌های تصویر به شیء تصویر
            if isinstance(image_data, bytes):
                image = Image.open(BytesIO(image_data))
            else:
                image = image_data
            
            # تغییر اندازه تصویر به 512x512 با حفظ نسبت
            width, height = image.size
            new_size = 512
            
            if width > height:
                new_height = int(height * new_size / width)
                new_width = new_size
            else:
                new_width = int(width * new_size / height)
                new_height = new_size
            
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # ایجاد تصویر جدید با پس‌زمینه شفاف
            new_image = Image.new('RGBA', (new_size, new_size), (0, 0, 0, 0))
            
            # قرار دادن تصویر اصلی در مرکز
            paste_x = (new_size - new_width) // 2
            paste_y = (new_size - new_height) // 2
            new_image.paste(resized_image, (paste_x, paste_y))
            
            # اعمال افکت بر اساس سبک
            if style == "کارتونی":
                # افکت کارتونی ساده
                new_image = self._apply_cartoon_effect(new_image)
            elif style == "پیکسلی":
                # افکت پیکسلی
                new_image = self._apply_pixel_effect(new_image)
            elif style == "نئون":
                # افکت نئون
                new_image = self._apply_neon_effect(new_image)
            
            # تبدیل به استیکر و بازگرداندن
            output = BytesIO()
            new_image.save(output, format='PNG')
            output.seek(0)
            
            return output
            
        except Exception as e:
            logger.error(f"Error creating image sticker: {e}")
            raise
    
    def _apply_cartoon_effect(self, image):
        """اعمال افکت کارتونی ساده روی تصویر"""
        # در اینجا می‌توانید افکت‌های پیچیده‌تری اضافه کنید
        return image
    
    def _apply_pixel_effect(self, image):
        """اعمال افکت پیکسلی روی تصویر"""
        # کاهش اندازه و سپس بزرگنمایی برای ایجاد افکت پیکسلی
        small_size = 64
        pixelated = image.resize((small_size, small_size), Image.NEAREST)
        return pixelated.resize(image.size, Image.NEAREST)
    
    def _apply_neon_effect(self, image):
        """اعمال افکت نئون روی تصویر"""
        # در اینجا می‌توانید افکت‌های پیچیده‌تری اضافه کنید
        return image
    
    def generate_image_from_text(self, prompt, user_id=None, username=None):
        """تولید تصویر از متن با استفاده از هوش مصنوعی"""
        if not self.enabled:
            logger.info("AI image generation is disabled")
            return None, "هوش مصنوعی غیرفعال است."
        
        try:
            # استفاده از n8n اگر آدرس آن تنظیم شده باشد
            if N8N_WORKFLOW_URL:
                response_text = self._process_with_n8n(prompt, None, user_id, username, is_image_generation=True)
                # اگر n8n تصویر را به صورت base64 برگرداند
                if response_text and response_text.startswith("data:image"):
                    image_data = response_text.split(",")[1]
                    return BytesIO(base64.b64decode(image_data)), None
                return None, response_text
            
            # استفاده از Replicate اگر فعال باشد
            if self.settings.get("use_replicate", True) and REPLICATE_API_KEY:
                image_data, error = self._generate_image_with_replicate(prompt)
                if image_data:
                    return image_data, None
                return None, error or "خطا در تولید تصویر با Replicate"
            
            # استفاده از Hugging Face اگر فعال باشد
            if self.settings.get("use_huggingface", True) and HUGGINGFACE_API_KEY:
                image_data, error = self._generate_image_with_huggingface(prompt)
                if image_data:
                    return image_data, None
                return None, error or "خطا در تولید تصویر با Hugging Face"
            
            # اگر هیچ سرویسی تنظیم نشده باشد
            logger.warning("No AI service configured for image generation")
            return None, "متأسفانه سرویس تولید تصویر در دسترس نیست."
            
        except Exception as e:
            logger.error(f"Error in AI image generation: {e}")
            return None, f"خطا در تولید تصویر: {str(e)}"
    
    def _process_with_n8n(self, text, image_base64=None, user_id=None, username=None, is_image_generation=False):
        """پردازش با استفاده از n8n workflow"""
        try:
            payload = {
                "text": text or "",
                "user_id": user_id or "unknown",
                "username": username or "unknown",
                "timestamp": time.time(),
                "is_image_generation": is_image_generation
            }
            
            # اضافه کردن تصویر اگر موجود باشد
            if image_base64:
                payload["image"] = image_base64
            
            # ارسال درخواست به n8n
            response = requests.post(
                N8N_WORKFLOW_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60  # زمان بیشتر برای تولید تصویر
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "پاسخی از سرویس هوش مصنوعی دریافت نشد.")
            else:
                logger.error(f"n8n API error: {response.status_code} - {response.text}")
                return f"خطا در ارتباط با سرویس هوش مصنوعی. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in n8n processing: {e}")
            return "خطا در ارتباط با سرویس n8n."
    
    def _process_with_openai(self, text):
        """پردازش متن با استفاده از OpenAI API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": self.settings.get("model", "gpt-3.5-turbo"),
                "messages": [
                    {"role": "system", "content": "شما یک دستیار هوشمند در یک ربات تلگرام هستید که به کاربران کمک می‌کنید. پاسخ‌های کوتاه و مفید بدهید."},
                    {"role": "user", "content": text}
                ],
                "max_tokens": self.settings.get("max_tokens", 150),
                "temperature": self.settings.get("temperature", 0.7)
            }
            
            response = requests.post(
                AI_SERVICE_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return f"خطا در ارتباط با سرویس OpenAI. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in OpenAI processing: {e}")
            return "خطا در ارتباط با سرویس OpenAI."
    
    def _process_image_with_openai(self, image_base64, caption=None):
        """پردازش تصویر با استفاده از OpenAI API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            # ساخت پیام‌ها با تصویر
            messages = [
                {"role": "system", "content": "شما یک دستیار هوشمند در یک ربات تلگرام هستید که به کاربران کمک می‌کنید. پاسخ‌های کوتاه و مفید بدهید."}
            ]
            
            # اضافه کردن پیام کاربر با تصویر
            user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
            
            # اضافه کردن کپشن اگر موجود باشد
            if caption:
                user_message["content"].append({
                    "type": "text",
                    "text": caption
                })
            elif not caption:
                # اگر کپشن نداشته باشیم، یک متن پیش‌فرض اضافه می‌کنیم
                user_message["content"].append({
                    "type": "text",
                    "text": "این تصویر را توصیف کن و در مورد آن توضیح بده."
                })
            
            messages.append(user_message)
            
            payload = {
                "model": "gpt-4-vision-preview",  # مدل با قابلیت پردازش تصویر
                "messages": messages,
                "max_tokens": self.settings.get("max_tokens", 300),
                "temperature": self.settings.get("temperature", 0.7)
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60  # زمان بیشتر برای پردازش تصویر
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenAI Vision API error: {response.status_code} - {response.text}")
                return f"خطا در ارتباط با سرویس پردازش تصویر. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in OpenAI Vision processing: {e}")
            return "خطا در پردازش تصویر با هوش مصنوعی."
    
    def _process_with_huggingface_text(self, text):
        """پردازش متن با استفاده از Hugging Face API"""
        try:
            headers = {
                "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
            }
            
            payload = {
                "inputs": text,
                "parameters": {
                    "max_new_tokens": self.settings.get("max_tokens", 150),
                    "temperature": self.settings.get("temperature", 0.7),
                    "return_full_text": False
                }
            }
            
            model_id = HUGGINGFACE_MODELS["text_to_text"]
            api_url = f"https://api-inference.huggingface.co/models/{model_id}"
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                return "پاسخی از سرویس هوش مصنوعی دریافت نشد."
            else:
                logger.error(f"Hugging Face API error: {response.status_code} - {response.text}")
                return f"خطا در ارتباط با سرویس Hugging Face. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in Hugging Face processing: {e}")
            return "خطا در ارتباط با سرویس Hugging Face."
    
    def _process_with_replicate_image(self, image_base64, caption=None):
        """پردازش تصویر با استفاده از Replicate API"""
        try:
            headers = {
                "Authorization": f"Token {REPLICATE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # استفاده از مدل image-to-text
            model_id = REPLICATE_MODELS["image_to_text"]
            
            payload = {
                "version": model_id,
                "input": {
                    "image": f"data:image/jpeg;base64,{image_base64}",
                    "task": "image_captioning"
                }
            }
            
            # اگر کپشن داشته باشیم، از آن به عنوان راهنما استفاده می‌کنیم
            if caption:
                payload["input"]["caption"] = caption
            
            # ارسال درخواست به Replicate
            response = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                prediction = response.json()
                prediction_id = prediction["id"]
                
                # بررسی وضعیت پیش‌بینی
                status_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
                
                # انتظار برای تکمیل پیش‌بینی
                for _ in range(30):  # حداکثر 30 ثانیه انتظار
                    time.sleep(1)
                    status_response = requests.get(status_url, headers=headers)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data["status"] == "succeeded":
                            return status_data["output"]
                        elif status_data["status"] == "failed":
                            logger.error(f"Replicate prediction failed: {status_data.get('error')}")
                            return f"خطا در پردازش تصویر: {status_data.get('error')}"
                
                return "زمان پردازش تصویر به پایان رسید. لطفاً دوباره تلاش کنید."
            else:
                logger.error(f"Replicate API error: {response.status_code} - {response.text}")
                return f"خطا در ارتباط با سرویس Replicate. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in Replicate processing: {e}")
            return "خطا در پردازش تصویر با Replicate."
    
    def _generate_image_with_huggingface(self, prompt):
        """تولید تصویر با استفاده از Hugging Face API"""
        try:
            headers = {
                "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
            }
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "negative_prompt": "low quality, blurry, distorted",
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5
                }
            }
            
            model_id = HUGGINGFACE_MODELS["text_to_image"]
            api_url = f"https://api-inference.huggingface.co/models/{model_id}"
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                # پاسخ مستقیماً داده‌های تصویر است
                image_bytes = BytesIO(response.content)
                return image_bytes, None
            else:
                logger.error(f"Hugging Face API error: {response.status_code} - {response.text}")
                return None, f"خطا در ارتباط با سرویس Hugging Face. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in Hugging Face image generation: {e}")
            return None, f"خطا در تولید تصویر با Hugging Face: {str(e)}"
    
    def _generate_image_with_replicate(self, prompt):
        """تولید تصویر با استفاده از Replicate API"""
        try:
            headers = {
                "Authorization": f"Token {REPLICATE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            model_id = REPLICATE_MODELS["text_to_image"]
            
            payload = {
                "version": model_id,
                "input": {
                    "prompt": prompt,
                    "negative_prompt": "low quality, blurry, distorted",
                    "num_outputs": 1,
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5
                }
            }
            
            # ارسال درخواست به Replicate
            response = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                prediction = response.json()
                prediction_id = prediction["id"]
                
                # بررسی وضعیت پیش‌بینی
                status_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
                
                # انتظار برای تکمیل پیش‌بینی
                for _ in range(60):  # حداکثر 60 ثانیه انتظار
                    time.sleep(1)
                    status_response = requests.get(status_url, headers=headers)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data["status"] == "succeeded":
                            # دریافت URL تصویر
                            image_url = status_data["output"][0]
                            # دانلود تصویر
                            image_response = requests.get(image_url)
                            if image_response.status_code == 200:
                                image_bytes = BytesIO(image_response.content)
                                return image_bytes, None
                            else:
                                return None, "خطا در دانلود تصویر تولید شده."
                        elif status_data["status"] == "failed":
                            logger.error(f"Replicate prediction failed: {status_data.get('error')}")
                            return None, f"خطا در تولید تصویر: {status_data.get('error')}"
                
                return None, "زمان تولید تصویر به پایان رسید. لطفاً دوباره تلاش کنید."
            else:
                logger.error(f"Replicate API error: {response.status_code} - {response.text}")
                return None, f"خطا در ارتباط با سرویس Replicate. کد خطا: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in Replicate image generation: {e}")
            return None, f"خطا در تولید تصویر با Replicate: {str(e)}"

# --- توابع کمکی برای استفاده در bot.py ---

def should_ai_respond(message, ai_manager):
    """بررسی اینکه آیا هوش مصنوعی باید به پیام پاسخ دهد یا خیر"""
    # اگر هوش مصنوعی غیرفعال باشد
    if not ai_manager.enabled:
        return False
    
    # اگر پیام دستور باشد، هوش مصنوعی پاسخ ندهد
    if message.startswith('/'):
        return False
    
    # در غیر این صورت پاسخ دهد
    return True

def check_ai_status(ai_manager):
    """بررسی وضعیت هوش مصنوعی"""
    return {
        "enabled": ai_manager.enabled,
        "image_processing": ai_manager.settings.get("image_processing_enabled", True),
        "text_processing": ai_manager.settings.get("text_processing_enabled", True),
        "model": ai_manager.settings.get("model", "gpt-3.5-turbo"),
        "temperature": ai_manager.settings.get("temperature", 0.7),
        "max_tokens": ai_manager.settings.get("max_tokens", 150)
    }

def activate_ai(ai_manager):
    """فعال کردن هوش مصنوعی"""
    ai_manager.enabled = True
    ai_manager.settings["enabled"] = True
    ai_manager._save_settings()
    return "✅ هوش مصنوعی فعال شد."

def deactivate_ai(ai_manager):
    """غیرفعال کردن هوش مصنوعی"""
    ai_manager.enabled = False
    ai_manager.settings["enabled"] = False
    ai_manager._save_settings()
    return "❌ هوش مصنوعی غیرفعال شد."

def toggle_ai(ai_manager):
    """تغییر وضعیت هوش مصنوعی"""
    if ai_manager.enabled:
        return deactivate_ai(ai_manager)
    else:
        return activate_ai(ai_manager)