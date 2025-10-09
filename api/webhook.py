from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.bot_functions import process_update

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Log the request
            logger.info("Webhook POST request received")
            
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            logger.info(f"Content length: {content_length}")
            
            # Read request body
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                update_data = json.loads(post_data.decode('utf-8'))
                logger.info(f"Update data received: {update_data}")
                
                # Log specific information about the update
                if 'message' in update_data:
                    message = update_data['message']
                    if 'text' in message:
                        logger.info(f"Message text: {message['text']}")
                        if message['text'] == '/start':
                            logger.info("Received /start command")
                
                # Try to process the update
                try:
                    logger.info("Attempting to process update...")
                    asyncio.run(process_update(update_data))
                    logger.info("Update processed successfully")
                except Exception as e:
                    logger.error(f"Error processing update: {e}")
                    # Don't raise the exception to prevent Telegram retries
            else:
                logger.info("No content in request")
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'ok', 'message': 'Webhook processed'}
            self.wfile.write(json.dumps(response).encode())
            logger.info("Response sent successfully")
            
        except Exception as e:
            # Log error but still send success response to prevent Telegram retries
            logger.error(f"Webhook error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'ok', 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def do_GET(self):
        logger.info("Webhook GET request received")
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ok', 'message': 'Webhook is active'}
        self.wfile.write(json.dumps(response).encode())
        logger.info("GET response sent successfully")