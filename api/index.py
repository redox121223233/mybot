from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import asyncio

# Add the current directory to Python path
sys.path.append('/var/task')

try:
    from bot import bot, dp
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback for local testing
    bot = None
    dp = None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle Telegram webhook updates"""
        if self.path != '/api/webhook':
            self.send_response(404)
            self.end_headers()
            return
        
        try:
            # Read the request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Parse the update
            update = json.loads(post_data.decode('utf-8'))
            
            if bot and dp:
                # Process the update asynchronously
                asyncio.run(self.process_update(update))
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())
            else:
                self.send_response(500)
                self.end_headers()
                
        except Exception as e:
            print(f"Error processing webhook: {e}")
            self.send_response(500)
            self.end_headers()
    
    def do_GET(self):
        """Handle health checks and setup webhook"""
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        elif self.path == '/api':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "message": "Telegram Bot API is running",
                "endpoints": {
                    "webhook": "/api/webhook",
                    "health": "/api/health"
                }
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    async def process_update(self, update):
        """Process Telegram update"""
        try:
            # Initialize bot if not already initialized
            if bot is not None:
                # Feed the update to dispatcher
                await dp.feed_update(bot, update)
        except Exception as e:
            print(f"Error in dispatcher: {e}")