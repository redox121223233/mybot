import logging
from telegram import Update
from telegram.ext import CallbackContext
from bot import bot_features

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Basic command handlers
async def start_command(update: Update, context: CallbackContext):
    """Handle /start command"""
    try:
        await bot_features.start_command(update, context)
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

async def help_command(update: Update, context: CallbackContext):
    """Handle /help command"""
    try:
        await bot_features.help_command(update, context)
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# Search commands
async def search_command(update: Update, context: CallbackContext):
    """Handle /search command"""
    try:
        if not context.args:
            await update.message.reply_text("🔍 لطفاً متن جستجو را وارد کنید:\nمثال: /search پایتخت ایران")
            return
        
        query = " ".join(context.args)
        result = await bot_features.search_internet(query)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in search_command: {e}")
        await update.message.reply_text("❌ خطا در جستجو. لطفاً دوباره تلاش کنید.")

async def music_command(update: Update, context: CallbackContext):
    """Handle /music command"""
    try:
        if not context.args:
            await update.message.reply_text("🎵 لطفاً نام آهنگ را وارد کنید:\nمثال: /music آهنگ شاد")
            return
        
        query = " ".join(context.args)
        result = await bot_features.search_music(query)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in music_command: {e}")
        await update.message.reply_text("❌ خطا در جستجوی موسیقی. لطفاً دوباره تلاش کنید.")

# Weather and crypto
async def weather_command(update: Update, context: CallbackContext):
    """Handle /weather command"""
    try:
        if not context.args:
            await update.message.reply_text("🌦️ لطفاً نام شهر را وارد کنید:\nمثال: /weather تهران")
            return
        
        city = " ".join(context.args)
        result = await bot_features.get_weather(city)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in weather_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت آب و هوا. لطفاً دوباره تلاش کنید.")

async def crypto_command(update: Update, context: CallbackContext):
    """Handle /crypto command"""
    try:
        if not context.args:
            await update.message.reply_text("💰 لطفاً نام ارز را وارد کنید:\nمثال: /crypto btc\n\nارزهای موجود: btc, eth, bnb, ada, sol")
            return
        
        symbol = context.args[0]
        result = await bot_features.get_crypto_price(symbol)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in crypto_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت قیمت. لطفاً دوباره تلاش کنید.")

async def btc_command(update: Update, context: CallbackContext):
    """Handle /btc command"""
    try:
        result = await bot_features.get_crypto_price("btc")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in btc_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت قیمت بیت‌کوین.")

async def eth_command(update: Update, context: CallbackContext):
    """Handle /eth command"""
    try:
        result = await bot_features.get_crypto_price("eth")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in eth_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت قیمت اتریوم.")

# Entertainment commands
async def joke_command(update: Update, context: CallbackContext):
    """Handle /joke command"""
    try:
        await bot_features.tell_joke(update, context)
    except Exception as e:
        logger.error(f"Error in joke_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت جوک. لطفاً دوباره تلاش کنید.")

async def fact_command(update: Update, context: CallbackContext):
    """Handle /fact command"""
    try:
        await bot_features.tell_fact(update, context)
    except Exception as e:
        logger.error(f"Error in fact_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت اطلاعات جالب. لطفاً دوباره تلاش کنید.")

async def magic_8_ball_command(update: Update, context: CallbackContext):
    """Handle /8ball command"""
    try:
        await bot_features.magic_8_ball(update, context)
    except Exception as e:
        logger.error(f"Error in magic_8_ball_command: {e}")
        await update.message.reply_text("❌ خطا در توپ جادویی. لطفاً دوباره تلاش کنید.")

async def roll_dice_command(update: Update, context: CallbackContext):
    """Handle /roll_dice command"""
    try:
        await bot_features.roll_dice(update, context)
    except Exception as e:
        logger.error(f"Error in roll_dice_command: {e}")
        await update.message.reply_text("❌ خطا در تاس اندازی. لطفاً دوباره تلاش کنید.")

