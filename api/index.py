"""
FastAPI API endpoint برای ربات استیکر ساز
Webhook handler for Vercel deployment
"""

import os
import asyncio
from fastapi import FastAPI, Request, Response
from .main import bot, dp, BOT_USERNAME

# ایجاد FastAPI app
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    """راه‌اندازی ربات و تنظیم webhook"""
    global BOT_USERNAME
    try:
        bot_info = await bot.get_me()
        BOT_USERNAME = bot_info.username
        print(f"ربات با نام کاربری @{BOT_USERNAME} شروع به کار کرد")
        
        # تنظیم webhook برای Vercel
        webhook_url = os.getenv("VERCEL_URL")
        if webhook_url:
            webhook_url = f"https://{webhook_url}/webhook"
            
            # بررسی وضعیت فعلی webhook
            try:
                current_webhook = await bot.get_webhook_info()
                if current_webhook.url == webhook_url:
                    print(f"Webhook already correctly set to: {webhook_url}")
                else:
                    print(f"Current webhook: {current_webhook.url}, setting new webhook...")
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await bot.set_webhook(url=webhook_url)
                            print(f"Webhook set to: {webhook_url}")
                            break
                        except Exception as webhook_error:
                            if "Flood control" in str(webhook_error) or "Too Many Requests" in str(webhook_error):
                                wait_time = 2 ** attempt + 1  # exponential backoff + 1
                                print(f"Flood control detected, waiting {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                                if attempt == max_retries - 1:
                                    print("Max retries reached, webhook setting failed")
                                    print("Bot will still work but webhook might not be updated")
                            else:
                                raise webhook_error
            except Exception as webhook_check_error:
                print(f"Could not check webhook status: {webhook_check_error}")
                # تلاش برای تنظیم webhook بدون بررسی
                try:
                    await bot.set_webhook(url=webhook_url)
                    print(f"Webhook set to: {webhook_url}")
                except Exception as direct_set_error:
                    print(f"Could not set webhook: {direct_set_error}")
                    print("Bot will still work - make sure webhook is manually set if needed")
        
    except Exception as e:
        print(f"Error in startup: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    """بستن سشن ربات"""
    try:
        await bot.session.close()
    except Exception as e:
        print(f"Error in shutdown: {e}")

@app.post("/webhook")
async def bot_webhook(request: Request):
    """Handle incoming webhook updates from Telegram"""
    try:
        # دریافت update از تلگرام
        import json
        from aiogram.types import Update
        
        update_data = await request.json()
        
        # پردازش update در aiogram
        update = Update.model_validate(update_data, context={"bot": bot})
        
        # اجرای update در dispatcher
        await dp.feed_webhook_update(bot, update)
        
        return Response(status_code=200, content="OK")
    except Exception as e:
        print(f"Webhook error: {e}")
        return Response(status_code=500, content="Error")

@app.get("/")
async def root():
    """Check bot status"""
    return {
        "status": "bot is running", 
        "bot_username": BOT_USERNAME if BOT_USERNAME else "loading..."
    }

# برای اجرا در محیط توسعه محلی
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)