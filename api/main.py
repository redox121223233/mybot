"""
Ultra-simple Vercel compatible handler - no Flask, minimal dependencies
"""
import os
import json
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info(f"Request: {method} {path}")
        
        # Handle different paths
        if path == '/' and method == 'GET':
            response_data = {
                'status': 'ok',
                'message': 'Telegram Bot API is running',
                'version': '1.0.0',
                'endpoints': {
                    'webhook': 'POST /webhook',
                    'health': 'GET /health'
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
                'region': environ.get('VERCEL_REGION', 'unknown')
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
                    logger.info(f"Webhook received: {webhook_data}")
                    
                    # Simple response for now
                    response_data = {'status': 'ok', 'processed': True}
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
                logger.error(f"JSON decode error: {e}")
                response_data = {'error': 'Invalid JSON'}
                body = json.dumps(response_data)
                response = SimpleResponse(
                    status_code=400,
                    headers={'Content-Type': 'application/json'},
                    body=body
                )
            except Exception as e:
                logger.error(f"Webhook processing error: {e}")
                response_data = {'error': 'Processing failed'}
                body = json.dumps(response_data)
                response = SimpleResponse(
                    status_code=500,
                    headers={'Content-Type': 'application/json'},
                    body=body
                )
        
        else:
            response_data = {'error': 'Not found'}
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
        logger.error(f"Handler error: {e}")
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
    
    print("Testing GET /")
    response = handler(environ, start_response)
    print(f"Response: {response[0].decode('utf-8')}")

if __name__ == '__main__':
    test_handler()