from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from bot_features import bot_features
from security import security_manager
from user_manager import user_manager
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Update user info and track command usage
    user_manager.update_user(update)
    user_manager.increment_command_usage(update.effective_user.id, "start")
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_features.help_command(update, context)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Update user info and track command usage
    user_manager.update_user(update)
    user_manager.increment_command_usage(update.effective_user.id, "search")
    
    if not context.args:
        await update.message.reply_text("❌ لطفاً عبارت مورد نظر برای جستجو را وارد کنید.\nمثال: /search تلگرام ربات")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text("🔍 در حال جستجو...")
    result = await bot_features.search_internet(query)
    await update.message.reply_text(result)

async def music_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام آهنگ یا هنرمند را وارد کنید.\nمثال: /music شاد")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text("🎵 در حال جستجوی موسیقی...")
    result = await bot_features.search_music(query)
    await update.message.reply_text(result)

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام شهر را وارد کنید.\nمثال: /weather تهران")
        return
    
    city = " ".join(context.args)
    await update.message.reply_text("🌤️ در حال دریافت اطلاعات آب و هوا...")
    result = await bot_features.get_weather(city)
    await update.message.reply_text(result)

async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام ارز دیجیتال را وارد کنید.\nمثال: /crypto btc")
        return
    
    symbol = context.args[0]
    await update.message.reply_text("💰 در حال دریافت قیمت...")
    result = await bot_features.get_crypto_price(symbol)
    await update.message.reply_text(result)

async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 در حال دریافت قیمت بیت‌کوین...")
    result = await bot_features.get_crypto_price("btc")
    await update.message.reply_text(result)

async def eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 در حال دریافت قیمت اتریوم...")
    result = await bot_features.get_crypto_price("eth")
    await update.message.reply_text(result)

async def sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 در حال آماده کردن بازی...")
    game_data = await bot_features.play_game("quiz")
    
    if isinstance(game_data, dict):
        keyboard = [
            [InlineKeyboardButton(option, callback_data=f"quiz_answer_{i}")]
            for i, option in enumerate(["تهران", "۴", "آران"])  # موقت استفاده از گزینه‌های ثابت
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(game_data["question"], reply_markup=reply_markup)
    else:
        await update.message.reply_text(game_data)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_command(update, context)

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام کالا را وارد کنید.\nمثال: /price گوشی موبایل")
        return
    
    product = " ".join(context.args)
    await update.message.reply_text("🛍️ در حال جستجوی قیمت...")
    result = await bot_features.search_products(product)
    await update.message.reply_text(result)

async def coupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎫 در حال دریافت کپن‌ها...")
    result = await bot_features.get_coupons()
    await update.message.reply_text(result)

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📰 در حال دریافت اخبار...")
    result = await bot_features.get_news("general")
    await update.message.reply_text(result)

async def technews_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💻 در حال دریافت اخبار تکنولوژی...")
    result = await bot_features.get_news("tech")
    await update.message.reply_text(result)

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"⏰ زمان فعلی:\n📅 {time_str}")

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً عبارت محاسباتی را وارد کنید.\nمثال: /calc 2+2*3")
        return
    
    expression = " ".join(context.args)
    result = await bot_features.calculate(expression)
    await update.message.reply_text(result)

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً متن مورد نظر برای ترجمه را وارد کنید.\nمثال: /translate hello world")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text("🌍 در حال ترجمه...")
    result = await bot_features.translate_text(text)
    await update.message.reply_text(result)

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً سوال خود را وارد کنید.\nمثال: /ai آب و هوا چطور است؟")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤖 در حال پردازش سوال شما...")
    
    # شبیه‌سازی پاسخ AI
    response = f"پاسخ هوش مصنوعی به سوال شما:\n\n❓ {question}\n\n🤖 این یک پاسخ شبیه‌سازی شده است. در نسخه واقعی، اینجا پاسخ از سرویس هوش مصنوعی دریافت می‌شود."
    await update.message.reply_text(response)

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً پیام خود را برای چت وارد کنید.\nمثال: /chat سلام، حالت چطوره؟")
        return
    
    message = " ".join(context.args)
    await update.message.reply_text("🤖 در حال پاسخگویی...")
    
    # شبیه‌سازی پاسخ چت
    response = f"پاسخ ربات:\n\n👤 شما: {message}\n\n🤖 ربات: سلام! من یک ربات چندمنظوره هستم و می‌توانم به سوالات شما پاسخ دهم. چطور می‌توانم کمکتان کنم؟"
    await update.message.reply_text(response)

