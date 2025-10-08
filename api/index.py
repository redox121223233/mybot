import os
import sys
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import bot functions
from api.bot_functions import process_update
from api.cold_start import handle_cold_start

def handler(request):
    """
    Vercel serverless function handler - Main endpoint
    بدون استفاده از cron job - فقط در زمان درخواست فعال می‌شود
    """
    try:
        # مدیریت کولد استارت بدون cron job
        handle_cold_start()
        
        method = request.method
        path = request.path
        
        print(f"Request method: {method}, path: {path}")
        
        if method == 'POST':
            # Handle webhook POST requests
            try:
                update_data = request.get_json() or {}
                print(f"Webhook data received: {update_data}")
                
                import asyncio
                asyncio.run(process_update(update_data))
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'status': 'ok', 'path': path})
                }
            except Exception as e:
                print(f"Webhook error: {e}")
                return {
                    'statusCode': 200,  # Return 200 to prevent Telegram retries
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': str(e)})
                }
        
        elif method == 'GET':
            # Health check
            print("Health check requested")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'healthy',
                    'bot': 'running',
                    'path': path,
                    'message': 'Bot is active and ready!'
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        print(f"General error: {e}")
        return {
            'statusCode': 200,  # Return 200 to prevent Telegram retries
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }