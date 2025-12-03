import json
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global bot instance - don't initialize at module load
bot_app = None

def handler(request):
    """Proper Vercel handler following exact Vercel pattern"""
    try:
        # Handle different request formats
        if hasattr(request, 'method'):
            # Standard request object
            method = request.method
            path = getattr(request, 'url', '/').split('?')[0]
        elif isinstance(request, dict):
            # Vercel event format
            method = request.get('method', 'GET')
            path = request.get('path', '/')
        else:
            # Fallback
            method = 'GET'
            path = '/'
        
        # Health check
        if method == 'GET' and (path.endswith('/health') or path.endswith('/api/health')):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "status": "healthy",
                    "bot_loaded": bot_app is not None
                })
            }
        
        # Main API endpoint
        elif method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "message": "Telegram Sticker Bot API",
                    "status": "running",
                    "endpoints": {
                        "health": "/api/health",
                        "webhook": "/api/webhook"
                    }
                })
            }
        
        # Webhook endpoint - initialize bot only when needed
        elif method == 'POST' and (path.endswith('/webhook') or path.endswith('/api/webhook')):
            try:
                # Initialize bot on first webhook
                if bot_app is None:
                    initialize_bot()
                
                # Process webhook (simplified for now)
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok"})
                }
            except Exception as webhook_error:
                return {
                    'statusCode': 200,  # Still return 200 to avoid webhook failures
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok", "error": str(webhook_error)})
                }
        
        else:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"error": "Not found"})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": f"Internal server error: {str(e)}"})
        }

def initialize_bot():
    """Initialize bot - called only when needed"""
    global bot_app
    try:
        # Import bot modules only when needed
        import asyncio
        
        async def _init():
            from bot_optimized_fixed import create_bot
            await create_bot()
            return True
        
        # Run initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_init())
            bot_app = "initialized"
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Bot initialization error: {e}")
        # Don't set bot_app if initialization failed

# Export for Vercel
__all__ = ['handler']