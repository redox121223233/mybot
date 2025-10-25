from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot_features import bot_features
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: CallbackContext):
    await bot_features.help_command(update, context)

async def search_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً عبارت مورد نظر برای جستجو را وارد کنید.\nمثال: /search تلگرام ربات")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text("🔍 در حال جستجو...")
    result = await bot_features.search_internet(query)
    await update.message.reply_text(result)

async def music_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام آهنگ یا هنرمند را وارد کنید.\nمثال: /music شاد")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text("🎵 در حال جستجوی موسیقی...")
    result = await bot_features.search_music(query)
    await update.message.reply_text(result)

async def weather_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام شهر را وارد کنید.\nمثال: /weather تهران")
        return
    
    city = " ".join(context.args)
    await update.message.reply_text("🌤️ در حال دریافت اطلاعات آب و هوا...")
    result = await bot_features.get_weather(city)
    await update.message.reply_text(result)

async def crypto_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام ارز دیجیتال را وارد کنید.\nمثال: /crypto btc")
        return
    
    symbol = context.args[0]
    await update.message.reply_text("💰 در حال دریافت قیمت...")
    result = await bot_features.get_crypto_price(symbol)
    await update.message.reply_text(result)

async def btc_command(update: Update, context: CallbackContext):
    await update.message.reply_text("💰 در حال دریافت قیمت بیت‌کوین...")
    result = await bot_features.get_crypto_price("btc")
    await update.message.reply_text(result)

async def eth_command(update: Update, context: CallbackContext):
    await update.message.reply_text("💰 در حال دریافت قیمت اتریوم...")
    result = await bot_features.get_crypto_price("eth")
    await update.message.reply_text(result)

async def sticker_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً متن استیکر را وارد کنید.\nمثال: /sticker سلام")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text("🎨 در حال ساخت استیکر...")
    
    sticker_bytes = await bot_features.create_sticker(text)
    if sticker_bytes:
        await update.message.reply_sticker(sticker=sticker_bytes)
    else:
        await update.message.reply_text("❌ خطا در ساخت استیکر!")

async def game_command(update: Update, context: CallbackContext):
    await update.message.reply_text("🎮 در حال آماده کردن بازی...")
    game_data = await bot_features.play_game("quiz")
    
    if isinstance(game_data, dict):
        keyboard = [
            [InlineKeyboardButton(option, callback_data=f"quiz_answer_{i}")]
            for i, option in enumerate(["تهران", "۴", "آرام"])  #临时使用固定选项
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(game_data["question"], reply_markup=reply_markup)
    else:
        await update.message.reply_text(game_data)

async def quiz_command(update: Update, context: CallbackContext):
    await game_command(update, context)

async def price_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام کالا را وارد کنید.\nمثال: /price گوشی موبایل")
        return
    
    product = " ".join(context.args)
    await update.message.reply_text("🛍️ در حال جستجوی قیمت...")
    result = await bot_features.search_products(product)
    await update.message.reply_text(result)

async def coupon_command(update: Update, context: CallbackContext):
    await update.message.reply_text("🎫 در حال دریافت کوپن‌ها...")
    result = await bot_features.get_coupons()
    await update.message.reply_text(result)

async def news_command(update: Update, context: CallbackContext):
    await update.message.reply_text("📰 در حال دریافت اخبار...")
    result = await bot_features.get_news("general")
    await update.message.reply_text(result)

async def technews_command(update: Update, context: CallbackContext):
    await update.message.reply_text("💻 در حال دریافت اخبار تکنولوژی...")
    result = await bot_features.get_news("tech")
    await update.message.reply_text(result)

async def time_command(update: Update, context: CallbackContext):
    from datetime import datetime
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"⏰ زمان فعلی:\n📅 {time_str}")

async def calc_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً عبارت محاسباتی را وارد کنید.\nمثال: /calc 2+2*3")
        return
    
    expression = " ".join(context.args)
    result = await bot_features.calculate(expression)
    await update.message.reply_text(result)

async def translate_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً متن مورد نظر برای ترجمه را وارد کنید.\nمثال: /translate hello world")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text("🌐 در حال ترجمه...")
    result = await bot_features.translate_text(text)
    await update.message.reply_text(result)

async def ai_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً سوال خود را وارد کنید.\nمثال: /ai آب و هوا چطور است؟")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤖 در حال پردازش سوال شما...")
    
    # شبیه‌سازی پاسخ AI
    response = f"پاسخ هوش مصنوعی به سوال شما:\n\n❓ {question}\n\n🤖 این یک پاسخ شبیه‌سازی شده است. در نسخه واقعی، اینجا پاسخ از سرویس هوش مصنوعی دریافت می‌شود."
    await update.message.reply_text(response)

async def chat_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً پیام خود را برای چت وارد کنید.\nمثال: /chat سلام، حالت چطوره؟")
        return
    
    message = " ".join(context.args)
    await update.message.reply_text("🤖 در حال پاسخگویی...")
    
    # شبیه‌سازی پاسخ چت
    response = f"پاسخ ربات:\n\n👤 شما: {message}\n\n🤖 ربات: سلام! من یک ربات چندمنظوره هستم و می‌توانم به سوالات شما پاسخ دهم. چطور می‌توانم کمکتان کنم؟"
    await update.message.reply_text(response)

