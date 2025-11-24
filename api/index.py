"""
Vercel serverless function for Telegram bot webhook
"""
import asyncio
import os
import json
from typing import Dict, Any
import sys

# Add parent directory to path to import bot.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import main, router, BOT_TOKEN

# Global variables for bot and dispatcher
bot = None
dp = None

async def initialize_bot():
    """Initialize bot and dispatcher"""
    global bot, dp
    if bot is None or dp is None:
        try:
            from aiogram import Bot, Dispatcher, F
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            
            # Create bot instance
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            
            # Create dispatcher
            dp = Dispatcher()
            
            # Include router from bot.py
            dp.include_router(router)
            
            # Get bot info
            bot_info = await bot.get_me()
            print(f"Bot initialized: @{bot_info.username}")
            
            # Set webhook
            webhook_url = f"https://{os.environ.get('VERCEL_URL', 'localhost:3000')}/api/webhook"
            await bot.set_webhook(webhook_url)
            print(f"Webhook set to: {webhook_url}")
            
        except Exception as e:
            print(f"Error during initialization: {e}")
            raise

async def handler(request):
    """Main handler for Vercel serverless functions"""
    global bot, dp
    
    try:
        # Parse request
        method = request.method
        url_path = request.url.path if hasattr(request, 'url') else request.path
        
        # Initialize bot if not done yet
        await initialize_bot()
        
        if method == "POST" and url_path == "/api/webhook":
            # Handle webhook
            try:
                # Get update data
                if hasattr(request, 'json'):
                    update_data = await request.json()
                else:
                    body = request.body.read().decode('utf-8')
                    update_data = json.loads(body)
                
                # Create update object and feed to dispatcher
                from aiogram.types import Update
                update = Update.model_validate(update_data)
                
                # Process update
                await dp.feed_update(bot=bot, update=update)
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({"status": "ok"}),
                    "headers": {"Content-Type": "application/json"}
                }
                
            except Exception as e:
                print(f"Error processing webhook: {e}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": str(e)}),
                    "headers": {"Content-Type": "application/json"}
                }
        
        elif method == "GET" and url_path == "/api/health":
            # Health check
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "healthy", 
                    "bot_initialized": bot is not None
                }),
                "headers": {"Content-Type": "application/json"}
            }
        
        elif method == "GET" and url_path == "/":
            # Root endpoint
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Telegram Bot API Server", 
                    "status": "running"
                }),
                "headers": {"Content-Type": "application/json"}
            }
        
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Not found"}),
                "headers": {"Content-Type": "application/json"}
            }
            
    except Exception as e:
        print(f"Handler error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
            "headers": {"Content-Type": "application/json"}
        }

# Vercel serverless function entry point
async def main_handler(request):
    """Main entry point for Vercel"""
    return await handler(request)

# Export the handler
def handler_v2(event):
    """Vercel V2 function handler"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Create mock request object from event
        class MockRequest:
            def __init__(self, event):
                self.method = event.get('httpMethod', 'GET')
                self.path = event.get('path', '/')
                self.body = event.get('body', '')
                self.headers = event.get('headers', {})
                
                # Parse URL
                if 'pathParameters' in event:
                    self.path = '/' + event['pathParameters'].get('proxy', '')
                
                self.url = MockURL(self.path)
            
            async def json(self):
                if self.body:
                    return json.loads(self.body)
                return {}
        
        class MockURL:
            def __init__(self, path):
                self.path = path
        
        # Process the request
        mock_request = MockRequest(event)
        result = loop.run_until_complete(handler(mock_request))
        
        # Convert to Vercel response format
        return {
            'statusCode': result['statusCode'],
            'body': result['body'],
            'headers': result.get('headers', {})
        }
        
    finally:
        loop.close()

# For Vercel compatibility
handler = handler_v2