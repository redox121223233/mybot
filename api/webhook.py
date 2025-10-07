import os
import sys
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import bot functions
from api.bot_functions import process_update

def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vercel serverless function handler - Dedicated webhook endpoint
    """
    try:
        if event.get('httpMethod') != 'POST':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                update_data = json.loads(body)
            except json.JSONDecodeError:
                update_data = {}
        else:
            update_data = body
        
        import asyncio
        asyncio.run(process_update(update_data))
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'ok', 'endpoint': 'webhook'})
        }
    
    except Exception as e:
        return {
            'statusCode': 200,  # Return 200 to prevent Telegram retries
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }