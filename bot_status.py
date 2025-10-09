import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def check_bot_status():
    """Check the current status of the bot"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return
    
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ WEBHOOK_URL not found in environment")
        return
    
    try:
        bot = Bot(bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Get bot info
        bot_info = await bot.get_me()
        print(f"🤖 Bot Username: @{bot_info.username}")
        print(f"🤖 Bot ID: {bot_info.id}")
        print(f"🤖 Bot First Name: {bot_info.first_name}")
        
        # Get webhook info
        webhook_info = await bot.get_webhook_info()
        print(f"\n🔗 Webhook URL: {webhook_info.url}")
        print(f"📋 Pending Updates: {webhook_info.pending_update_count}")
        if webhook_info.last_error_date:
            print(f"❌ Last Error: {webhook_info.last_error_message}")
        
        if webhook_info.url == webhook_url:
            print("✅ Webhook URL is correctly set")
        else:
            print("⚠️  Webhook URL mismatch")
            
        await bot.session.close()
        
    except Exception as e:
        print(f"❌ Error checking bot status: {e}")

if __name__ == "__main__":
    asyncio.run(check_bot_status())