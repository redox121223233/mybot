import json
import os
import sys
import asyncio

# Add the current directory to Python path
sys.path.append('/var/task')

try:
    from bot import bot, dp
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback for local testing
    bot = None
    dp = None

async def process_update(update):
    """Process Telegram update"""
    try:
        # Initialize bot if not already initialized
        if bot is not None:
            # Feed the update to dispatcher
            await dp.feed_update(bot, update)
    except Exception as e:
        print(f"Error in dispatcher: {e}")

def handler(request):
    """Vercel serverless function handler"""
    try:
        # Parse request
        if request.method == 'POST':
            if request.url.endswith('/webhook'):
                # Handle webhook
                body = json.loads(request.body)
                
                if bot and dp:
                    # Process the update asynchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(process_update(body))
                    loop.close()
                    
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({"status": "ok"})
                    }
                else:
                    return {
                        'statusCode': 500,
                        'body': json.dumps({"error": "Bot not initialized"})
                    }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({"error": "Not found"})
                }
        elif request.method == 'GET':
            if request.url.endswith('/health'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "healthy"})
                }
            elif request.url.endswith('/api'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "message": "Telegram Bot API is running",
                        "endpoints": {
                            "webhook": "/api/webhook",
                            "health": "/api/health"
                        }
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
        print(f"Error in handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "Internal server error"})
        }

# For Vercel compatibility
def main(request):
    return handler(request)

# Export the handler
__all__ = ['handler', 'main']