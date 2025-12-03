import json
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def handler(event, context):
    """Minimal Vercel handler - absolutely no custom objects"""
    try:
        method = event.get('method', 'GET')
        path = event.get('path', '')
        
        if method == 'GET':
            if path.endswith('/health') or path.endswith('/api/health'):
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "healthy"})
                }
            else:
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"message": "Bot API running"})
                }
        elif method == 'POST':
            if path.endswith('/webhook') or path.endswith('/api/webhook'):
                # Just return success - no processing for now
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({"status": "ok"})
                }
        else:
            return {'statusCode': 405, 'body': 'Method not allowed'}
            
    except Exception as e:
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

# Export for Vercel
__all__ = ['handler']