async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام فیلم را وارد کنید.\nمثال: /movie اینتراستلار")
        return
    
    movie = " ".join(context.args)
    await update.message.reply_text("🎬 در حال جستجوی فیلم...")
    
    # شبیه‌سازی جستجوی فیلم
    result = f"🎬 نتایج جستجو برای '{movie}':\n\n🎥️ {movie} (2023)\n⭐ امتیاز: 8.5/10\n📝 خلاصه: این یک فیلم عالی است...\n\n🔗 برای دانلود و مشاهده به لینک زیر مراجعه کنید:\nhttps://movies.example.com/{movie.replace(' ', '-')}"
    await update.message.reply_text(result)

async def series_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً نام سریال را وارد کنید.\nمثال: /series بازی تاج‌وتخت")
        return
    
    series = " ".join(context.args)
    await update.message.reply_text("📺 در حال جستجوی سریال...")
    
    # شبیه‌سازی جستجوی سریال
    result = f"📺 نتایج جستجو برای '{series}':\n\n🎭 {series} (فصل 1-5)\n⭐ امتیاز: 9.2/10\n📝 خلاصه: این یک سریال فوق‌العاده است...\n\n🔗 برای دانلود و مشاهده به لینک زیر مراجعه کنید:\nhttps://series.example.com/{series.replace(' ', '-')}"
    await update.message.reply_text(result)

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً عبارت مورد نظر برای جستجوی تصویر را وارد کنید.\nمثال: /image گربه")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text("🖼️ در حال جستجوی تصویر...")
    
    # شبیه‌سازی جستجوی تصویر
    result = f"🖼️ تصاویر یافت شده برای '{query}':\n\n📸 تصویر 1: https://images.example.com/{query.replace(' ', '-')}-1.jpg\n📸 تصویر 2: https://images.example.com/{query.replace(' ', '-')}-2.jpg\n📸 تصویر 3: https://images.example.com/{query.replace(' ', '-')}-3.jpg"
    await update.message.reply_text(result)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً لینک دانلود را وارد کنید.\nمثال: /download https://music.example.com/song.mp3")
        return
    
    url = context.args[0]
    await update.message.reply_text("⬇️ در حال آماده سازی دانلود...")
    
    # شبیه‌سازی دانلود
    result = f"⬇️ لینک دانلود آماده شد:\n\n🔗 {url}\n\n📝 برای دانلود روی لینک بالا کلیک کنید."
    await update.message.reply_text(result)

