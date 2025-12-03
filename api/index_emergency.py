import json

def handler(request):
    """
    Emergency ultra-minimal handler to stop issubclass() error
    NO bot initialization, NO async operations, NO complex imports
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
        
        # Health check - only this endpoint works
        if method == 'GET' and (path.endswith('/health') or path.endswith('/api/health')):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "status": "healthy",
                    "message": "Emergency handler - bot initialization disabled",
                    "timestamp": "2025-12-03"
                })
            }
        
        # Main API info - minimal response
        elif method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "message": "Telegram Sticker Bot API - Emergency Mode",
                    "status": "minimal",
                    "bot": "disabled",
                    "endpoints": {
                        "health": "/api/health"
                    }
                })
            }
        
        # Webhook - always return OK, no processing
        elif method == 'POST' and (path.endswith('/webhook') or path.endswith('/api/webhook')):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    "status": "ok",
                    "message": "Webhook received - bot disabled for maintenance"
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