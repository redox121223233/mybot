"""Vercel serverless function for Telegram webhook"""
import os
import sys
import json
import asyncio
from http.server import BaseHTTPRequestHandler

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import process_update

class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler"""

    def do_GET(self):
        """Handle GET requests (health check)"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            'status': 'healthy',
            'bot': 'running'
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle POST requests (webhook)"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Parse JSON
            update_data = json.loads(body.decode('utf-8'))

            # Process update
            asyncio.run(process_update(update_data))

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {
                'status': 'ok',
                'update_id': update_data.get('update_id', 'unknown')
            }
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            print(f"Error processing webhook: {e}")
            import traceback
            traceback.print_exc()

            # Send error response
            self.send_response(200)  # Return 200 to prevent Telegram retries
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {'error': str(e)}
            self.wfile.write(json.dumps(response).encode())