async def coin_flip_command(update: Update, context: CallbackContext):
    """Handle /coin_flip command"""
    try:
        await bot_features.coin_flip(update, context)
    except Exception as e:
        logger.error(f"Error in coin_flip_command: {e}")
        await update.message.reply_text("❌ خطا در شیر یا خط. لطفاً دوباره تلاش کنید.")

async def compliment_command(update: Update, context: CallbackContext):
    """Handle /compliment command"""
    try:
        await bot_features.give_compliment(update, context)
    except Exception as e:
        logger.error(f"Error in compliment_command: {e}")
        await update.message.reply_text("❌ خطا در تعریف کردن. لطفاً دوباره تلاش کنید.")

async def quote_command(update: Update, context: CallbackContext):
    """Handle /quote command"""
    try:
        await bot_features.random_quote(update, context)
    except Exception as e:
        logger.error(f"Error in quote_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت نقل قول. لطفاً دوباره تلاش کنید.")

async def poem_command(update: Update, context: CallbackContext):
    """Handle /poem command"""
    try:
        await bot_features.random_poem(update, context)
    except Exception as e:
        logger.error(f"Error in poem_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت شعر. لطفاً دوباره تلاش کنید.")

# Game commands
async def number_game_command(update: Update, context: CallbackContext):
    """Handle /number_game command"""
    try:
        await bot_features.number_game(update, context)
    except Exception as e:
        logger.error(f"Error in number_game_command: {e}")
        await update.message.reply_text("❌ خطا در شروع بازی حدس عدد. لطفاً دوباره تلاش کنید.")

async def rock_paper_scissors_command(update: Update, context: CallbackContext):
    """Handle /rock_paper_scissors command"""
    try:
        await bot_features.rock_paper_scissors(update, context)
    except Exception as e:
        logger.error(f"Error in rock_paper_scissors_command: {e}")
        await update.message.reply_text("❌ خطا در شروع بازی سنگ کاغذ قیچی. لطفاً دوباره تلاش کنید.")

async def memory_game_command(update: Update, context: CallbackContext):
    """Handle /memory_game command"""
    try:
        await bot_features.memory_game(update, context)
    except Exception as e:
        logger.error(f"Error in memory_game_command: {e}")
        await update.message.reply_text("❌ خطا در شروع بازی حافظه. لطفاً دوباره تلاش کنید.")

async def word_chain_command(update: Update, context: CallbackContext):
    """Handle /word_chain command"""
    try:
        await bot_features.word_chain(update, context)
    except Exception as e:
        logger.error(f"Error in word_chain_command: {e}")
        await update.message.reply_text("❌ خطا در شروع بازی زنجیره کلمات. لطفاً دوباره تلاش کنید.")

async def trivia_command(update: Update, context: CallbackContext):
    """Handle /trivia command"""
    try:
        await bot_features.trivia_quiz(update, context)
    except Exception as e:
        logger.error(f"Error in trivia_command: {e}")
        await update.message.reply_text("❌ خطا در شروع مسابقه اطلاعات عمومی. لطفاً دوباره تلاش کنید.")

async def game_command(update: Update, context: CallbackContext):
    """Handle /game command"""
    try:
        game_data = await bot_features.play_game("quiz")
        if isinstance(game_data, dict):
            await update.message.reply_text(
                f"🎮 **مسابقه!**\n\n❓ {game_data['question']}", 
                reply_markup=game_data['reply_markup']
            )
        else:
            await update.message.reply_text(game_data)
    except Exception as e:
        logger.error(f"Error in game_command: {e}")
        await update.message.reply_text("❌ خطا در شروع بازی. لطفاً دوباره تلاش کنید.")

async def quiz_command(update: Update, context: CallbackContext):
    """Handle /quiz command"""
    try:
        await game_command(update, context)
    except Exception as e:
        logger.error(f"Error in quiz_command: {e}")
        await update.message.reply_text("❌ خطا در شروع مسابقه. لطفاً دوباره تلاش کنید.")

