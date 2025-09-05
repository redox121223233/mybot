import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import arabic_reshaper
from bidi.algorithm import get_display
import requests
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token here
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

def download_persian_font():
    """Download a Persian font if not available locally."""
    font_path = "NotoSansFarsi-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            # Download Noto Sans Arabic font (supports Persian)
            url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf"
            response = requests.get(url)
            if response.status_code == 200:
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                logger.info("Persian font downloaded successfully")
            return font_path
        except Exception as e:
            logger.error(f"Failed to download font: {e}")
            return None
    return font_path

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('سلام! متن فارسی خود را بفرستید تا آن را به استیکر زیبا تبدیل کنم. 🎨')

def create_beautiful_persian_sticker(text: str) -> BytesIO:
    """Create a beautiful sticker from Persian text."""
    
    # Process Persian text for proper display
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    # Create image with gradient background
    img_width, img_height = 512, 512
    image = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 0))
    
    # Create a beautiful gradient background
    for y in range(img_height):
        for x in range(img_width):
            # Create a radial gradient from center
            center_x, center_y = img_width // 2, img_height // 2
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            max_distance = (img_width ** 2 + img_height ** 2) ** 0.5 / 2
            
            # Gradient colors (purple to blue)
            ratio = min(distance / max_distance, 1.0)
            r = int(138 + (63 - 138) * ratio)   # 138 -> 63
            g = int(43 + (81 - 43) * ratio)     # 43 -> 81
            b = int(226 + (181 - 226) * ratio)  # 226 -> 181
            a = 255
            
            image.putpixel((x, y), (r, g, b, a))
    
    draw = ImageDraw.Draw(image)
    
    # Try to load Persian font
    font_path = download_persian_font()
    font_size = 80
    
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            # Try system fonts that support Persian
            font_paths = [
                "arial.ttf",
                "/System/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/Windows/Fonts/arial.ttf",
                "C:\\Windows\\Fonts\\arial.ttf"
            ]
            
            font = None
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
    except Exception as e:
        logger.error(f"Font loading error: {e}")
        font = ImageFont.load_default()
    
    # Calculate text size and adjust font size if needed
    bbox = draw.textbbox((0, 0), bidi_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Adjust font size to fit nicely
    max_width = img_width - 80
    max_height = img_height - 80
    
    while (text_width > max_width or text_height > max_height) and font_size > 20:
        font_size -= 5
        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (img_width - text_width) // 2
    y = (img_height - text_height) // 2
    
    # Add multiple shadow layers for depth
    shadow_colors = [
        (0, 0, 0, 100),      # Dark shadow
        (0, 0, 0, 60),       # Medium shadow
        (0, 0, 0, 30),       # Light shadow
    ]
    
    shadow_offsets = [4, 3, 2]
    
    for i, (shadow_color, offset) in enumerate(zip(shadow_colors, shadow_offsets)):
        draw.text((x + offset, y + offset), bidi_text, font=font, fill=shadow_color)
    
    # Draw the main text with white color
    draw.text((x, y), bidi_text, font=font, fill=(255, 255, 255, 255))
    
    # Add a subtle border/outline effect
    outline_color = (200, 200, 200, 150)
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), bidi_text, font=font, fill=outline_color)
    
    # Redraw main text on top
    draw.text((x, y), bidi_text, font=font, fill=(255, 255, 255, 255))
    
    # Add decorative corners
    corner_size = 20
    corner_color = (255, 255, 255, 100)
    
    # Top-left corner
    draw.polygon([(0, 0), (corner_size, 0), (0, corner_size)], fill=corner_color)
    # Top-right corner
    draw.polygon([(img_width, 0), (img_width - corner_size, 0), (img_width, corner_size)], fill=corner_color)
    # Bottom-left corner
    draw.polygon([(0, img_height), (corner_size, img_height), (0, img_height - corner_size)], fill=corner_color)
    # Bottom-right corner
    draw.polygon([(img_width, img_height), (img_width - corner_size, img_height), (img_width, img_height - corner_size)], fill=corner_color)
    
    # Save to BytesIO
    bio = BytesIO()
    image.save(bio, format='PNG')
    bio.seek(0)
    
    return bio

async def text_to_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert text message to beautiful sticker."""
    text = update.message.text
    
    if not text:
        await update.message.reply_text('لطفاً متنی بفرستید.')
        return
    
    # Send "creating sticker" message
    status_message = await update.message.reply_text('در حال ساخت استیکر زیبا... ⏳')
    
    try:
        # Create beautiful sticker
        sticker_bio = create_beautiful_persian_sticker(text)
        
        # Delete status message
        await status_message.delete()
        
        # Send sticker
        await update.message.reply_sticker(sticker=sticker_bio)
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        await status_message.edit_text('خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.')

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_to_sticker))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
