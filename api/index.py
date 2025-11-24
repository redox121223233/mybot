from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
import sys

# Add parent directory to path to import bot.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import main, router, BOT_TOKEN

# Global variables for bot and dispatcher
bot = None
dp = None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/api/health':
            response_data = {"status": "healthy", "bot_initialized": bot is not None}
        else:
            response_data = {"message": "Telegram Bot API Server", "status": "running"}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
        return

    def do_POST(self):
        """Handle POST requests - Telegram webhooks"""
        global bot, dp
        
        if self.path != '/api/webhook':
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))
            return

        try:
            # Read the request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            # Initialize bot if not already done
            if bot is None or dp is None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    self._initialize_bot(loop)
                finally:
                    loop.close()
            
            # Process the update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._process_update(update_data))
            finally:
                loop.close()
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            
        except Exception as e:
            print(f"Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        return

    def _initialize_bot(self, loop):
        """Initialize bot and dispatcher"""
        global bot, dp
        try:
            from aiogram import Bot, Dispatcher
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            
            # Create bot instance
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            
            # Create dispatcher
            dp = Dispatcher()
            
            # Include router from bot.py
            dp.include_router(router)
            
            # Get bot info
            bot_info = loop.run_until_complete(bot.get_me())
            print(f"Bot initialized: @{bot_info.username}")
            
            # Set webhook
            webhook_url = f"https://{os.environ.get('VERCEL_URL', 'localhost:3000')}/api/webhook"
            loop.run_until_complete(bot.set_webhook(webhook_url))
            print(f"Webhook set to: {webhook_url}")
            
        except Exception as e:
            print(f"Error during initialization: {e}")
            raise

    async def _process_update(self, update_data):
        """Process Telegram update"""
        global bot, dp
        
        if not bot or not dp:
            raise Exception("Bot not initialized")
        
        # Create update object and feed to dispatcher
        from aiogram.types import Update
        update = Update.model_validate(update_data)
        
        # Process update
        await dp.feed_update(bot=bot, update=update)