async def riddle_command(update: Update, context: CallbackContext):
    """Handle /riddle command"""
    try:
        result = await bot_features.play_game("riddle")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in riddle_command: {e}")
        await update.message.reply_text("❌ خطا در شروع معما. لطفاً دوباره تلاش کنید.")

# Shopping commands
async def price_command(update: Update, context: CallbackContext):
    """Handle /price command"""
    try:
        if not context.args:
            await update.message.reply_text("🛍️ لطفاً نام کالا را وارد کنید:\nمثال: /price موبایل")
            return
        
        product_name = " ".join(context.args)
        result = await bot_features.search_products(product_name)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in price_command: {e}")
        await update.message.reply_text("❌ خطا در جستجوی کالا. لطفاً دوباره تلاش کنید.")

async def coupon_command(update: Update, context: CallbackContext):
    """Handle /coupon command"""
    try:
        category = context.args[0] if context.args else None
        result = await bot_features.get_coupons(category)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in coupon_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت کوپن‌ها. لطفاً دوباره تلاش کنید.")

# Utility commands
async def calc_command(update: Update, context: CallbackContext):
    """Handle /calc command"""
    try:
        if not context.args:
            await update.message.reply_text("🧮 لطفاً عبارت محاسبه را وارد کنید:\nمثال: /calc 2+2*3")
            return
        
        expression = " ".join(context.args)
        result = await bot_features.calculate(expression)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in calc_command: {e}")
        await update.message.reply_text("❌ خطا در محاسبه. لطفاً دوباره تلاش کنید.")

async def translate_command(update: Update, context: CallbackContext):
    """Handle /translate command"""
    try:
        if not context.args:
            await update.message.reply_text("🌐 لطفاً متن برای ترجمه را وارد کنید:\nمثال: /translate hello world")
            return
        
        text = " ".join(context.args)
        result = await bot_features.translate_text(text)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in translate_command: {e}")
        await update.message.reply_text("❌ خطا در ترجمه. لطفاً دوباره تلاش کنید.")

async def news_command(update: Update, context: CallbackContext):
    """Handle /news command"""
    try:
        category = context.args[0] if context.args else "general"
        result = await bot_features.get_news(category)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in news_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت اخبار. لطفاً دوباره تلاش کنید.")

async def technews_command(update: Update, context: CallbackContext):
    """Handle /technews command"""
    try:
        result = await bot_features.get_news("tech")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in technews_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت اخبار تکنولوژی. لطفاً دوباره تلاش کنید.")

async def time_command(update: Update, context: CallbackContext):
    """Handle /time command"""
    try:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await update.message.reply_text(f"⏰ **زمان فعلی:**\n\n📅 {current_time}")
    except Exception as e:
        logger.error(f"Error in time_command: {e}")
        await update.message.reply_text("❌ خطا در دریافت زمان. لطفاً دوباره تلاش کنید.")

# Sticker commands
async def sticker_command(update: Update, context: CallbackContext):
    """Handle /sticker command"""
    try:
        if not context.args:
            await update.message.reply_text("🎨 لطفاً متن استیکر را وارد کنید:\nمثال: /sticker سلام")
            return
        
        text = " ".join(context.args)
        sticker_img = await bot_features.create_sticker(text)
        
        if sticker_img:
            await update.message.reply_sticker(sticker=InputFile(sticker_img, filename="sticker.png"))
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        logger.error(f"Error in sticker_command: {e}")
        await update.message.reply_text("❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.")

