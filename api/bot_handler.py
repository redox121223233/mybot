#!/usr/bin/env python3
"""
Enhanced bot handler for Vercel with Telegram functionality
Minimal dependencies, proper error handling
"""

import os
import json
import sys
import logging
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBotHandler:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = 6053579919
        self.support_username = "@onedaytoalive"
        
        if not self.bot_token:
            logger.error("❌ No Telegram token found in environment!")
            raise ValueError("BOT_TOKEN environment variable is required")
        
        logger.info(f"✅ Bot handler initialized")
    
    async def process_update(self, update_data):
        """Process Telegram update"""
        try:
            logger.info(f"📨 Processing update: {update_data.get('update_id', 'unknown')}")
            
            # Extract message info
            message = update_data.get('message', {})
            callback_query = update_data.get('callback_query', {})
            
            if message:
                await self.handle_message(message)
            elif callback_query:
                await self.handle_callback(callback_query)
            else:
                logger.info("📋 Received non-message update")
            
            return {"status": "success", "processed": True}
            
        except Exception as e:
            logger.error(f"❌ Error processing update: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def handle_message(self, message):
        """Handle incoming messages"""
        user_id = message.get('from', {}).get('id')
        text = message.get('text', '')
        
        if not user_id:
            return
        
        logger.info(f"💬 Message from {user_id}: {text[:50]}...")
        
        # Simple command handling
        if text == '/start':
            await self.send_start_message(user_id)
        elif text == '/help':
            await self.send_help_message(user_id)
        elif text.startswith('/sticker'):
            await self.handle_sticker_command(user_id, text)
        else:
            logger.info(f"📝 Text message received: {text}")
    
    async def handle_callback(self, callback_query):
        """Handle callback queries"""
        user_id = callback_query.get('from', {}).get('id')
        data = callback_query.get('data', '')
        
        if not user_id or not data:
            return
        
        logger.info(f"🎯 Callback from {user_id}: {data}")
        
        # Handle sticker-related callbacks
        if data == 'sticker_creator':
            await self.send_sticker_menu(user_id)
        elif data.startswith('sticker:'):
            await self.handle_sticker_callback(user_id, data)
        else:
            logger.info(f"🔄 Unknown callback: {data}")
    
    async def send_start_message(self, user_id):
        """Send start message"""
        message = """
🎮 **به ربات بازی و استیکر ساز خوش آمدید!** 🎨

من یک ربات ساده با قابلیت‌های زیر هستم:

🎮 **بازی‌ها:**
• 🎯 حدس عدد
• ✂️ سنگ کاغذ قیچی
• 📝 بازی کلمات
• 🧠 بازی حافظه

🎨 **استیکر ساز:**
• 📸 ساخت استیکر متنی
• 🎨 انتخاب رنگ و فونت
• ⚡ ساخت سریع استیکر

برای شروع، دستور /help را ارسال کنید.
        """
        
        # Send message (simplified - would need proper Telegram API call)
        logger.info(f"📤 Sending start message to {user_id}")
    
    async def send_help_message(self, user_id):
        """Send help message"""
        help_text = """
📚 **راهنمای کامل ربات:**

🎯 **حدس عدد:**
• /guess - شروع بازی حدس عدد

✂️ **سنگ کاغذ قیچی:**
• /rps - شروع بازی سنگ کاغذ قیچی

🎨 **استیکر ساز:**
• /sticker <متن> - ساخت استیکر متنی
• /customsticker - ساخت استیکر سفارشی

🎲 **بازی تصادفی:**
• /random - بازی تصادفی

برای هر دستور می‌توانید از منوی هم استفاده کنید!
        """
        
        logger.info(f"📖 Sending help message to {user_id}")
    
    async def send_sticker_menu(self, user_id):
        """Send sticker creation menu"""
        menu_text = "🎨 **استیکر ساز**\n\nلطفاً نوع استیکر را انتخاب کنید:"
        
        logger.info(f"🎨 Sending sticker menu to {user_id}")
    
    async def handle_sticker_command(self, user_id, text):
        """Handle sticker creation command"""
        sticker_text = text.replace('/sticker', '').strip()
        
        if not sticker_text:
            await self.send_message(user_id, "لطفاً متن استیکر را وارد کنید: /sticker <متن>")
            return
        
        logger.info(f"🎨 Creating sticker for {user_id}: {sticker_text}")
        
        # Here you would integrate with the actual sticker creation logic
        # For now, we'll just log it
        success = await self.create_simple_sticker(sticker_text)
        
        if success:
            await self.send_message(user_id, f"✅ استیکر «{sticker_text}» با موفقیت ساخته شد!")
        else:
            await self.send_message(user_id, "❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.")
    
    async def handle_sticker_callback(self, user_id, data):
        """Handle sticker-related callbacks"""
        logger.info(f"🎯 Handling sticker callback for {user_id}: {data}")
        
        # Process sticker creation workflow
        if data == 'sticker:simple':
            await self.send_message(user_id, "لطفاً متن استیکر ساده را ارسال کنید:")
        elif data == 'sticker:advanced':
            await self.send_message(user_id, "در حال ساخت منوی استیکر پیشرفته...")
    
    async def create_simple_sticker(self, text):
        """Create a simple sticker (mock implementation)"""
        try:
            logger.info(f"🎨 Creating sticker with text: {text}")
            
            # Mock sticker creation - in real implementation, this would:
            # 1. Create an image with PIL
            # 2. Add text with proper font handling
            # 3. Convert to WebP format
            # 4. Upload to Telegram
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating sticker: {e}")
            return False
    
    async def send_message(self, user_id, text):
        """Send message to user (mock implementation)"""
        logger.info(f"📤 Sending message to {user_id}: {text[:100]}...")
        # In real implementation, this would use the Telegram Bot API

# Create global instance
bot_handler = None

def get_bot_handler():
    """Get or create bot handler instance"""
    global bot_handler
    if bot_handler is None:
        bot_handler = TelegramBotHandler()
    return bot_handler

async def process_telegram_update(update_data):
    """Process Telegram update asynchronously"""
    handler = get_bot_handler()
    return await handler.process_update(update_data)