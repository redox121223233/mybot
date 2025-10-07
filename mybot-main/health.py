import json
import time
import os

def handler(event, context):
    """Health check endpoint for Vercel"""
    try:
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'timestamp': time.time(),
                'platform': 'vercel',
                'bot_configured': bool(os.environ.get('BOT_TOKEN')),
                'webhook_secret_set': bool(os.environ.get('WEBHOOK_SECRET')),
                'message': 'Bot is running on Vercel!'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }