import asyncio
import json
import logging
import os
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from flask import Flask, request as flask_request
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot initialization flag
bot_initialized = False

# Stages for sticker creation
PHOTO, TEXT, CONFIRM = range(3)
# States for main menu
MENU_STATE = 'MENU'
# Admin user ID
ADMIN_ID = 5935332189
# Path for font file
FONT_FILE = os.path.join(os.path.dirname(__file__), 'Vazirmatn-Regular.ttf')

# Data storage paths in Vercel's writable directory
USERS_FILE = '/tmp/users.json'
SESSIONS_FILE = '/tmp/sessions.json'

def load_data(file_path):
    """Loads data from a JSON file."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
    return {}

def save_data(data, file_path):
    """Saves data to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")

# Load initial data
users = load_data(USERS_FILE)
sessions = load_data(SESSIONS_FILE)
logger.info(f"Initial users loaded: {list(users.keys())}")

def save_all_data():
    """Saves both users and sessions data."""
    save_data(users, USERS_FILE)
    save_data(sessions, SESSIONS_FILE)

async def start(update: Update, context: CallbackContext) -> int:
    """Sends a welcome message and directs the user to the main menu."""
    user = update.effective_user
    user_id = str(user.id)
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    if user_id not in users:
        try:
            # Note: Replace '@YOUR_CHANNEL_ID' with your actual channel ID
            chat_member = await context.bot.get_chat_member(chat_id='@YOUR_CHANNEL_ID', user_id=user.id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                users[user_id] = {'subscribed': True, 'name': user.first_name}
                save_all_data()
            else:
                await update.message.reply_text("Please join our channel to use the bot.")
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Could not check channel subscription for {user_id}: {e}")
            await update.message.reply_text("Welcome! We couldn't verify your channel subscription, but you can proceed.")

    sessions[user_id] = {}
    save_all_data()
    await update.message.reply_text("Welcome to the sticker bot! Please send a photo to start.")
    return PHOTO

async def photo_handler(update: Update, context: CallbackContext) -> int:
    """Stores the photo and asks for the text."""
    user_id = str(update.effective_user.id)
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f'/tmp/user_photo_{user_id}.jpg'
    await photo_file.download_to_drive(photo_path)

    sessions[user_id]['photo'] = photo_path
    save_all_data()

    await update.message.reply_text("Great! Now, please send the text you want to add to the sticker.")
    return TEXT

async def text_handler(update: Update, context: CallbackContext) -> int:
    """Stores the text and shows a confirmation."""
    user_id = str(update.effective_user.id)
    text = update.message.text
    sessions[user_id]['text'] = text
    save_all_data()

    await update.message.reply_text(f"Your text is: '{text}'. Is this correct? (yes/no)")
    return CONFIRM

async def confirm_handler(update: Update, context: CallbackContext) -> int:
    """Processes the confirmation and creates the sticker."""
    user_id = str(update.effective_user.id)
    user_response = update.message.text.lower()

    if user_response == 'yes':
        try:
            photo_path = sessions[user_id]['photo']
            text = sessions[user_id]['text']

            # Create the sticker
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)

            image = Image.open(photo_path).convert("RGBA")
            txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            try:
                font = ImageFont.truetype(FONT_FILE, 40)
            except IOError:
                logger.error(f"Font file not found at {FONT_FILE}. Using default font.")
                font = ImageFont.load_default()

            draw.text((10, 10), bidi_text, font=font, fill=(0, 0, 0, 255))
            out = Image.alpha_composite(image, txt_layer)

            sticker_path = f'/tmp/sticker_{user_id}.webp'
            out.save(sticker_path, 'WEBP')

            # Send the sticker
            with open(sticker_path, 'rb') as sticker_file:
                await update.message.reply_sticker(sticker=sticker_file)

            await update.message.reply_text("Here is your sticker! Send another photo to create a new one.")

            # Clean up session
            if os.path.exists(photo_path):
                os.remove(photo_path)
            if os.path.exists(sticker_path):
                os.remove(sticker_path)
            del sessions[user_id]
            save_all_data()

            return PHOTO

        except Exception as e:
            logger.error(f"Error creating sticker for user {user_id}: {e}")
            await update.message.reply_text("Sorry, something went wrong. Please try again from the beginning by sending a photo.")
            return PHOTO

    else:
        await update.message.reply_text("Okay, let's try again. Please send the text.")
        return TEXT


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.effective_user
    user_id = str(user.id)
    logger.info(f"User {user.first_name} canceled the conversation.")

    # Clean up user's session data
    if user_id in sessions:
        if 'photo' in sessions[user_id] and os.path.exists(sessions[user_id]['photo']):
            os.remove(sessions[user_id]['photo'])
        del sessions[user_id]
        save_all_data()

    await update.message.reply_text(
        'Sticker creation canceled. Send a photo anytime to start over.'
    )
    return ConversationHandler.END

async def post_init(application: Application):
    """Sets the webhook after the application is initialized."""
    webhook_url = f"https://{os.environ.get('VERCEL_URL')}/api/index"
    await application.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook set to {webhook_url}")

# --- Flask App ---
app = Flask(__name__)

# --- Telegram Bot Application Setup ---
# We build the application instance once when the module is loaded.
telegram_app = (
    Application.builder()
    .token(os.environ.get("TELEGRAM_TOKEN"))
    .post_init(post_init)
    .build()
)

# Add conversation handler with the states
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start), MessageHandler(filters.PHOTO, photo_handler)],
    states={
        PHOTO: [MessageHandler(filters.PHOTO, photo_handler)],
        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
        CONFIRM: [MessageHandler(filters.Regex('^(?i)(yes|no)$'), confirm_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)
telegram_app.add_handler(conv_handler)


@app.route('/api/index', methods=['POST'])
async def webhook():
    """Webhook endpoint to process Telegram updates."""
    global bot_initialized
    if not bot_initialized:
        logger.info("First request received. Initializing bot application...")
        await telegram_app.initialize()
        bot_initialized = True
        logger.info("Bot application initialized.")

    try:
        req_json = flask_request.get_json(force=True)
        update = Update.de_json(req_json, telegram_app.bot)
        await telegram_app.process_update(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Error processing update in webhook: {e}")
        return 'error', 500

@app.route('/api/set_webhook', methods=['GET'])
async def set_webhook_route():
    """Manual webhook set endpoint for verification."""
    global bot_initialized
    if not bot_initialized:
       logger.info("Manual webhook set request. Initializing bot application...")
       await telegram_app.initialize()
       bot_initialized = True
       logger.info("Bot application initialized.")

    webhook_info = await telegram_app.bot.get_webhook_info()
    return f"Webhook is set to: {webhook_info.url}"

if __name__ == "__main__":
    # This block is for local development, not for Vercel
    logger.info("Starting bot in polling mode for local development...")
    telegram_app.run_polling()
