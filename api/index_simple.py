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
bot_instance = None
dp_instance = None

async def init_bot():
    """Initialize the bot safely"""
    global bot_instance, dp_instance
    try:
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

def handler(event, context):
    """Standard Vercel serverless function handler"""
    try:
        # Extract method and path from event
        method = event.get('method', 'GET')
        path = event.get('path', '')
        
        logger.info(f"Received {method} request to {path}")
        
        # Handle different endpoints
        if method == 'POST':
            if path.endswith('/webhook') or path.endswith('/api/webhook'):
                # Handle webhook
                logger.info("Processing webhook request")
                
                # Get body from event
                body = event.get('body', '')
                update_data = {}
                
                # Parse JSON body
                if body:
                    try:
                        if isinstance(body, str):
                            update_data = json.loads(body)
                        else:
                            update_data = body
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in webhook body")
                
                # Process the update asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(process_update(update_data))
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
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"error": "Not found"})
                }
        
        elif method == 'GET':
            if path.endswith('/health') or path.endswith('/api/health'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "status": "healthy", 
                        "bot_initialized": bot_instance is not None
                    })
                }
            elif path.endswith('/api') or path == '/':
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
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"error": "Not found"})
                }
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"error": "Method not allowed"})
            }
            
    except Exception as e:
        logger.error(f"Error in handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": "Internal server error"})
        }

# Initialize bot on module load
async def startup():
    """Initialize bot on startup"""
    logger.info("Initializing sticker bot...")
    await init_bot()

# Export the handler for Vercel
__all__ = ['handler']

# Auto-initialize if running in production
if os.getenv('VERCEL_ENV') is not None:
    # Run startup initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(startup())
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
    finally:
        loop.close()