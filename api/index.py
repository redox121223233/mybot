from fastapi import Request, FastAPI, Response, status
from fastapi.responses import JSONResponse
import logging
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Telegram Sticker Bot API")

@app.get("/")
async def root():
    return {"message": "Telegram Sticker Bot API is running"}

@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates"""
    try:
        update_data = await request.json()
        logger.info(f"Received update: {update_data}")
        
        # Process the update (placeholder for actual bot logic)
        # Here you would typically integrate with your bot handler
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success"}
        )
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "telegram-sticker-bot"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
