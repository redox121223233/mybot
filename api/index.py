import os
import sys
import json
import asyncio
from typing import Dict, Any

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mybot-zx31.vercel.app")

# Add parent directory to path to import bot module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import process_update, set_webhook_url

async def setup_webhook():
    """Setup webhook on startup"""
    try:
        await set_webhook_url(WEBHOOK_URL)
        print(f"✅ Webhook set successfully to: {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Failed to set webhook: {e}")

def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vercel serverless function handler for webhook
    """
    try:
        print(f"📡 Received event: {event.get('httpMethod', 'UNKNOWN')} {event.get('path', '/')}")
        
        # Handle different event types
        if event.get('httpMethod') == 'POST':
            # Webhook endpoint
            body = event.get('body', '{}')
            if isinstance(body, str):
                update_data = json.loads(body)
            else:
                update_data = body
            
            print(f"📨 Received update: {update_data.get('update_id', 'unknown')}")
            
            # Process update asynchronously
            asyncio.run(process_update(update_data))
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({'status': 'ok'})
            }
        
        elif event.get('httpMethod') == 'GET':
            # Health check endpoint
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'healthy',
                    'bot': 'running',
                    'webhook': WEBHOOK_URL,
                    'timestamp': str(asyncio.get_event_loop().time())
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        print(f"❌ Handler error: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e), 'traceback': traceback.format_exc()})
        }

# Setup webhook on cold start
if __name__ != "__main__":
    try:
        asyncio.run(setup_webhook())
    except Exception as e:
        print(f"❌ Cold start webhook setup failed: {e}")