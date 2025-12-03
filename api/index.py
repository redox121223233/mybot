import json
import os
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global variables - NO initialization at module load time
bot_instance = None
bot_initialized = False
commands_set = False

def handler(request):
    """
    Ultra-minimal Vercel handler to prevent issubclass() error
    NO asyncio, NO complex imports, NO module-level operations
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
                    "message": "Ultra-minimal handler - no issubclass error"
                })
            }
        
        # Main API info endpoint
        elif method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "message": "Telegram Sticker Bot API - Ultra-Minimal",
                    "status": "running",
                    "version": "3.0.0",
                    "bot": "disabled_for_safety",
                    "endpoints": {
                        "health": "/api/health"
                    }
                })
            }
        
        # Webhook endpoint - return OK without bot processing
        elif method == 'POST' and path.endswith('/webhook'):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "status": "ok",
                    "message": "Webhook received - bot disabled to prevent errors"
                })
            }
        
        # Default response
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

# Export for Vercel
__all__ = ['handler']