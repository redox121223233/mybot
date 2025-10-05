import os
import os
import sys
import json

from async_loop import run_sync

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mybot-zx31.vercel.app")

# Add parent directory to path to import bot module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from bot import process_update
    print("✅ Successfully imported bot module")
except ImportError as e:
    print(f"❌ Failed to import bot module: {e}")
    # Fallback handler
    def process_update(update_data):
        print(f"Fallback: Received update {update_data.get('update_id', 'unknown')}")

def app(environ, start_response):
    """
    WSGI application for Vercel
    """
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    print(f"📡 {method} {path}")
    
    if method == 'POST' and path == '/webhook':
        try:
            # Read request body
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                body = environ['wsgi.input'].read(content_length)
                update_data = json.loads(body.decode('utf-8'))
                print(f"📨 Processing update: {update_data.get('update_id', 'unknown')}")
                
                # Process update (synchronously for WSGI)
                run_sync(process_update(update_data))
                
                response = {'status': 'ok', 'update_id': update_data.get('update_id')}
            else:
                response = {'error': 'No body'}
            
            status = '200 OK'
            headers = [('Content-Type', 'application/json')]
            body = json.dumps(response).encode('utf-8')
            
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            status = '200 OK'  # Return 200 to prevent Telegram retries
            headers = [('Content-Type', 'application/json')]
            body = json.dumps({'error': str(e)}).encode('utf-8')
    
    elif method == 'GET' and path in ['/', '/health']:
        status = '200 OK'
        headers = [('Content-Type', 'application/json')]
        response = {
            'status': 'healthy',
            'bot': 'running',
            'webhook': WEBHOOK_URL,
            'bot_token_set': bool(BOT_TOKEN)
        }
        body = json.dumps(response).encode('utf-8')
    
    else:
        status = '405 Method Not Allowed'
        headers = [('Content-Type', 'application/json')]
        body = json.dumps({'error': 'Method not allowed'}).encode('utf-8')
    
    headers.append(('Content-Length', str(len(body))))
    start_response(status, headers)
    return [body]
