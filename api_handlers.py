import requests
import json
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger("api_handlers")

class TelegramAPI:
    """کلاس مدیریت API تلگرام"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}/"
    
    def send_message(self, chat_id: Union[int, str], text: str, reply_markup: Optional[Dict] = None, 
                    parse_mode: str = "HTML", reply_to_message_id: Optional[int] = None) -> Dict:
        """ارسال پیام به کاربر"""
        url = f"{self.api_url}sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
            
        try:
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"ok": False, "description": str(e)}
    
    def edit_message_text(self, chat_id: Union[int, str], message_id: int, text: str, 
                         reply_markup: Optional[Dict] = None, parse_mode: str = "HTML") -> Dict:
        """ویرایش متن پیام"""
        url = f"{self.api_url}editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
            
        try:
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return {"ok": False, "description": str(e)}
    
    def send_photo(self, chat_id: Union[int, str], photo: str, caption: Optional[str] = None,
                  reply_markup: Optional[Dict] = None, parse_mode: str = "HTML") -> Dict:
        """ارسال تصویر به کاربر"""
        url = f"{self.api_url}sendPhoto"
        data = {
            "chat_id": chat_id,
            "parse_mode": parse_mode
        }
        
        if caption:
            data["caption"] = caption
            
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        files = None
        if photo.startswith("http"):
            data["photo"] = photo
        else:
            try:
                files = {"photo": open(photo, "rb")}
            except Exception as e:
                logger.error(f"Error opening photo file: {e}")
                return {"ok": False, "description": str(e)}
        
        try:
            if files:
                response = requests.post(url, data=data, files=files)
            else:
                response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return {"ok": False, "description": str(e)}
        finally:
            if files and "photo" in files:
                files["photo"].close()
    
    def send_sticker(self, chat_id: Union[int, str], sticker: str, 
                    reply_markup: Optional[Dict] = None) -> Dict:
        """ارسال استیکر به کاربر"""
        url = f"{self.api_url}sendSticker"
        data = {
            "chat_id": chat_id
        }
        
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        files = None
        if sticker.startswith("http"):
            data["sticker"] = sticker
        else:
            try:
                files = {"sticker": open(sticker, "rb")}
            except Exception as e:
                logger.error(f"Error opening sticker file: {e}")
                return {"ok": False, "description": str(e)}
        
        try:
            if files:
                response = requests.post(url, data=data, files=files)
            else:
                response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending sticker: {e}")
            return {"ok": False, "description": str(e)}
        finally:
            if files and "sticker" in files:
                files["sticker"].close()
    
    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None, 
                             show_alert: bool = False) -> Dict:
        """پاسخ به callback query"""
        url = f"{self.api_url}answerCallbackQuery"
        data = {
            "callback_query_id": callback_query_id
        }
        
        if text:
            data["text"] = text
            
        if show_alert:
            data["show_alert"] = True
            
        try:
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return {"ok": False, "description": str(e)}
    
    def create_sticker_set(self, user_id: int, name: str, title: str, 
                          png_sticker: str, emojis: str) -> Dict:
        """ایجاد پک استیکر جدید"""
        url = f"{self.api_url}createNewStickerSet"
        data = {
            "user_id": user_id,
            "name": name,
            "title": title,
            "emojis": emojis
        }
        
        files = None
        if png_sticker.startswith("http"):
            data["png_sticker"] = png_sticker
        else:
            try:
                files = {"png_sticker": open(png_sticker, "rb")}
            except Exception as e:
                logger.error(f"Error opening sticker file: {e}")
                return {"ok": False, "description": str(e)}
        
        try:
            if files:
                response = requests.post(url, data=data, files=files)
            else:
                response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error creating sticker set: {e}")
            return {"ok": False, "description": str(e)}
        finally:
            if files and "png_sticker" in files:
                files["png_sticker"].close()
    
    def add_sticker_to_set(self, user_id: int, name: str, png_sticker: str, emojis: str) -> Dict:
        """افزودن استیکر به پک موجود"""
        url = f"{self.api_url}addStickerToSet"
        data = {
            "user_id": user_id,
            "name": name,
            "emojis": emojis
        }
        
        files = None
        if png_sticker.startswith("http"):
            data["png_sticker"] = png_sticker
        else:
            try:
                files = {"png_sticker": open(png_sticker, "rb")}
            except Exception as e:
                logger.error(f"Error opening sticker file: {e}")
                return {"ok": False, "description": str(e)}
        
        try:
            if files:
                response = requests.post(url, data=data, files=files)
            else:
                response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error adding sticker to set: {e}")
            return {"ok": False, "description": str(e)}
        finally:
            if files and "png_sticker" in files:
                files["png_sticker"].close()
    
    def set_webhook(self, url: str, secret_token: Optional[str] = None) -> Dict:
        """تنظیم webhook برای دریافت آپدیت‌ها"""
        api_url = f"{self.api_url}setWebhook"
        data = {
            "url": url
        }
        
        if secret_token:
            data["secret_token"] = secret_token
            
        try:
            response = requests.post(api_url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return {"ok": False, "description": str(e)}
    
    def delete_webhook(self) -> Dict:
        """حذف webhook"""
        url = f"{self.api_url}deleteWebhook"
        
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return {"ok": False, "description": str(e)}