async def meme_command(update: Update, context: CallbackContext):
    """Handle /meme command"""
    try:
        if not context.args:
            await update.message.reply_text("😄 لطفاً متن میم را وارد کنید:\nمثال: /meme وقتی امتحان سخته")
            return
        
        text = " ".join(context.args)
        meme_img = await bot_features.create_sticker(f"😄 {text}")
        
        if meme_img:
            await update.message.reply_photo(photo=InputFile(meme_img, filename="meme.png"))
        else:
            await update.message.reply_text("❌ خطا در ساخت میم. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        logger.error(f"Error in meme_command: {e}")
        await update.message.reply_text("❌ خطا در ساخت میم. لطفاً دوباره تلاش کنید.")

# Media commands
async def movie_command(update: Update, context: CallbackContext):
    """Handle /movie command"""
    try:
        if not context.args:
            await update.message.reply_text("🎬 لطفاً نام فیلم را وارد کنید:\nمثال: /movie فیلم ایرانی")
            return
        
        query = " ".join(context.args)
        result = await bot_features.search_internet(f"فیلم {query}")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in movie_command: {e}")
        await update.message.reply_text("❌ خطا در جستجوی فیلم. لطفاً دوباره تلاش کنید.")

async def series_command(update: Update, context: CallbackContext):
    """Handle /series command"""
    try:
        if not context.args:
            await update.message.reply_text("📺 لطفاً نام سریال را وارد کنید:\nمثال: /series سریال ایرانی")
            return
        
        query = " ".join(context.args)
        result = await bot_features.search_internet(f"سریال {query}")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in series_command: {e}")
        await update.message.reply_text("❌ خطا در جستجوی سریال. لطفاً دوباره تلاش کنید.")

async def download_command(update: Update, context: CallbackContext):
    """Handle /download command"""
    try:
        if not context.args:
            await update.message.reply_text("⬇️ لطفاً لینک دانلود را وارد کنید:\nمثال: /download https://example.com/music.mp3")
            return
        
        link = " ".join(context.args)
        await update.message.reply_text("⬇️ **در حال پردازش لینک دانلود...**\n\n" 
                                      "این قابلیت در حال توسعه است. لطفاً بعداً دوباره تلاش کنید.")
    except Exception as e:
        logger.error(f"Error in download_command: {e}")
        await update.message.reply_text("❌ خطا در دانلود. لطفاً دوباره تلاش کنید.")

async def image_command(update: Update, context: CallbackContext):
    """Handle /image command"""
    try:
        if not context.args:
            await update.message.reply_text("🖼️ لطفاً متن جستجوی تصویر را وارد کنید:\nمثال: /image گربه")
            return
        
        query = " ".join(context.args)
        result = await bot_features.search_internet(f"تصویر {query}")
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Error in image_command: {e}")
        await update.message.reply_text("❌ خطا در جستجوی تصویر. لطفاً دوباره تلاش کنید.")

# AI commands
async def ai_command(update: Update, context: CallbackContext):
    """Handle /ai command"""
    try:
        if not context.args:
            await update.message.reply_text("🤖 لطفاً سوال خود را وارد کنید:\nمثال: /ai پایتخت ایران کجاست؟")
            return
        
        question = " ".join(context.args)
        result = await bot_features.search_internet(question)
        await update.message.reply_text(f"🤖 **پاسخ هوش مصنوعی:**\n\n{result}")
    except Exception as e:
        logger.error(f"Error in ai_command: {e}")
        await update.message.reply_text("❌ خطا در پاسخ هوش مصنوعی. لطفاً دوباره تلاش کنید.")

async def chat_command(update: Update, context: CallbackContext):
    """Handle /chat command"""
    try:
        if not context.args:
            await update.message.reply_text("💬 لطفاً متن چت را وارد کنید:\nمثال: /chat سلام، حالت چطوره؟")
            return
        
        text = " ".join(context.args)
        result = await bot_features.search_internet(text)
        await update.message.reply_text(f"💬 **پاسخ چت:**\n\n{result}")
    except Exception as e:
        logger.error(f"Error in chat_command: {e}")
        await update.message.reply_text("❌ خطا در چت. لطفاً دوباره تلاش کنید.")

# Message handler
async def handle_message(update: Update, context: CallbackContext):
    """Handle text messages"""
    try:
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Handle number game guesses
        if (user_id in bot_features.game_states and 
            bot_features.game_states[user_id].get('game_type') == 'number' and
            message_text.isdigit()):
            
            guess = int(message_text)
            secret_number = bot_features.game_states[user_id]['number']
            bot_features.game_states[user_id]['attempts'] += 1
            attempts = bot_features.game_states[user_id]['attempts']
            
            if guess == secret_number:
                await update.message.reply_text(
                    f"🎉 **آفرین!** 🎉\n\n"
                    f"عدد {secret_number} بود!\n"
                    f"تعداد تلاش‌ها: {attempts}\n\n"
                    f"برای بازی جدید، /number_game را بزن!"
                )
                del bot_features.game_states[user_id]
            elif guess < secret_number:
                await update.message.reply_text(f"📈 عدد بزرگ‌تری انتخاب کن! (تلاش {attempts})")
            else:
                await update.message.reply_text(f"📉 عدد کوچک‌تری انتخاب کن! (تلاش {attempts})")
            return
        
        # Handle memory game input
        if (user_id in bot_features.game_states and 
            bot_features.game_states[user_id].get('game_type') == 'memory'):
            
            user_sequence = message_text.split()
            correct_sequence = bot_features.game_states[user_id]['memory_sequence']
            
            if user_sequence == correct_sequence:
                await update.message.reply_text(
                    f"🧠 **عالی!** 🧠\n\n"
                    f"دنباله رو به درستی به خاطر سپردی!\n\n"
                    f"برای بازی جدید، /memory_game را بزن!"
                )
                del bot_features.game_states[user_id]
            else:
                await update.message.reply_text(
                    f"❌ **اشتباه!** ❌\n\n"
                    f"دنباله صحیح: {' '.join(correct_sequence)}\n\n"
                    f"برای تلاش دوباره، /memory_game را بزن!"
                )
            return
        
        # Default response
        responses = [
            "🤔 جالب بود! ادامه بده...",
            "💡 فکری به سرم زد!",
            "🌟 می‌تونی بیشتر توضیح بدی؟",
            "🎯 حرف جالبی زدی!",
            "🔍 می‌خوای در موردش بیشتر بدونی؟",
        ]
        
        response = random.choice(responses)
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")

# Callback query handler
async def handle_callback_query(update: Update, context: CallbackContext):
    """Handle inline keyboard button presses"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Handle main menu buttons
        if data == "search":
            await query.edit_message_text("🔍 برای جستجو از دستور /search استفاده کن:\nمثال: /search موضوع مورد نظر")
        elif data == "music":
            await query.edit_message_text("🎵 برای جستجوی موسیقی از دستور /music استفاده کن:\nمثال: /music نام آهنگ")
        elif data == "movie":
            await query.edit_message_text("🎬 برای جستجوی فیلم از دستور /movie استفاده کن:\nمثال: /movie نام فیلم")
        elif data == "chat":
            await query.edit_message_text("🤖 برای چت با هوش مصنوعی از دستور /chat استفاده کن:\nمثال: /chat سلام")
        elif data == "weather":
            await query.edit_message_text("🌦️ برای آب و هوا از دستور /weather استفاده کن:\nمثال: /weather تهران")
        elif data == "crypto":
            await query.edit_message_text("💰 برای قیمت ارز از دستور /crypto استفاده کن:\nمثال: /crypto btc")
        elif data == "game":
            await query.edit_message_text("🎮 برای بازی از یکی از دستورات زیر استفاده کن:\n\n"
                                       "• /game - مسابقه عمومی\n"
                                       "• /number_game - حدس عدد\n"
                                       "• /rock_paper_scissors - سنگ کاغذ قیچی\n"
                                       "• /memory_game - بازی حافظه\n"
                                       "• /word_chain - زنجیره کلمات\n"
                                       "• /trivia - اطلاعات عمومی")
        elif data == "shopping":
            await query.edit_message_text("🛍️ برای خرید از دستورات زیر استفاده کن:\n\n"
                                       "• /price <کالا> - قیمت کالا\n"
                                       "• /coupon - کوپن‌های تخفیف")
        elif data == "fun":
            await query.edit_message_text("🃏 برای سرگرمی از دستورات زیر استفاده کن:\n\n"
                                       "• /joke - جوک\n"
                                       "• /fact - اطلاعات جالب\n"
                                       "• /8ball <سوال> - توپ جادویی\n"
                                       "• /roll_dice - تاس\n"
                                       "• /coin_flip - شیر یا خط\n"
                                       "• /compliment - تعریف\n"
                                       "• /quote - نقل قول\n"
                                       "• /poem - شعر")
        elif data == "new_game":
            await query.edit_message_text("🎲 **بازی جدید!** 🎲\n\n"
                                       "یکی از بازی‌ها رو انتخاب کن:\n"
                                       "• /number_game - حدس عدد\n"
                                       "• /rock_paper_scissors - سنگ کاغذ قیچی\n"
                                       "• /memory_game - بازی حافظه\n"
                                       "• /trivia - مسابقه اطلاعات عمومی\n"
                                       "• /word_chain - زنجیره کلمات")
        
        # Handle quiz answers
        elif data.startswith("quiz_answer_"):
            try:
                answer_num = int(data.split("_")[2])
                await query.edit_message_text(f"✅ جواب شما ثبت شد: {answer_num + 1}")
            except:
                await query.edit_message_text("❌ خطا در ثبت جواب!")
        
        # Handle rock paper scissors
        elif data.startswith("rps_"):
            user_choice = data.split("_")[1]
            choices = {"rock": "🪨 سنگ", "paper": "📄 کاغذ", "scissors": "✂️ قیچی"}
            computer_choice = random.choice(list(choices.keys()))
            
            user_text = choices[user_choice]
            computer_text = choices[computer_choice]
            
            # Determine winner
            if user_choice == computer_choice:
                result = "🤝 مساوی!"
            elif (
                (user_choice == "rock" and computer_choice == "scissors") or
                (user_choice == "paper" and computer_choice == "rock") or
                (user_choice == "scissors" and computer_choice == "paper")
            ):
                result = "🎉 تو بردی!"
            else:
                result = "😢 کامپیوتر برد!"
            
            await query.edit_message_text(
                f"🎮 **سنگ، کاغذ، قیچی**\n\n"
                f"تو: {user_text}\n"
                f"کامپیوتر: {computer_text}\n\n"
                f"**{result}**\n\n"
                f"برای بازی دوباره: /rock_paper_scissors"
            )
        
        # Handle trivia answers
        elif data.startswith("trivia_"):
            try:
                user_id = update.effective_user.id
                answer_num = int(data.split("_")[1])
                
                if (user_id in bot_features.game_states and
                    'trivia_answer' in bot_features.game_states[user_id]):
                    
                    correct_answer = bot_features.game_states[user_id]['trivia_answer']
                    explanation = bot_features.game_states[user_id]['trivia_explanation']
                    
                    if answer_num == correct_answer:
                        result_text = "✅ **آفرین! پاسخ درسته!**"
                    else:
                        result_text = "❌ **اشتباه!**"
                    
                    await query.edit_message_text(
                        f"🧠 **مسابقه اطلاعات عمومی**\n\n"
                        f"{result_text}\n\n"
                        f"📝 {explanation}\n\n"
                        f"برای سوال جدید: /trivia"
                    )
                    
                    # Clean up game state
                    del bot_features.game_states[user_id]
                else:
                    await query.edit_message_text("⚠️ بازی پیدا نشد! لطفاً دوباره با /trivia شروع کن.")
            except Exception as e:
                await query.edit_message_text("❌ خطا در بررسی جواب! لطفاً دوباره تلاش کنید.")
        
        else:
            await query.edit_message_text("❌ دکمه‌ای یافت نشد!")
        
    except Exception as e:
        logger.error(f"Error in handle_callback_query: {e}")
        try:
            await update.callback_query.answer("خطایی رخ داد!")
        except:
            pass

# Sticker handler
async def handle_sticker(update: Update, context: CallbackContext):
    """Handle sticker messages"""
    try:
        sticker_responses = [
            "😄 استیکر جالبی بود!",
            "🎨 عالیه! از کی آوردی؟",
            "😂 خخخخ، باحال بود!",
            "👌 جیده!",
            "🔥 آتیشین استیکر!",
        ]
        
        response = random.choice(sticker_responses)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in handle_sticker: {e}")
</full-file-rewrite>