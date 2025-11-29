"""
Script to set webhook for the sticker bot
"""
import asyncio
import os
from bot_optimized import create_bot

async def set_webhook():
    """Set webhook for the bot"""
    # Get webhook URL
    webhook_url = os.getenv('WEBHOOK_URL') or input("Enter your Vercel URL (e.g., your-app.vercel.app): ")
    if not webhook_url.startswith('https://'):
        webhook_url = f"https://{webhook_url}"
    
    if not webhook_url.endswith('/api/webhook'):
        webhook_url = f"{webhook_url}/api/webhook"
    
    try:
        # Create bot instance
        success = await create_bot()
        if not success:
            print("❌ Failed to initialize bot")
            return
        
        from bot_optimized import bot
        
        # Remove existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("🗑️ Removed existing webhook")
        
        # Set new webhook
        await bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook set successfully to: {webhook_url}")
        
        # Test webhook info
        webhook_info = await bot.get_webhook_info()
        print(f"📡 Webhook URL: {webhook_info.url}")
        print(f"📡 Pending updates: {webhook_info.pending_update_count}")
        print(f"📡 Last error: {webhook_info.last_error_message}")
        
        # Test bot info
        bot_info = await bot.get_me()
        print(f"🤖 Bot info: @{bot_info.username} ({bot_info.first_name})")
        
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")

if __name__ == "__main__":
    print("🔧 Setting webhook for Sticker Bot...")
    asyncio.run(set_webhook())