#!/usr/bin/env python3
"""
Sticker Pack Handler for Telegram Bot
Handles creating and managing sticker packs
"""

import os
import logging
import tempfile
import io
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import CallbackContext
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class StickerPackHandler:
    """Handle sticker pack creation and management"""
    
    def __init__(self):
        # Dictionary to store user sticker packs
        # Format: {user_id: {pack_name: {"name": str, "title": str, "stickers": List[Dict]}}}
        self.user_sticker_packs: Dict[int, Dict[str, Dict]] = {}
        # Current pack being created by each user
        self.user_current_pack: Dict[int, Optional[str]] = {}
        
    async def create_new_sticker_pack(self, user_id: int, pack_name: str, pack_title: str) -> Dict:
        """Create a new sticker pack for user"""
        try:
            # Initialize user data if not exists
            if user_id not in self.user_sticker_packs:
                self.user_sticker_packs[user_id] = {}
                
            # Check if pack already exists
            if pack_name in self.user_sticker_packs[user_id]:
                return {
                    "success": False,
                    "message": f"❌ پک استیکر '{pack_name}' از قبل وجود دارد! لطفاً نام دیگری انتخاب کنید."
                }
            
            # Create new pack
            self.user_sticker_packs[user_id][pack_name] = {
                "name": pack_name,
                "title": pack_title,
                "stickers": [],
                "created_at": None,
                "telegram_pack_name": None  # Will be set when pack is created on Telegram
            }
            
            # Set as current pack
            self.user_current_pack[user_id] = pack_name
            
            return {
                "success": True,
                "message": f"✅ پک استیکر جدید '{pack_title}' با موفقیت ساخته شد!\n\nحالا می‌توانید استیکرهای خود را ارسال کنید تا به این پک اضافه شوند."
            }
            
        except Exception as e:
            logger.error(f"Error creating sticker pack: {e}")
            return {
                "success": False,
                "message": "❌ خطا در ساخت پک استیکر! لطفاً دوباره تلاش کنید."
            }
    
    async def add_sticker_to_pack(self, user_id: int, sticker_data: Dict) -> Dict:
        """Add a sticker to user's current pack"""
        try:
            # Check if user has a current pack
            current_pack = self.user_current_pack.get(user_id)
            if not current_pack:
                return {
                    "success": False,
                    "message": "❌ شما هیچ پک استیکری فعال ندارید! ابتدا یک پک جدید بسازید."
                }
            
            # Check if pack exists
            if user_id not in self.user_sticker_packs or current_pack not in self.user_sticker_packs[user_id]:
                return {
                    "success": False,
                    "message": "❌ پک استیکر پیدا نشد! لطفاً یک پک جدید بسازید."
                }
            
            # Add sticker to pack
            pack = self.user_sticker_packs[user_id][current_pack]
            sticker_info = {
                "file_id": sticker_data.get("file_id"),
                "emoji": sticker_data.get("emoji", "😊"),
                "added_at": None
            }
            
            pack["stickers"].append(sticker_info)
            
            return {
                "success": True,
                "message": f"✅ استیکر با موفقیت به پک '{pack['title']}' اضافه شد!\n\nتعداد استیکرها: {len(pack['stickers'])} 📊"
            }
            
        except Exception as e:
            logger.error(f"Error adding sticker to pack: {e}")
            return {
                "success": False,
                "message": "❌ خطا در اضافه کردن استیکر به پک! لطفاً دوباره تلاش کنید."
            }
    
    async def get_user_packs(self, user_id: int) -> List[Dict]:
        """Get all sticker packs for a user"""
        if user_id not in self.user_sticker_packs:
            return []
        
        packs = []
        for pack_name, pack_data in self.user_sticker_packs[user_id].items():
            packs.append({
                "name": pack_data["name"],
                "title": pack_data["title"],
                "sticker_count": len(pack_data["stickers"]),
                "is_current": pack_name == self.user_current_pack.get(user_id)
            })
        
        return packs
    
    async def set_current_pack(self, user_id: int, pack_name: str) -> Dict:
        """Set a pack as the current active pack for user"""
        try:
            if user_id not in self.user_sticker_packs or pack_name not in self.user_sticker_packs[user_id]:
                return {
                    "success": False,
                    "message": "❌ پک استیکر پیدا نشد!"
                }
            
            self.user_current_pack[user_id] = pack_name
            pack = self.user_sticker_packs[user_id][pack_name]
            
            return {
                "success": True,
                "message": f"✅ پک '{pack['title']}' به عنوان پک فعلی انتخاب شد.\n\nاکنون می‌توانید استیکرها را به این پک اضافه کنید."
            }
            
        except Exception as e:
            logger.error(f"Error setting current pack: {e}")
            return {
                "success": False,
                "message": "❌ خطا در انتخاب پک! لطفاً دوباره تلاش کنید."
            }
    
    def get_pack_management_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Get keyboard for pack management"""
        keyboard = []
        
        # Add current pack info if exists
        current_pack = self.user_current_pack.get(user_id)
        if current_pack and user_id in self.user_sticker_packs:
            pack_info = self.user_sticker_packs[user_id][current_pack]
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 پک فعلی: {pack_info['title']} ({len(pack_info['stickers'])} استیکر)", 
                    callback_data="pack_info"
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ ساخت پک جدید", callback_data="create_new_pack")],
            [InlineKeyboardButton("📋 مشاهده پک‌ها", callback_data="list_packs")],
            [InlineKeyboardButton("🔧 انتخاب پک فعلی", callback_data="select_current_pack")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_packs_list_keyboard(self, user_id: int) -> Optional[InlineKeyboardMarkup]:
        """Get keyboard with user's sticker packs"""
        if user_id not in self.user_sticker_packs:
            return None
        
        packs = self.user_sticker_packs[user_id]
        if not packs:
            return None
        
        keyboard = []
        for pack_name, pack_data in packs.items():
            is_current = pack_name == self.user_current_pack.get(user_id)
            status = " ✅" if is_current else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {pack_data['title']} ({len(pack_data['stickers'])}){status}", 
                    callback_data=f"select_pack_{pack_name}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="sticker_pack_menu")])
        return InlineKeyboardMarkup(keyboard)

# Global instance
sticker_pack_handler = StickerPackHandler()