"""
Vercel-compatible handler for Telegram bot
Follows Vercel Python runtime requirements
"""

import os
import json
import sys
import logging
import asyncio
from http.server import BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import bot handler with fallback
try:
    from bot_handler import process_telegram_update
    BOT_ENABLED = True
    logger.info("✅ Bot handler imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Bot handler not available: {e}")
    BOT_ENABLED = False

class handler(BaseHTTPRequestHandler):
    """
    Vercel-compatible HTTP handler
    Must inherit from BaseHTTPRequestHandler for Vercel Python runtime
    """
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            logger.info(f"📥 GET request: {self.path}")
            
            if self.path == '/' or self.path == '':
                response_data = {
                    'status': 'ok',
                    'message': 'Telegram Bot API is running',
                    'version': '2.0.0',
                    'bot_enabled': BOT_ENABLED,
                    'endpoints': {
                        'webhook': 'POST /webhook',
                        'health': 'GET /health'
                    },
                    'features': {
                        'sticker_creation': True,
                        'webp_format': True,
                        'pack_management': True
                    }
                }
                self.send_json_response(200, response_data)
                
            elif self.path == '/health':
                health_data = {
                    'status': 'healthy',
                    'bot_status': 'enabled' if BOT_ENABLED else 'disabled',
                    'python_version': sys.version,
                    'platform': sys.platform
                }
                self.send_json_response(200, health_data)
                
            else:
                error_data = {
                    'error': 'Not found',
                    'available_endpoints': ['/', '/health', '/webhook']
                }
                self.send_json_response(404, error_data)
                
        except Exception as e:
            logger.error(f"❌ GET error: {e}", exc_info=True)
            self.send_json_response(500, {'error': 'Internal server error'})
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            logger.info(f"📥 POST request: {self.path}")
            
            if self.path == '/webhook' or self.path == '/api/webhook':
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    webhook_data = json.loads(body.decode('utf-8'))
                    
                    logger.info(f"📨 Webhook received: update_id={webhook_data.get('update_id', 'unknown')}")
                    
                    if BOT_ENABLED:
                        try:
                            # Process with bot handler
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(
                                process_telegram_update(webhook_data)
                            )
                            loop.close()
                            
                            logger.info(f"✅ Webhook processed successfully")
                            self.send_json_response(200, {
                                'status': 'ok',
                                'processed': True,
                                'result': result
                            })
                        except Exception as bot_error:
                            logger.error(f"❌ Bot processing error: {bot_error}", exc_info=True)
                            self.send_json_response(500, {
                                'status': 'error',
                                'message': str(bot_error)
                            })
                    else:
                        # Echo when bot disabled
                        logger.info("📋 Bot disabled, echoing webhook")
                        self.send_json_response(200, {
                            'status': 'ok',
                            'echo': webhook_data,
                            'note': 'Bot functionality is currently disabled'
                        })
                else:
                    self.send_json_response(400, {'error': 'No data received'})
            else:
                self.send_json_response(404, {'error': 'Endpoint not found'})
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            self.send_json_response(400, {'error': 'Invalid JSON'})
        except Exception as e:
            logger.error(f"❌ POST error: {e}", exc_info=True)
            self.send_json_response(500, {'error': 'Internal server error'})
    
    def send_json_response(self, status_code, data):
        """Send JSON response"""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response_body = json.dumps(data, indent=2)
            self.wfile.write(response_body.encode('utf-8'))
        except Exception as e:
            logger.error(f"❌ Error sending response: {e}")
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")

# For local testing
if __name__ == '__main__':
    from http.server import HTTPServer
    
    print("🧪 Starting test server on http://localhost:8000")
    server = HTTPServer(('localhost', 8000), handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()