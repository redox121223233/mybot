import os
import sys
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import bot functions
from api.bot_functions import process_update

def handler(request):
    """
    Vercel serverless function handler - Dedicated webhook endpoint
    """
    try:
        if request.method != 'POST':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        try:
            update_data = request.get_json() or {}
            print(f"Webhook received: {update_data}")
        except Exception as e:
            print(f"JSON parse error: {e}")
            update_data = {}
        
        import asyncio
        asyncio.run(process_update(update_data))
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'ok', 'endpoint': 'webhook'})
        }
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return {
            'statusCode': 200,  # Return 200 to prevent Telegram retries
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }