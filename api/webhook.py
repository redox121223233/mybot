import json
from api.bot_functions import process_update

def handler(request):
    """Webhook endpoint for Telegram updates"""
    try:
        # Only accept POST requests
        if request.method != 'POST':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # Get the update data from the request
        try:
            update_data = json.loads(request.body)
            print(f"Webhook received update: {update_data.get('update_id')}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in webhook: {e}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON'})
            }
        
        # Process the update asynchronously
        import asyncio
        try:
            asyncio.run(process_update(update_data))
            print("Update processed successfully")
        except Exception as e:
            print(f"Error processing update: {e}")
            # Don't return error to Telegram to prevent retries
        
        # Always return success to Telegram
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'ok'})
        }
        
    except Exception as e:
        print(f"Webhook error: {e}")
        # Always return success to prevent Telegram from retrying
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'ok', 'error': str(e)})
        }