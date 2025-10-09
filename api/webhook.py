import os
import json
import logging
import asyncio
import sys
from http.server import BaseHTTPRequestHandler

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.bot_functions import process_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                logger.info(f"Webhook received: {data}")

                # Process the update asynchronously
                try:
                    asyncio.run(process_update(data))
                except Exception as e:
                    logger.error(f"Error processing update: {e}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {'status': 'ok', 'message': 'Webhook received'}
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ok', 'message': 'Webhook endpoint is active'}
        self.wfile.write(json.dumps(response).encode())