import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import handlers

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

def main():
    """Start the bot."""
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("help", handlers.help_command))
        
        # Search commands
        application.add_handler(CommandHandler("search", handlers.search_command))
        application.add_handler(CommandHandler("image", handlers.image_command))
        
        # Media commands
        application.add_handler(CommandHandler("music", handlers.music_command))
        application.add_handler(CommandHandler("download", handlers.download_command))
        application.add_handler(CommandHandler("movie", handlers.movie_command))
        application.add_handler(CommandHandler("series", handlers.series_command))
        
        # AI commands
        application.add_handler(CommandHandler("ai", handlers.ai_command))
        application.add_handler(CommandHandler("chat", handlers.chat_command))
        
        # Weather and crypto
        application.add_handler(CommandHandler("weather", handlers.weather_command))
        application.add_handler(CommandHandler("crypto", handlers.crypto_command))
        application.add_handler(CommandHandler("btc", handlers.btc_command))
        application.add_handler(CommandHandler("eth", handlers.eth_command))
        
        # Entertainment commands
        application.add_handler(CommandHandler("joke", handlers.joke_command))
        application.add_handler(CommandHandler("fact", handlers.fact_command))
        application.add_handler(CommandHandler("8ball", handlers.magic_8_ball_command))
        application.add_handler(CommandHandler("roll_dice", handlers.roll_dice_command))
        application.add_handler(CommandHandler("coin_flip", handlers.coin_flip_command))
        application.add_handler(CommandHandler("compliment", handlers.compliment_command))
        application.add_handler(CommandHandler("quote", handlers.quote_command))
        application.add_handler(CommandHandler("poem", handlers.poem_command))
        
        # Game commands
        application.add_handler(CommandHandler("game", handlers.game_command))
        application.add_handler(CommandHandler("quiz", handlers.quiz_command))
        application.add_handler(CommandHandler("riddle", handlers.riddle_command))
        application.add_handler(CommandHandler("number_game", handlers.number_game_command))
        application.add_handler(CommandHandler("rock_paper_scissors", handlers.rock_paper_scissors_command))
        application.add_handler(CommandHandler("memory_game", handlers.memory_game_command))
        application.add_handler(CommandHandler("word_chain", handlers.word_chain_command))
        application.add_handler(CommandHandler("trivia", handlers.trivia_command))
        
        # Shopping commands
        application.add_handler(CommandHandler("price", handlers.price_command))
        application.add_handler(CommandHandler("coupon", handlers.coupon_command))
        
        # Sticker commands
        application.add_handler(CommandHandler("sticker", handlers.sticker_command))
        application.add_handler(CommandHandler("meme", handlers.meme_command))
        
        # Utility commands
        application.add_handler(CommandHandler("time", handlers.time_command))
        application.add_handler(CommandHandler("calc", handlers.calc_command))
        application.add_handler(CommandHandler("translate", handlers.translate_command))
        application.add_handler(CommandHandler("news", handlers.news_command))
        application.add_handler(CommandHandler("technews", handlers.technews_command))
        
        # Callback query handler for inline keyboards
        application.add_handler(CallbackQueryHandler(handlers.handle_callback_query))
        
        # Message handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
        application.add_handler(MessageHandler(filters.STICKER, handlers.handle_sticker))
        
        # Start the bot
        logger.info("🚀 Bot is starting...")
        print("🤖 ربات با موفقیت شروع به کار کرد!")
        print("📱 ربات آماده دریافت پیام‌هاست...")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"❌ خطا در شروع ربات: {e}")

if __name__ == '__main__':
    main()