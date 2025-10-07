import os
import sys
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import bot functions
from api.bot_functions import process_update
from api.cold_start import handle_cold_start

def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vercel serverless function handler - Main endpoint
    بدون استفاده از cron job - فقط در زمان درخواست فعال می‌شود
    """
    try:
        # مدیریت کولد استارت بدون cron job
        handle_cold_start()
        
        method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        
        if method == 'POST':
            # Handle webhook POST requests
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
                'body': json.dumps({'status': 'ok', 'path': path})
            }
        
        elif method == 'GET':
            # Health check
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'healthy',
                    'bot': 'running',
                    'path': path
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        return {
            'statusCode': 200,  # Return 200 to prevent Telegram retries
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }