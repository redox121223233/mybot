import json

def handler(request):
    """Simple health check endpoint"""
    try:
        print("Health check requested")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'healthy',
                'bot': 'running',
                'message': 'Bot is active!'
            })
        }
    except Exception as e:
        print(f"Health check error: {e}")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }