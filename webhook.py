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
                elif 'callback_query' in update_data:
                    callback_query = update_data['callback_query']
                    logger.info(f"Callback query data: {callback_query.get('data', 'No data')}")
                
                # پاسخ سریع به تلگرام قبل از پردازش کامل
                # این باعث می‌شه تلگرام تاخیر کمتری احساس کنه
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'status': 'ok', 'message': 'Webhook processed'}
                self.wfile.write(json.dumps(response).encode())
                logger.info("Response sent quickly")
                
                # حالا update رو در محیط سرورلس پردازش می‌کنیم
                # با مدیریت صحیح event loop
                try:
                    logger.info("Processing update in serverless environment...")
                    
                    # ایجاد event loop جدید برای هر درخواست در سرورلس
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # پردازش update در event loop جدید
                        loop.run_until_complete(process_update(update_data))
                        logger.info("Update processed successfully in serverless")
                    except Exception as process_error:
                        logger.error(f"Error in serverless processing: {process_error}")
                    finally:
                        # بستن event loop بعد از پردازش
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"Error setting up event loop: {e}")
                    # Don't raise the exception to prevent Telegram retries
            else:
                logger.info("No content in request")
                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'status': 'ok', 'message': 'No content'}
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
            logger.info("Error response sent successfully")
    
    def do_GET(self):
        logger.info("Webhook GET request received")
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ok', 'message': 'Webhook is active and optimized for serverless'}
        self.wfile.write(json.dumps(response).encode())
        logger.info("GET response sent successfully")