async def movie_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام فیلم را وارد کنید.\nمثال: /movie اینتراستلار")
        return
    
    movie = " ".join(context.args)
    await update.message.reply_text("🎬 در حال جستجوی فیلم...")
    
    # شبیه‌سازی جستجوی فیلم
    result = f"🎬 نتایج جستجو برای '{movie}':\n\n📽️ {movie} (2023)\n⭐ امتیاز: 8.5/10\n📝 خلاصه: این یک فیلم عالی است...\n\n🔗 برای دانلود و مشاهده به لینک زیر مراجعه کنید:\nhttps://movies.example.com/{movie.replace(' ', '-')}"
    await update.message.reply_text(result)

async def series_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام سریال را وارد کنید.\nمثال: /series بازی تاج‌وتخت")
        return
    
    series = " ".join(context.args)
    await update.message.reply_text("📺 در حال جستجوی سریال...")
    
    # شبیه‌سازی جستجوی سریال
    result = f"📺 نتایج جستجو برای '{series}':\n\n🎭 {series} (فصل 1-5)\n⭐ امتیاز: 9.2/10\n📝 خلاصه: این یک سریال فوق‌العاده است...\n\n🔗 برای دانلود و مشاهده به لینک زیر مراجعه کنید:\nhttps://series.example.com/{series.replace(' ', '-')}"
    await update.message.reply_text(result)

async def image_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً عبارت مورد نظر برای جستجوی تصویر را وارد کنید.\nمثال: /image گربه")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text("🖼️ در حال جستجوی تصویر...")
    
    # شبیه‌سازی جستجوی تصویر
    result = f"🖼️ تصاویر یافت شده برای '{query}':\n\n📸 تصویر 1: https://images.example.com/{query.replace(' ', '-')}-1.jpg\n📸 تصویر 2: https://images.example.com/{query.replace(' ', '-')}-2.jpg\n📸 تصویر 3: https://images.example.com/{query.replace(' ', '-')}-3.jpg"
    await update.message.reply_text(result)

async def download_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً لینک دانلود را وارد کنید.\nمثال: /download https://music.example.com/song.mp3")
        return
    
    url = context.args[0]
    await update.message.reply_text("⬇️ در حال آماده سازی دانلود...")
    
    # شبیه‌سازی دانلود
    result = f"⬇️ لینک دانلود آماده شد:\n\n🔗 {url}\n\n📝 برای دانلود روی لینک بالا کلیک کنید."
    await update.message.reply_text(result)

async def meme_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ لطفاً متن میم را وارد کنید.\nمثال: /meme این هم از زندگی")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text("😄 در حال ساخت میم...")
    
    # شبیه‌سازی ساخت میم
    result = f"😄 میم شما ساخته شد!\n\n💬 متن: {text}\n\n🖼️ برای دریافت تصویر میم، اینجا کلیک کنید:\nhttps://meme.example.com/generate?text={text.replace(' ', '%20')}"
    await update.message.reply_text(result)

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "search":
        await query.message.reply_text("🔍 برای جستجو از دستور /search استفاده کنید:\nمثال: /search تلگرام ربات")
    elif data == "music":
        await query.message.reply_text("🎵 برای جستجوی موسیقی از دستور /music استفاده کنید:\nمثال: /music آهنگ شاد")
    elif data == "movie":
        await query.message.reply_text("🎬 برای جستجوی فیلم از دستور /movie استفاده کنید:\nمثال: /movie اینتراستلار")
    elif data == "chat":
        await query.message.reply_text("🤖 برای چت با AI از دستور /chat استفاده کنید:\nمثال: /chat سلام، حالت چطوره؟")
    elif data == "weather":
        await query.message.reply_text("🌦️ برای دریافت آب و هوا از دستور /weather استفاده کنید:\nمثال: /weather تهران")
    elif data == "crypto":
        await query.message.reply_text("💰 برای دریافت قیمت ارز از دستور /crypto استفاده کنید:\nمثال: /crypto btc")
    elif data == "game":
        await game_command(update, context)
    elif data == "shopping":
        await query.message.reply_text("🛍️ برای جستجوی کالا از دستور /price استفاده کنید:\nمثال: /price گوشی موبایل")
    elif data.startswith("quiz_answer_"):
        answer_index = int(data.split("_")[-1])
        correct_answers = [0, 1, 2]  #答案索引
        if answer_index in correct_answers:
            await query.message.reply_text("✅ پاسخ صحیح! آفرین!")
        else:
            await query.message.reply_text("❌ پاسخ اشتباه! دوباره تلاش کنید.")
    else:
        await query.message.reply_text("❌ دکمه نامعتبر است.")

async def unknown(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ دستور نامعتبر است! برای دیدن لیست دستورات، /help را وارد کنید.")

def setup_handlers(application):
    # دکماندHandlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("music", music_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("crypto", crypto_command))
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("eth", eth_command))
    application.add_handler(CommandHandler("sticker", sticker_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("coupon", coupon_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("technews", technews_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("calc", calc_command))
    application.add_handler(CommandHandler("translate", translate_command))
    application.add_handler(CommandHandler("ai", ai_command))
    application.add_handler(CommandHandler("chat", chat_command))
    application.add_handler(CommandHandler("movie", movie_command))
    application.add_handler(CommandHandler("series", series_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CommandHandler("meme", meme_command))
    
    # Callback Handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Unknown Handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown))