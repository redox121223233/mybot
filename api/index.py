import json
import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global bot instance
bot_initialized = False

async def init_bot_once():
    """Initialize bot only once"""
    global bot_initialized
    if not bot_initialized:
        try:
            from bot_optimized_fixed import create_bot
            await create_bot()
            bot_initialized = True
            logger.info("Bot initialized successfully")
        except Exception as e:
            error_str = str(e).lower()
            if "flood control" in error_str or "too many requests" in error_str:
                logger.info("Bot initialization hit flood control - will work normally")
                bot_initialized = True  # Still mark as initialized since bot works
            else:
                logger.error(f"Bot initialization failed: {e}")
    return bot_initialized

async def handle_webhook(body):
    """Handle webhook updates"""
    try:
        if not bot_initialized:
            await init_bot_once()
        
        if bot_initialized:
            from bot_optimized_fixed import bot, dp
            update_data = json.loads(body) if isinstance(body, str) else body
            await dp.feed_update(bot, update_data)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")

def handler(event, context):
    """Vercel handler with bot functionality"""
    try:
        method = event.get('method', 'GET')
        path = event.get('path', '')
        
        if method == 'GET':
            if path.endswith('/health') or path.endswith('/api/health'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "status": "healthy", 
                        "bot_initialized": bot_initialized
                    })
                }
            else:
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "message": "Telegram Sticker Bot API",
                        "endpoints": {
                            "health": "/api/health",
                            "webhook": "/api/webhook"
                        }
                    })
                }
        
        elif method == 'POST':
            if path.endswith('/webhook') or path.endswith('/api/webhook'):
                body = event.get('body', '')
                
                # Process webhook asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(handle_webhook(body))
                finally:
                    loop.close()
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok"})
                }
        
        return {'statusCode': 404, 'body': 'Not found'}
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {'statusCode': 500, 'body': f'Internal error: {str(e)}'}

# Auto-initialize bot on load
if os.getenv('VERCEL_ENV'):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_bot_once())
    except Exception as e:
        logger.error(f"Startup error: {e}")
    finally:
        loop.close()

# Export for Vercel
__all__ = ['handler']