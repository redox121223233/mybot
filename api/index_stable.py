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
commands_set = False

def handler(request):
    """
    Stable Vercel handler with flood control protection
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
                    "commands_set": commands_set,
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
                    "version": "2.1.0",
                    "features": {
                        "flood_control": "enabled",
                        "on_demand_init": "enabled",
                        "delayed_commands": "enabled"
                    },
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
                
                # Process webhook (simplified for now)
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
    Safe bot initialization with flood control protection
    """
    global bot_instance, bot_initialized, commands_set
    
    try:
        logger.info("Starting safe bot initialization...")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run async initialization
            success = loop.run_until_complete(_async_init_bot_with_flood_control())
            return success
        finally:
            # Always close the loop
            loop.close()
            
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        return False

async def _async_init_bot_with_flood_control():
    """
    Async bot initialization with complete flood control protection
    """
    global bot_instance, bot_initialized, commands_set
    
    try:
        # Import only when needed to avoid module load issues
        from bot_no_flood import create_bot_without_commands, set_bot_commands_delayed
        
        # Create bot WITHOUT setting commands (prevents flood control)
        bot_instance = await create_bot_without_commands()
        
        if bot_instance:
            bot_initialized = True
            logger.info("Bot initialized successfully (no commands set)")
            
            # Start background task to set commands after delay
            asyncio.create_task(_set_commands_background())
            
            return True
        else:
            logger.error("Failed to initialize bot")
            return False
            
    except Exception as e:
        logger.error(f"Async bot initialization error: {e}")
        return False

async def _set_commands_background():
    """
    Background task to set bot commands after initialization
    This prevents flood control by separating initialization and command setup
    """
    global commands_set
    
    try:
        # Wait a bit to ensure bot is fully initialized
        await asyncio.sleep(5)
        
        # Import the delayed command setup function
        from bot_no_flood import set_bot_commands_delayed
        
        # Set commands with retry mechanism
        success = await set_bot_commands_delayed()
        commands_set = success
        
        if success:
            logger.info("Bot commands set successfully in background")
        else:
            logger.warning("Failed to set bot commands in background (will retry later)")
            
    except Exception as e:
        logger.error(f"Background command setup error: {e}")

# Export for Vercel
__all__ = ['handler']