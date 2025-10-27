import logging
import asyncio
from telegram import Update, InputFile
from telegram.ext import CallbackContext
from bot import bot_features

logger = logging.getLogger(__name__)

# متغیرهای سراسری برای حالت کاربر
user_states = {}

async def setup_handlers(application):
    """تنظیم handlerها برای ربات"""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
    
    # دستورات اصلی
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sticker", sticker_command))
    application.add_handler(CommandHandler("guess", guess_command))
    application.add_handler(CommandHandler("rps", rps_command))
    application.add_handler(CommandHandler("word", word_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("customsticker", customsticker_command))
    
    # handlerهای callback و پیام‌ها
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def start_command(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    await bot_features.start_command(update, context)
    user_id = update.effective_user.id
    user_states[user_id] = {"mode": "main"}

async def help_command(update: Update, context: CallbackContext) -> None:
    """دستور /help"""
    await bot_features.help_command(update, context)

async def sticker_command(update: Update, context: CallbackContext) -> None:
    """دستور /sticker برای ساخت استیکر"""
    if context.args:
        text = ' '.join(context.args)
        sticker_bytes = await bot_features.create_sticker(text)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.png")
            )
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
    else:
        await update.message.reply_text("❌ لطفاً متن استیکر را وارد کنید:\nمثال: /sticker سلام دنیا")

async def guess_command(update: Update, context: CallbackContext) -> None:
    """شروع بازی حدس عدد"""
    game_data = await bot_features.guess_number_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def rps_command(update: Update, context: CallbackContext) -> None:
    """شروع بازی سنگ کاغذ قیچی"""
    game_data = await bot_features.rock_paper_scissors_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def word_command(update: Update, context: CallbackContext) -> None:
    """شروع بازی کلمات"""
    game_data = await bot_features.word_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def memory_command(update: Update, context: CallbackContext) -> None:
    """شروع بازی حافظه"""
    game_data = await bot_features.memory_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def random_command(update: Update, context: CallbackContext) -> None:
    """بازی تصادفی"""
    game_data = await bot_features.random_game()
    await update.message.reply_text(
        game_data["message"],
        reply_markup=game_data["reply_markup"]
    )

async def customsticker_command(update: Update, context: CallbackContext) -> None:
    """منوی استیکر ساز سفارشی"""
    menu_data = await bot_features.custom_sticker_menu()
    await update.message.reply_text(
        menu_data["message"],
        reply_markup=menu_data["reply_markup"]
    )

async def button_callback(update: Update, context: CallbackContext) -> None:
    """مدیریت کلیک روی دکمه‌ها"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "back_to_main":
        await bot_features.start_command(update, context)
        return
    
    elif callback_data == "guess_number":
        game_data = await bot_features.guess_number_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "guess_prompt":
        keyboard = [[
            InlineKeyboardButton("ارسال عدد", callback_data="guess_send_number")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔢 لطفاً عدد مورد نظر خود را به صورت پیام متنی ارسال کنید (بین 1 تا 100):",
            reply_markup=reply_markup
        )
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["waiting_for_guess"] = True
    
    elif callback_data == "guess_hint":
        if 'guess_number' in bot_features.user_data:
            number = bot_features.user_data['guess_number']
            hint = "بزرگتر از 50" if number > 50 else "کوچکتر از 50"
            await query.edit_message_text(
                f"💡 **راهنمایی:** عدد {hint} است!\n\nدوباره تلاش کنید:",
                reply_markup=query.message.reply_markup
            )
    
    elif callback_data == "rock_paper_scissors":
        game_data = await bot_features.rock_paper_scissors_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data.startswith("rps_choice_"):
        user_choice = callback_data.replace("rps_choice_", "")
        result = await bot_features.check_rps_choice(user_choice)
        await query.edit_message_text(
            result["message"],
            reply_markup=result["reply_markup"]
        )
    
    elif callback_data == "word_game":
        game_data = await bot_features.word_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "word_hint":
        if 'word_game' in bot_features.user_data:
            word = bot_features.user_data['word_game']['word']
            first_letter = word[0]
            last_letter = word[-1]
            await query.edit_message_text(
                f"💡 **راهنمایی:**\n\nحرف اول: {first_letter}\nحرف آخر: {last_letter}\n\nتعداد حروف: {len(word)}",
                reply_markup=query.message.reply_markup
            )
    
    elif callback_data == "memory_game":
        game_data = await bot_features.memory_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "random_game":
        game_data = await bot_features.random_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "sticker_creator":
        menu_data = await bot_features.custom_sticker_menu()
        await query.edit_message_text(
            menu_data["message"],
            reply_markup=menu_data["reply_markup"]
        )
    
    elif callback_data.startswith("sticker_bg_"):
        color = callback_data.replace("sticker_bg_", "")
        color_map = {
            "white": "white",
            "black": "black", 
            "blue": "#3498db",
            "red": "#e74c3c",
            "green": "#2ecc71",
            "yellow": "#f1c40f"
        }
        
        bg_color = color_map.get(color, "white")
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["sticker_bg"] = bg_color
        
        keyboard = [[
            InlineKeyboardButton("✏️ نوشتن متن", callback_data="sticker_text")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ رنگ پس‌زمینه انتخاب شد!\n\nحالا متن استیکر خود را بنویسید:",
            reply_markup=reply_markup
        )
    
    elif callback_data == "sticker_text":
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id]["waiting_for_sticker_text"] = True
        
        await query.edit_message_text(
            "✏️ لطفاً متن مورد نظر خود را برای استیکر بنویسید:"
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    """مدیریت پیام‌های متنی کاربر"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # بررسی حالت انتظار برای حدس عدد
    if user_id in user_states and user_states[user_id].get("waiting_for_guess"):
        try:
            guess = int(text)
            result = await bot_features.check_guess(guess)
            await update.message.reply_text(
                result["message"],
                reply_markup=result["reply_markup"]
            )
            user_states[user_id]["waiting_for_guess"] = False
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد صحیح وارد کنید!")
    
    # بررسی حالت انتظار برای متن استیکر
    elif user_id in user_states and user_states[user_id].get("waiting_for_sticker_text"):
        bg_color = user_states[user_id].get("sticker_bg", "white")
        sticker_bytes = await bot_features.create_sticker(text, bg_color)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.png")
            )
            await update.message.reply_text("✅ استیکر شما با موفقیت ساخته شد!")
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر!")
        
        user_states[user_id]["waiting_for_sticker_text"] = False
    
    # ساخت استیکر سریع با دستور مستقیم
    elif text.startswith("/sticker "):
        sticker_text = text.replace("/sticker ", "")
        sticker_bytes = await bot_features.create_sticker(sticker_text)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.png")
            )