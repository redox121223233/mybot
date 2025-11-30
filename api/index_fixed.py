import json
import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global variables
bot_app = None
bot_instance = None
dp_instance = None

async def init_bot():
    """Initialize the bot safely"""
    global bot_instance, dp_instance
    try:
        # Import the fixed bot module
        from bot_optimized_fixed import create_bot
        success = await create_bot()
        if success:
            from bot_optimized_fixed import bot, dp
            bot_instance = bot
            dp_instance = dp
            logger.info("Sticker bot initialized successfully")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to initialize sticker bot: {e}")
        import traceback
        traceback.print_exc()
        return False

async def process_update(update):
    """Process Telegram update"""
    try:
        # Initialize bot if not already initialized
        if bot_instance is None or dp_instance is None:
            await init_bot()
        
        if bot_instance is not None and dp_instance is not None:
            # Feed the update to dispatcher
            await dp_instance.feed_update(bot_instance, update)
        else:
            logger.error("Bot or dispatcher not initialized")
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        import traceback
        traceback.print_exc()

class Request:
    """Simple request class for Vercel compatibility"""
    def __init__(self, method, url, body=None):
        self.method = method
        self.url = url
        self.body = body

def handler(request_obj):
    """Vercel serverless function handler"""
    try:
        # Handle different request types
        method = getattr(request_obj, 'method', 'GET')
        url = getattr(request_obj, 'url', '/')
        
        # Parse request body for POST requests
        if hasattr(request_obj, 'body'):
            body_str = request_obj.body.decode('utf-8') if isinstance(request_obj.body, bytes) else request_obj.body
        else:
            body_str = "{}"
        
        # Parse JSON body
        try:
            body = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            body = {}
        
        # Handle different endpoints
        if method == 'POST':
            if url.endswith('/webhook') or url.endswith('/api/webhook'):
                # Handle webhook
                logger.info("Received webhook request")
                
                # Process the update asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(process_update(body))
                finally:
                    loop.close()
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok"})
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({"error": "Not found"})
                }
        
        elif method == 'GET':
            if url.endswith('/health') or url.endswith('/api/health'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "status": "healthy", 
                        "bot_initialized": bot_instance is not None
                    })
                }
            elif url.endswith('/api') or url.endswith('/'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "message": "Telegram Sticker Bot API is running",
                        "endpoints": {
                            "webhook": "/api/webhook",
                            "health": "/api/health"
                        },
                        "features": [
                            "Text stickers",
                            "Image stickers", 
                            "Inline keyboard menu",
                            "Daily limits",
                            "Channel membership check"
                        ]
                    })
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({"error": "Not found"})
                }
        else:
            return {
                'statusCode': 405,
                'body': json.dumps({"error": "Method not allowed"})
            }
            
    except Exception as e:
        logger.error(f"Error in handler: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "Internal server error"})
        }

# For Vercel compatibility
def main(request):
    """Main entry point for Vercel"""
    return handler(request)

# Initialize bot on module load
async def startup():
    """Initialize bot on startup"""
    logger.info("Initializing sticker bot...")
    await init_bot()

# Export the handler
__all__ = ['handler', 'main']

# Auto-initialize if running in production
if os.getenv('VERCEL_ENV') is not None:
    # Run startup initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(startup())
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()