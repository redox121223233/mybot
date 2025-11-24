"""
Vercel serverless function for Telegram bot webhook
"""
import asyncio
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import sys

# Add parent directory to path to import bot.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import main, router, BOT_TOKEN

app = FastAPI()

# Global variables for bot and dispatcher
bot = None
dp = None

@app.on_event("startup")
async def startup_event():
    """Initialize bot and dispatcher when server starts"""
    global bot, dp
    try:
        from aiogram import Bot, Dispatcher, F
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        
        # Create bot instance
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Create dispatcher
        dp = Dispatcher()
        
        # Include router from bot.py
        dp.include_router(router)
        
        # Get bot info
        bot_info = await bot.get_me()
        print(f"Bot initialized: @{bot_info.username}")
        
        # Set webhook
        webhook_url = f"https://{os.environ.get('VERCEL_URL', 'localhost:3000')}/api/webhook"
        await bot.set_webhook(webhook_url)
        print(f"Webhook set to: {webhook_url}")
        
    except Exception as e:
        print(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up when server shuts down"""
    global bot
    if bot:
        try:
            await bot.delete_webhook()
            print("Webhook deleted")
        except Exception as e:
            print(f"Error deleting webhook: {e}")

@app.post("/api/webhook")
async def webhook(request: Request):
    """Handle incoming webhook updates from Telegram"""
    global bot, dp
    
    if not bot or not dp:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        # Get update data from request
        update_data = await request.json()
        
        # Create update object and feed to dispatcher
        from aiogram.types import Update
        update = Update.model_validate(update_data)
        
        # Process update
        await dp.feed_update(bot=bot, update=update)
        
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy", "bot_initialized": bot is not None})

@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(content={"message": "Telegram Bot API Server", "status": "running"})

# Vercel serverless function handler
async def handler(request):
    """Main handler for Vercel serverless functions"""
    if request.method == "POST" and request.url.path == "/api/webhook":
        return await webhook(request)
    elif request.method == "GET" and request.url.path == "/api/health":
        return await health_check()
    elif request.method == "GET" and request.url.path == "/":
        return await root()
    else:
        raise HTTPException(status_code=404, detail="Not found")

# Export for Vercel
app.handler = handler