async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ لطفاً متن میم را وارد کنید.\nمثال: /meme این هم از زندگیم")
        return
    
    text = " ".join(context.args)
    await update.message.reply_text("😄 در حال ساخت میم...")
    
    # شبیه‌سازی ساخت میم
    result = f"😄 میم شما ساخته شد!\n\n💬 متن: {text}\n\n🖼️ برای دریافت تصویر میم، اینجا کلیک کنید:\nhttps://meme.example.com/generate?text={text.replace(' ', '%20')}"
    await update.message.reply_text(result)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # دکمه‌های اصلی
    if data == "search":
        await query.message.reply_text("🔍 برای جستجو از دستور /search استفاده کنید:\nمثال: /search تلگرام ربات")
    elif data == "music":
        await query.message.reply_text("🎵 برای جستجوی موسیقی از دستور /music استفاده کنید:\nمثال: /music آهنگ شاد")
    elif data == "movie":
        await query.message.reply_text("🎬 برای جستجوی فیلم از دستور /movie استفاده کنید:\nمثال: /movie اینتراستلار")
    elif data == "chat":
        await query.message.reply_text("🤖 برای چت با AI از دستور /chat استفاده کنید:\nمثال: /chat سلام، حالت چطوره؟")
    elif data == "weather":
        await query.message.reply_text("🌤️ برای دریافت آب و هوا از دستور /weather استفاده کنید:\nمثال: /weather تهران")
    elif data == "crypto":
        await query.message.reply_text("💰 برای دریافت قیمت ارز از دستور /crypto استفاده کنید:\nمثال: /crypto btc")
    elif data == "game":
        await game_command(update, context)
    elif data == "shopping":
        await query.message.reply_text("🛍️ برای جستجوی کالا از دستور /price استفاده کنید:\nمثال: /price گوشی موبایل")
    
    # دکمه‌های ادمین
    elif data == "admin_users":
        if security_manager.is_admin(query.from_user.id):
            top_users = user_manager.get_top_users()
            text = "👥 **کاربران فعال**\n\n"
            for i, user in enumerate(top_users, 1):
                text += f"{i}. {user['name']} (@{user['username']}) - {user['message_count']} پیام\n"
            await query.message.reply_text(text)
    elif data == "admin_security":
        if security_manager.is_admin(query.from_user.id):
            await query.message.reply_text("🔒 **امنیت**\n\n• سیستم امنیتی فعال است\n• محدودیت نرخ در حال کار است\n• کاربران مسدود: 0 نفر")
    elif data == "admin_stats":
        if security_manager.is_admin(query.from_user.id):
            stats = user_manager.get_bot_statistics()
            text = f"📊 **آمار دقیق**\n\n"
            text += f"کاربران کل: {stats['users']['total']}\n"
            text += f"فعال امروز: {stats['users']['active_today']}\n"
            text += f"پیام‌ها: {stats['usage']['total_messages']}\n"
            text += f"جستجوها: {stats['usage']['total_searches']}"
            await query.message.reply_text(text)
    
    # دکمه‌های تنظیمات
    elif data == "setting_notifications":
        user_id = query.from_user.id
        user_data = user_manager.get_user(user_id)
        current = user_data["settings"]["notifications"]
        user_manager.set_user_setting(user_id, "notifications", not current)
        status = "✅ روشن" if not current else "❌ خاموش"
        await query.message.reply_text(f"🔔 اعلان‌ها {status} شد.")
    elif data == "setting_language":
        await query.message.reply_text("🌐 **انتخاب زبان**\n\nدر حال حاضر فقط فارسی پشتیبانی می‌شود.")
    elif data == "setting_theme":
        user_id = query.from_user.id
        user_data = user_manager.get_user(user_id)
        current = user_data["settings"]["theme"]
        new_theme = "dark" if current == "light" else "light"
        user_manager.set_user_setting(user_id, "theme", new_theme)
        await query.message.reply_text(f"🎨 پوسته به {new_theme} تغییر کرد.")
    
    # پاسخ کوییز
    elif data.startswith("quiz_answer_"):
        answer_index = int(data.split("_")[-1])
        correct_answers = [0, 1, 2]  # شماره پاسخ صحیح
        if answer_index in correct_answers:
            await query.message.reply_text("✅ پاسخ صحیح! آفرین!")
        else:
            await query.message.reply_text("❌ پاسخ اشتباه! دوباره تلاش کنید.")
    else:
        await query.message.reply_text("❌ دکمه نامعتبر است.")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin command"""
    user_id = update.effective_user.id
    
    if not security_manager.is_admin(user_id):
        await update.message.reply_text("❌ فقط ادمین می‌تواند از این دستور استفاده کند.")
        return
    
    stats = user_manager.get_bot_statistics()
    
    admin_text = f"""
🔧 **پنل مدیریت ادمین** 🔧

📊 **آمار کلی:**
• تعداد کاربران: {stats['users']['total']}
• کاربران ویژه: {stats['users']['premium']}
• فعال امروز: {stats['users']['active_today']}

