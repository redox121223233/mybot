"""
Simple Vercel handler - avoids complex imports and async issues
"""
import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(request):
    """
    Simple Vercel handler function
    """
    try:
        # Basic response for testing
        if hasattr(request, 'method') and request.method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'ok',
                    'message': 'Telegram Bot API is running',
                    'endpoints': {
                        'webhook': 'POST /webhook',
                        'health': 'GET /health'
                    }
                })
            }
        
        elif hasattr(request, 'method') and request.method == 'POST':
            # Handle webhook
            try:
                body = request.get_data(as_text=True)
                if body:
                    data = json.loads(body)
                    logger.info(f"Received webhook data: {data}")
                    
                    # TODO: Process Telegram update here
                    # For now, just acknowledge receipt
                    
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'status': 'ok'})
                    }
                else:
                    return {
                        'statusCode': 400,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'error': 'No data received'})
                    }
            except Exception as e:
                logger.error(f"Webhook processing error: {e}")
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': str(e)})
                }
        
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }

# Export for Vercel
app = handler