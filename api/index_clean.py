def handler(request):
    """Pure Vercel handler - no async, no complex imports"""
    try:
        # Basic response for testing
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"status": "ok", "message": "Bot API working"}'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }

# For Vercel compatibility
def main(request):
    return handler(request)

# Export
__all__ = ['handler', 'main']