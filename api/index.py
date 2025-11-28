from http.server import BaseHTTPRequestHandler
import json
import asyncio
import nest_asyncio
import logging
import os
import sys
from telegram import Update

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import build_application

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Build the bot application instance once when the module is loaded
try:
    application = build_application()
    logger.info("Bot application built successfully")
except Exception as e:
    logger.error(f"Failed to build bot application: {e}")
    application = None

async def process_update(data):
    """Process Telegram update with proper error handling."""
    if not application:
        logger.error("Application not initialized")
        return False
    
    try:
        if not hasattr(process_update, 'initialized'):
            await application.initialize()
            await application.start()
            process_update.initialized = True
            logger.info("Bot application initialized")

        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        logger.info(f"Processed update {update.update_id}")
        return True
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return False

class handler(BaseHTTPRequestHandler):
    """
    Vercel's native handler for serverless functions.
    Enhanced with better error handling and logging.
    """
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        logger.info(f"{self.address_string()} - {format%args}")

    def do_POST(self):
        """Handle POST requests for Telegram webhook."""
        try:
            # Log the request
            logger.info(f"POST request to {self.path}")
            
            # Get the content length and read the request body
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                logger.warning("Empty request body")
                self._send_error(400, "Empty request body")
                return
                
            body = self.rfile.read(content_len)
            logger.info(f"Received {len(body)} bytes")
            
            # Parse JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                self._send_error(400, "Invalid JSON")
                return

            # Process the update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(process_update(data))
                if success:
                    self._send_response(200, "OK")
                else:
                    self._send_error(500, "Failed to process update")
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Unexpected error in POST: {e}")
            self._send_error(500, f"Internal server error: {str(e)}")

    def do_GET(self):
        """Handle GET requests for health check."""
        logger.info(f"GET request to {self.path}")
        
        # Check if application is ready
        if application:
            self._send_response(200, "Bot is running")
        else:
            self._send_response(503, "Bot not ready")

    def _send_response(self, status_code, message):
        """Send HTTP response with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode())

    def _send_error(self, status_code, message):
        """Send error response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode())
