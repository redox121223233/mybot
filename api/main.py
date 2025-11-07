"""
Ultra-simple Vercel compatible handler with Telegram bot functionality
Minimal dependencies, proper error handling
"""

import os
import json
import sys
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our bot handler
try:
    from bot_handler import process_telegram_update
    BOT_ENABLED = True
    logger.info("✅ Bot handler imported successfully")
except ImportError as e:
    logger.error(f"⚠️ Bot handler not available: {e}")
    BOT_ENABLED = False

class SimpleResponse:
    def __init__(self, status_code=200, headers=None, body=''):
        self.status_code = status_code
        self.headers = headers or {'Content-Type': 'text/plain'}
        self.body = body

def handler(environ, start_response):
    """
    WSGI compatible handler for Vercel
    """
    try:
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')

        # Log the request
        logger.info(f"📥 Request: {method} {path}")

        # Handle different paths
        if path == '/' and method == 'GET':
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
            body = json.dumps(response_data, indent=2)
            response = SimpleResponse(
                status_code=200,
                headers={'Content-Type': 'application/json'},
                body=body
            )

        elif path == '/health' and method == 'GET':
            health_data = {
                'status': 'healthy',
                'timestamp': str(environ.get('HTTP_X_VERCEL_TIMESTAMP', 'unknown')),
                'region': environ.get('VERCEL_REGION', 'unknown'),
                'bot_status': 'enabled' if BOT_ENABLED else 'disabled',
                'python_version': sys.version
            }
            body = json.dumps(health_data, indent=2)
            response = SimpleResponse(
                status_code=200,
                headers={'Content-Type': 'application/json'},
                body=body
            )

        elif path == '/webhook' and method == 'POST':
            try:
                # Read request body
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                if content_length > 0:
                    body_bytes = environ['wsgi.input'].read(content_length)
                    body_str = body_bytes.decode('utf-8')

                    # Parse JSON
                    webhook_data = json.loads(body_str)
                    logger.info(f"📨 Webhook received: {type(webhook_data)}")

                    if BOT_ENABLED:
                        # Process with bot handler
                        try:
                            # Run async processing
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(
                                process_telegram_update(webhook_data)
                            )
                            loop.close()
                            
                            logger.info(f"✅ Webhook processed: {result}")
                            response_data = {
                                'status': 'ok', 
                                'processed': True,
                                'result': result
                            }
                        except Exception as bot_error:
                            logger.error(f"❌ Bot processing error: {bot_error}")
                            response_data = {
                                'status': 'error', 
                                'message': f'Bot processing failed: {str(bot_error)}'
                            }
                    else:
                        # Simple echo when bot is disabled
                        logger.info("📋 Bot disabled, echoing webhook data")
                        response_data = {
                            'status': 'ok', 
                            'echo': webhook_data,
                            'note': 'Bot functionality is currently disabled'
                        }

                    body = json.dumps(response_data)
                    response = SimpleResponse(
                        status_code=200,
                        headers={'Content-Type': 'application/json'},
                        body=body
                    )
                else:
                    response_data = {'error': 'No data received'}
                    body = json.dumps(response_data)
                    response = SimpleResponse(
                        status_code=400,
                        headers={'Content-Type': 'application/json'},
                        body=body
                    )

            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                response_data = {'error': 'Invalid JSON'}
                body = json.dumps(response_data)
                response = SimpleResponse(
                    status_code=400,
                    headers={'Content-Type': 'application/json'},
                    body=body
                )
            except Exception as e:
                logger.error(f"❌ Webhook processing error: {e}", exc_info=True)
                response_data = {'error': 'Processing failed'}
                body = json.dumps(response_data)
                response = SimpleResponse(
                    status_code=500,
                    headers={'Content-Type': 'application/json'},
                    body=body
                )

        else:
            response_data = {
                'error': 'Not found',
                'available_endpoints': ['/', '/health', '/webhook']
            }
            body = json.dumps(response_data)
            response = SimpleResponse(
                status_code=404,
                headers={'Content-Type': 'application/json'},
                body=body
            )

        # Start response
        status = f"{response.status_code} OK"
        headers = list(response.headers.items())
        start_response(status, headers)

        # Return response body
        return [response.body.encode('utf-8')]

    except Exception as e:
        logger.error(f"❌ Handler error: {e}", exc_info=True)
        error_response = SimpleResponse(
            status_code=500,
            headers={'Content-Type': 'application/json'},
            body=json.dumps({'error': 'Internal server error'})
        )

        status = f"{error_response.status_code} ERROR"
        headers = list(error_response.headers.items())
        start_response(status, headers)

        return [error_response.body.encode('utf-8')]

# For Vercel compatibility
app = handler

# Test function
def test_handler():
    """Test the handler locally"""
    def start_response(status, headers):
        print(f"Status: {status}")
        print(f"Headers: {headers}")

    # Test GET request
    environ = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/',
        'CONTENT_LENGTH': '0',
        'wsgi.input': type('', (), {'read': lambda self, n: b''})()
    }

    print("🧪 Testing GET /")
    response = handler(environ, start_response)
    print(f"Response: {response[0].decode('utf-8')[:200]}...")

if __name__ == '__main__':
    test_handler()