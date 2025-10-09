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

async def reset_webhook_clean():
    """Reset the webhook cleanly"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return False
    
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ WEBHOOK_URL not found in environment")
        return False
    
    try:
        bot = Bot(bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Delete existing webhook
        print("Deleting existing webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Set new webhook
        print(f"Setting new webhook to: {webhook_url}")
        await bot.set_webhook(url=webhook_url)
        
        # Check webhook info
        webhook_info = await bot.get_webhook_info()
        print(f"Webhook URL: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        
        if webhook_info.last_error_date:
            print(f"Last error: {webhook_info.last_error_message}")
        else:
            print("✅ No errors in webhook")
        
        await bot.session.close()
        
        if webhook_info.url == webhook_url:
            print("✅ Webhook reset successfully!")
            return True
        else:
            print("❌ Webhook reset failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error resetting webhook: {e}")
        return False

if __name__ == "__main__":
    print("Resetting webhook...")
    asyncio.run(reset_webhook_clean())