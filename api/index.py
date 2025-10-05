import os
import sys
import json

from async_loop import run_sync

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import process_update

async def handle_request(request):
    """Process incoming webhook request"""
    try:
        # Parse request body
        if hasattr(request, 'get_json'):
            update_data = await request.get_json()
        elif hasattr(request, 'json'):
            update_data = request.json() if callable(request.json) else request.json
        else:
            body = request.get('body', '{}')
            if isinstance(body, str):
                update_data = json.loads(body) if body else {}
            else:
                update_data = body

        # Process update
        if update_data:
            await process_update(update_data)

        return {
            'status': 'ok',
            'update_id': update_data.get('update_id', 'unknown')
        }
    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

def handler(request):
    """Vercel serverless handler"""
    from flask import Flask, request as flask_request, jsonify

    try:
        method = flask_request.method if hasattr(flask_request, 'method') else request.get('httpMethod', 'GET')

        if method == 'POST':
            # Handle webhook
            result = run_sync(handle_request(flask_request if hasattr(flask_request, 'method') else request))
            return jsonify(result)
        else:
            # Health check
            return jsonify({
                'status': 'healthy',
                'bot': 'running',
                'method': method
            })
    except Exception as e:
        print(f"Handler error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 200

# For Vercel
app = handler
