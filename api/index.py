# --- api/index.py (نسخه تست اول) ---
import os
import sys
import logging
from fastapi import Request, FastAPI, Response, status

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    """
    این تابع فقط برای تست است. هیچ منطق رباتی در آن وجود ندارد.
    """
    try:
        body = await request.body()
        print("SUCCESS: Webhook endpoint received a POST request!")
        print(f"Raw body: {body}")
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Exception in simple webhook: {e}")
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Simple FastAPI app for testing webhook."}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    logging.warning(f"Received request for unknown path: {request.method} /{path}")
    return Response(
        content=f"This endpoint is not available. Please use /webhook for Telegram bot requests.",
        status_code=status.HTTP_404_NOT_FOUND
    )
