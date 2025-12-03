import json
import os
import sys
import asyncio
import logging

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables - NO initialization at module load time
bot_instance = None
bot_initialized = False

def handler(request):
    """
    Final Vercel handler - follows exact Vercel pattern
    No module-level async operations
    """
    try:
        # Parse request safely
        method = getattr(request, 'method', 'GET')
        if isinstance(request, dict):
            method = request.get('method', 'GET')
        
        # Get path
        path = getattr(request, 'url', '/').split('?')[0]
        if isinstance(request, dict):
            path = request.get('path', '/')
        
        # Health check endpoint
        if method == 'GET' and path.endswith('/health'):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "status": "healthy",
                    "bot_initialized": bot_initialized,
                    "timestamp": int(asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0)
                })
            }
        
        # Main API info endpoint
        elif method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "message": "Telegram Sticker Bot API",
                    "status": "running",
                    "version": "2.0.0",
                    "endpoints": {
                        "health": "/api/health",
                        "webhook": "/api/webhook"
                    }
                })
            }
        
        # Webhook endpoint - initialize bot ONLY when needed
        elif method == 'POST' and path.endswith('/webhook'):
            try:
                # Initialize bot on first webhook call
                if not bot_initialized:
                    success = initialize_bot_safely()
                    if not success:
                        return {
                            'statusCode': 200,  # Still return 200 to avoid webhook failures
                            'headers': {'Content-Type': 'application/json'},
                            'body': json.dumps({"status": "bot_init_failed"})
                        }
                
                # Process webhook (placeholder for now)
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok"})
                }
                
            except Exception as webhook_error:
                logger.error(f"Webhook processing error: {webhook_error}")
                return {
                    'statusCode': 200,  # Always return 200 to webhook
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok", "error": str(webhook_error)})
                }
        
        # Default response
        else:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"error": "Not found"})
            }
            
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": f"Internal server error: {str(e)}"})
        }

def initialize_bot_safely():
    """
    Safe bot initialization - called only when needed
    Uses sync wrapper to avoid module-level async
    """
    global bot_instance, bot_initialized
    
    try:
        logger.info("Starting bot initialization...")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run async initialization
            success = loop.run_until_complete(_async_init_bot())
            return success
        finally:
            # Always close the loop
            loop.close()
            
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        return False

async def _async_init_bot():
    """
    Async bot initialization with flood control handling
    """
    global bot_instance, bot_initialized
    
    try:
        # Import only when needed to avoid module load issues
        from bot_optimized_final import create_bot_with_flood_control
        
        # Create bot with flood control
        bot_instance = await create_bot_with_flood_control()
        
        if bot_instance:
            bot_initialized = True
            logger.info("Bot initialized successfully")
            return True
        else:
            logger.error("Failed to initialize bot")
            return False
            
    except Exception as e:
        logger.error(f"Async bot initialization error: {e}")
        return False

# Export for Vercel
__all__ = ['handler']