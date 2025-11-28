from http.server import BaseHTTPRequestHandler
import json
import asyncio
import nest_asyncio
from telegram import Update

from bot import build_application

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Build the bot application instance once when the module is loaded
application = build_application()

async def main(data):
    """Initializes the bot (if needed) and processes one update."""
    if not hasattr(main, 'initialized'):
        await application.initialize()
        # Note: Webhook should be set manually or via a separate script for stability
        main.initialized = True

    await application.process_update(Update.de_json(data, application.bot))

class handler(BaseHTTPRequestHandler):
    """
    Vercel's native handler for serverless functions.
    This replaces the need for a separate web framework like Flask.
    """
    def do_POST(self):
        try:
            # Get the content length and read the request body
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            data = json.loads(body)

            # Process the update using our async logic
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main(data))

            # Send a 200 OK response
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            # If anything goes wrong, send a 500 error
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):
        """A simple GET handler to confirm the server is running."""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Hello, World!')
