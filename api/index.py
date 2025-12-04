
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
import traceback

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import bot components
try:
    from aiogram import Bot, Dispatcher
    from aiogram.types import Update
    from bot_core.config import BOT_TOKEN
    from bot_core.handlers import router  # Assuming handlers are attached to this router
    print("Successfully imported bot components.")
except ImportError as e:
    print(f"Import Error: {e}")
    traceback.print_exc()
    # Define dummy variables to allow server to start even if imports fail
    BOT_TOKEN = None
    Bot = Dispatcher = Update = Router = None

# Initialize bot and dispatcher at the module level
bot = None
dp = None
if BOT_TOKEN and Bot and Dispatcher:
    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        dp.include_router(router)
        print("Bot and Dispatcher initialized successfully.")
    except Exception as e:
        print(f"Error during bot initialization: {e}")
        traceback.print_exc()
else:
    print("Skipping bot initialization due to missing components.")

# --- Event Loop Management ---
# Get the existing event loop or create a new one.
try:
    loop = asyncio.get_running_loop()
    print("Using existing event loop.")
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("Created a new event loop.")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not bot or not dp:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Bot is not initialized.'}).encode())
            print("Handler received POST, but bot is not initialized.")
            return

        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))

            print(f"Received update: {json.dumps(update_data, indent=2)}")

            # Create an Update object and process it
            update = Update.model_validate(update_data, context={"bot": bot})

            # Run the async task and wait for it to complete
            async def process():
                await dp.feed_update(bot=bot, update=update)

            # This is a blocking call that runs the async function until it's done.
            loop.run_until_complete(process())

            self.send_response(200)
            self.end_headers()
            print("Successfully processed update and sent 200 OK.")

        except Exception as e:
            error_message = f"Error processing update: {e}"
            print(error_message)
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': error_message}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running.")
        print("Received GET request, responded 'Bot is running.'")
