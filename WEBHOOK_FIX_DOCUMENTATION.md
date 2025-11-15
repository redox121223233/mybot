# رفع خطای Webhook در ربات تلگرامی

## مشکل اصلی
خطای `'NoneType' object has no attribute 'application'` در وبهوک ربات تلگرامی

## دلیل مشکل
- متغیر `bot` در ابتدا با `None` مقداردهی شده بود
- در تابع `webhook()` تلاش می‌شد به `bot.application.bot` دسترسی پیدا شود
- در محیط Vercel، تابع `webhook()` قبل از `main()` اجرا می‌شد و `bot` هنوز `None` بود

## راه حل اجرا شده

### 1. ایجاد تابع `initialize_bot()`
```python
def initialize_bot():
    """Initialize bot application"""
    global bot, application
    
    # Return existing bot if already initialized
    if application is not None and bot is not None:
        return bot
        
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found")
        return None
    
    application = Application.builder().token(bot_token).build()
    # ... add handlers ...
    bot = type('Bot', (), {'application': application})()
    return bot
```

### 2. اصلاح تابع `webhook()`
```python
@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook handler - FIXED VERSION"""
    try:
        # Initialize bot if not already done
        current_bot = initialize_bot()
        if current_bot is None:
            logger.error("Bot initialization failed")
            return "Bot initialization failed", 500
            
        if request.is_json:
            update_data = request.get_json()
            update = Update.de_json(update_data, current_bot.application.bot)
            asyncio.run(current_bot.application.process_update(update))
            return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return f"Webhook error: {str(e)}", 500
```

## مزایای راه حل
1. **Initialization امن**: قبل از هر درخواست webhook، بابت حتماً initialize می‌شود
2. **جلوگیری از خطای NoneType**: چک می‌شود که bot مقدار معتبر داشته باشد
3. **عدم تکرار کد**: کد initialization فقط در یکجا نوشته شده
4. **مدیریت بهتر خطا**: خطاهای initialization به درستی handled می‌شوند

## تست و استقرار
- تغییرات در برچ `fix-vercel-type-error` کامیت و پوش شده‌اند
- کد آماده deploy در Vercel است
- خطای webhook باید برطرف شده باشد

## فایل‌های تغییر یافته
- `api/index.py` - فایل اصلی با اصلاحات
- `api/index_fixed.py` - نسخه پشتیبان از اصلاحات