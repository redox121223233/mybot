
import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
import nest_asyncio

# Apply nest_asyncio once at the top level
nest_asyncio.apply()

# --- Setup sys.path ---
# Ensure the project root is in the path to allow imports from bot_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Global Bot Initialization ---
# This section runs only ONCE when the Vercel instance starts (cold start).
BOT_INITIALIZED = False
BOT_INSTANCE = None
DISPATCHER_INSTANCE = None

try:
    print("--- STARTING BOT INITIALIZATION ---", file=sys.stderr)
    from aiogram import Bot, Dispatcher
    from aiogram.types import Update
    from bot_core.config import BOT_TOKEN
    print("---IMPORTED CONFIG---", file=sys.stderr)
    from bot_core.handlers import router
    print("---IMPORTED HANDLERS---", file=sys.stderr)

    if not BOT_TOKEN:
        print("!!! BOT_TOKEN IS NOT SET !!!", file=sys.stderr)
        raise ValueError("BOT_TOKEN is not configured in environment variables.")

    print(f"--- BOT_TOKEN FOUND: ...{BOT_TOKEN[-4:]} ---", file=sys.stderr)
    BOT_INSTANCE = Bot(token=BOT_TOKEN)
    print("--- BOT INSTANCE CREATED ---", file=sys.stderr)
    DISPATCHER_INSTANCE = Dispatcher()
    DISPATCHER_INSTANCE.include_router(router)
    print("--- DISPATCHER CONFIGURED ---", file=sys.stderr)

    BOT_INITIALIZED = True
    print("--- BOT INITIALIZED SUCCESSFULLY ---", file=sys.stderr)

except Exception as e:
    print("--- BOT INITIALIZATION FAILED ---", file=sys.stderr)
    print(f"Error Type: {type(e).__name__}", file=sys.stderr)
    print(f"Error Message: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

# --- Event Loop Management ---
# Get or create an event loop that will be reused across invocations.
try:
    LOOP = asyncio.get_running_loop()
    print("Attached to existing asyncio event loop.")
except RuntimeError:
    LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(LOOP)
    print("Created and set new asyncio event loop.")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handles incoming POST requests from Telegram."""
        if not BOT_INITIALIZED:
            print("ERROR: Received POST request, but bot is not initialized.")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Bot failed to initialize.'}).encode())
            return

        async def process_update():
            """Async function to handle the update."""
            try:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                update_data = json.loads(body.decode('utf-8'))

                update = Update.model_validate(update_data, context={"bot": BOT_INSTANCE})

                await DISPATCHER_INSTANCE.feed_update(bot=BOT_INSTANCE, update=update)

                self.send_response(200)
                self.end_headers()

            except json.JSONDecodeError:
                print("ERROR: Could not decode JSON from request body.")
                self.send_response(400) # Bad Request
                self.end_headers()
            except Exception as e:
                print(f"--- ERROR PROCESSING UPDATE ---")
                print(f"Error: {e}")
                traceback.print_exc()
                self.send_response(500) # Internal Server Error
                self.end_headers()

        # Run the async processing on our persistent event loop
        LOOP.run_until_complete(process_update())

    def do_GET(self):
        """Handles GET requests for health checks."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            'status': 'ok',
            'bot_initialized': BOT_INITIALIZED
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
