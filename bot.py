from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Message, InputFile
from aiogram.filters import Command
import asyncio
import os
from PIL import Image, ImageDraw, ImageFont
import textwrap
import arabic_reshaper
from bidi.algorithm import get_display

# Initialize router (always available)
router = Router()

def wrap_text_to_width_persian(text, font, max_width):
    """Wrap Persian text to fit within a specified width."""
    # Reshape and reorder Persian text for proper display
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    # Split the text into words
    words = bidi_text.split()
    lines = []
    current_line = ""
    
    for word in words:
        # Check if adding this word would exceed the max width
        test_line = current_line + " " + word if current_line else word
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0]
        
        if line_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # برای متن فارسی، ترتیب طبیعی: کلمات به ترتیب از بالا به پایین
    # بدون reverse کردن - ترتیب طبیعی حفظ می‌شود
    return lines

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("سلام! خوش آمدید به ربات تبدیل متن به استیکر. لطفاً یک متن فارسی ارسال کنید.")

@router.message()
async def handle_message(message: Message):
    text = message.text
    
    # Create a new image with white background
    width, height = 512, 512
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Load a font that supports Persian
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    # Wrap the Persian text
    lines = wrap_text_to_width_persian(text, font, width - 40)
    
    # Calculate text height and center vertically
    line_height = 60
    total_height = len(lines) * line_height
    y_start = (height - total_height) // 2
    
    # Draw each line of text
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        y = y_start + i * line_height
        draw.text((x, y), line, font=font, fill='black')
    
    # Save the image
    image_path = "sticker.png"
    image.save(image_path)
    
    # Send as sticker
    sticker = InputFile(image_path)
    await bot.send_sticker(chat_id=message.chat.id, sticker=sticker)
    
    # Clean up
    os.remove(image_path)

# Initialize bot only if token is available
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    bot = Bot(token=BOT_TOKEN)
else:
    # For serverless environment, bot will be initialized by the environment
    bot = None

# For serverless compatibility - export bot and router
__all__ = ['router', 'bot']

# For local testing
async def main():
    if bot:
        dp = Dispatcher()
        dp.include_router(router)
        await dp.start_polling(bot)

if __name__ == '__main__':
    if bot:
        asyncio.run(main())