📈 **آمار استفاده:**
• کل پیام‌ها: {stats['usage']['total_messages']}
• جستجوها: {stats['usage']['total_searches']}
• استیکرهای ساخته شده: {stats['usage']['total_stickers_created']}

👥 **کاربران فعال:**
"""
    
    for i, user in enumerate(stats['performance']['most_active_users'], 1):
        admin_text += f"{i}. {user['name']} ({user['message_count']} پیام)\n"
    
    keyboard = [
        [InlineKeyboardButton("👥 کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("🔒 امنیت", callback_data="admin_security")],
        [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(admin_text, reply_markup=reply_markup)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user statistics command"""
    user_id = update.effective_user.id
    stats = user_manager.get_user_stats(user_id)
    
    stats_text = f"""
📊 **آمار شما** 📊

👤 **اطلاعات:**
• نام: {stats['basic_info']['name']}
• یوزرنیم: @{stats['basic_info']['username']}
• کاربر ویژه: {'✅' if stats['basic_info']['is_premium'] else '❌'}

📅 **فعالیت:**
• تاریخ عضویت: {stats['activity']['joined_at'].split('T')[0]}
• آخرین فعالیت: {stats['activity']['last_active'].split('T')[0]}
• روزهای فعال: {stats['activity']['days_active']}
• کل پیام‌ها: {stats['activity']['message_count']}

🎯 **استفاده:**
• جستجو: {stats['usage']['search_count']} بار
• موسیقی: {stats['usage']['music_count']} بار
• استیکر: {stats['usage']['sticker_count']} بار
• بازی: {stats['usage']['game_count']} بار

⚙️ **دستورات استفاده شده:** {len(stats['commands_used'])} دستور
"""
    
    await update.message.reply_text(stats_text)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings command"""
    user_id = update.effective_user.id
    user_data = user_manager.get_user(user_id)
    settings = user_data["settings"]
    
    keyboard = [
        [InlineKeyboardButton("🔔 اعلان‌ها", callback_data="setting_notifications")],
        [InlineKeyboardButton("🌐 زبان", callback_data="setting_language")],
        [InlineKeyboardButton("🎨 پوسته", callback_data="setting_theme")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = f"""
⚙️ **تنظیمات شما** ⚙️

🔔 اعلان‌ها: {'✅ روشن' if settings['notifications'] else '❌ خاموش'}
🌐 زبان: {settings['language'].upper()}
🎨 پوسته: {settings['theme']}

برای تغییر تنظیمات، روی دکمه‌ها کلیک کنید.
"""
    
    await update.message.reply_text(settings_text, reply_markup=reply_markup)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile command"""
    user_id = update.effective_user.id
    user_data = user_manager.get_user(user_id)
    stats = user_manager.get_user_stats(user_id)
    
    profile_text = f"""
👤 **پروفایل کاربری** 👤

📝 **اطلاعات básicas:**
• نام: {stats['basic_info']['name']}
• یوزرنیم: @{stats['basic_info']['username'] or 'ندارد'}
• ID: {user_id}
• نوع کاربر: {'🌟 ویژه' if stats['basic_info']['is_premium'] else '👤 معمولی'}

📈 **سطح فعالیت:**
• امتیاز کل: {stats['activity']['message_count'] * 10}
• سطح: {'🏆 پلاتین' if stats['activity']['message_count'] > 100 else '🥇 طلا' if stats['activity']['message_count'] > 50 else '🥈 نقره' if stats['activity']['message_count'] > 20 else '🥉 برنز'}
• رتبه: در بین کاربران فعال

🎯 **دستورات محبوب:**
{', '.join(stats['commands_used'][:5]) if stats['commands_used'] else 'هنوز دستوری استفاده نکرده‌اید'}

💡 **نکته:** با استفاده بیشتر از ربات، سطح خود را بالا ببرید!
"""
    
    await update.message.reply_text(profile_text)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ دستور نامعتبر است! برای دیدن لیست دستورات، /help را وارد کنید.")

def setup_handlers(application):
    # دستورHandlers
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
    
    # دستورات جدید
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("profile", profile_command))
    
    # Callback Handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Unknown Handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown))