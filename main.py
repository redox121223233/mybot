import os
import asyncio
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
import uvicorn
from bot import process_update, set_webhook_url

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 8000))

@asynccontextmanager
async def lifespan(app: FastAPI):
    if WEBHOOK_URL:
        await set_webhook_url(WEBHOOK_URL)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "Bot is running", "message": "Webhook active"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update_data = await request.json()
        asyncio.create_task(process_update(update_data))
        return Response(status_code=200)
    except Exception as e:
        print(f"Error processing update: {e}")
        return Response(status_code=500)

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
