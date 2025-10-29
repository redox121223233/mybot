"""
Handlers with Glassmorphism Design
هندلرهای ربات با طراحی شیشه‌ای مدرن
"""
import logging
import asyncio
from telegram import Update, InputFile
from telegram.ext import CallbackContext
from bot_features import bot_features
from utils import UserStateManager

logger = logging.getLogger(__name__)

async def setup_handlers(application):
    """تنظیم هندلرها برای ربات شیشه‌ای"""
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
    application.add_handler(CommandHandler("games", games_menu))
    application.add_handler(CommandHandler("settings", settings_menu))
    
    # هندلرهای callback و پیام‌ها
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def start_command(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    await bot_features.start_command(update, context)
    user_id = update.effective_user.id
    UserStateManager.set_state(user_id, {"mode": "main", "color_scheme": "blue"})

async def help_command(update: Update, context: CallbackContext) -> None:
    """دستور /help"""
    await bot_features.help_command(update, context)

async def sticker_command(update: Update, context: CallbackContext) -> None:
    """دستور /sticker برای ساخت استیکر سریع"""
    if context.args:
        text = ' '.join(context.args)
        sticker_bytes = await bot_features.create_sticker(text, "blue")
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.webp")
            )
            await update.message.reply_text(
                "✨ استیکر شیشه‌ای شما با موفقیت ساخته شد!\n"
                "🎨 برای طرح‌های دیگر از دستور /customsticker استفاده کنید"
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ساخت استیکر!\n"
                "🔧 لطفاً دوباره تلاش کنید"
            )
    else:
        await update.message.reply_text(
            "🎨 **استیکر ساز شیشه‌ای**\n\n"
            "📝 لطفاً متن استیکر را وارد کنید:\n"
            "مثال: /sticker سلام دنیا\n\n"
            "🎯 برای طرح‌های مختلف از /customsticker استفاده کنید"
        )

async def games_menu(update: Update, context: CallbackContext) -> None:
    """منوی بازی‌ها"""
    text = """
🎮 **منوی بازی‌های شیشه‌ای**

🎯 انتخاب بازی مورد نظر:
    """
    
    buttons_data = [
        [("🔢 حدس عدد", "guess_number"), ("✂️ سنگ کاغذ قیچی", "rock_paper_scissors")],
        [("📝 حدس کلمه", "word_game"), ("🧠 بازی حافظه", "memory_game")],
        [("🎲 بازی تصادفی", "random_game"), ("🏠 بازگشت", "back_to_main")]
    ]
    
    reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, "purple")
    await update.message.reply_text(text, reply_markup=reply_markup)

async def settings_menu(update: Update, context: CallbackContext) -> None:
    """منوی تنظیمات"""
    text = """
⚙️ **تنظیمات ربات شیشه‌ای**

🎨 تغییر رنگ تم ربات:
    """
    
    buttons_data = [
        [("🔵 تم آبی", "set_theme_blue"), ("🟣 تم بنفش", "set_theme_purple")],
        [("🟢 تم سبز", "set_theme_green"), ("🔴 تم قرمز", "set_theme_red")],
        [("🟠 تم نارنجی", "set_theme_orange"), ("🩷 تم صورتی", "set_theme_pink")],
        [("🏠 بازگشت", "back_to_main")]
    ]
    
    reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, "blue")
    await update.message.reply_text(text, reply_markup=reply_markup)

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
    user_state = UserStateManager.get_state(user_id)
    callback_data = query.data
    
    # رنگ تم کاربر
    color_scheme = user_state.get("color_scheme", "blue")
    
    # هندلر دکمه‌های اصلی
    if callback_data == "back_to_main":
        await bot_features.start_command(update, context)
        UserStateManager.set_state(user_id, {"mode": "main", "color_scheme": color_scheme})
        return
    
    elif callback_data == "start_games":
        await games_menu(update, context)
    
    elif callback_data == "create_sticker":
        await customsticker_command(update, context)
    
    elif callback_data == "help_command":
        await help_command(update, context)
    
    elif callback_data == "settings":
        await settings_menu(update, context)
    
    elif callback_data == "games_menu":
        await games_menu(update, context)
    
    elif callback_data == "stickers_menu":
        await customsticker_command(update, context)
    
    elif callback_data == "random_game":
        game_data = await bot_features.random_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    # هندلر بازی حدس عدد
    elif callback_data == "guess_number":
        game_data = await bot_features.guess_number_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "guess_hint":
        if 'guess_number' in bot_features.user_data:
            number = bot_features.user_data['guess_number']
            hint = "بزرگتر از 50" if number > 50 else "کوچکتر از 50"
            
            text = f"""
💡 **راهنمایی**

🎯 عدد {hint} است!
🔢 بازه: {max(1, number-20)} تا {min(100, number+20)}

🎮 دوباره تلاش کنید!
            """
            
            buttons_data = [
                [("🎮 بازگشت به بازی", "guess_number"), ("🏠 منوی اصلی", "back_to_main")]
            ]
            
            reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, "orange")
            await query.edit_message_text(text, reply_markup=reply_markup)
    
    # هندلر بازی سنگ کاغذ قیچی
    elif callback_data.startswith("rps_choice_"):
        user_choice = callback_data.replace("rps_choice_", "")
        result = await bot_features.check_rps_choice(user_choice)
        await query.edit_message_text(
            result["message"],
            reply_markup=result["reply_markup"]
        )
    
    elif callback_data == "rock_paper_scissors":
        game_data = await bot_features.rock_paper_scissors_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    # هندلر بازی کلمات
    elif callback_data == "word_game":
        game_data = await bot_features.word_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "word_hint":
        if 'word_game' in bot_features.user_data:
            word_data = bot_features.user_data['word_game']
            word = word_data['word']
            first_letter = word[0]
            last_letter = word[-1]
            hints_count = word_data.get('hints', 0) + 1
            
            # محاسبه تعداد حروف قابل نمایش
            letters_to_show = min(hints_count, len(word) - 2)
            masked_word = first_letter + "_" * (len(word) - 2) + last_letter
            
            if letters_to_show > 1:
                for i in range(1, letters_to_show):
                    if i < len(word) - 1:
                        masked_word = masked_word[:i+1] + word[i] + masked_word[i+2:]
            
            text = f"""
💡 **راهنمایی**

📝 کلمه: {masked_word}
🔤 حرف اول: {first_letter}
🔤 حرف آخر: {last_letter}
📊 تعداد حروف: {len(word)}
🎯 راهنمایی {hints_count} استفاده شد

🎮 دوباره تلاش کنید!
            """
            
            bot_features.user_data['word_game']['hints'] = hints_count
            
            buttons_data = [
                [("🎮 بازگشت به بازی", "word_game"), ("🏠 منوی اصلی", "back_to_main")]
            ]
            
            reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, "purple")
            await query.edit_message_text(text, reply_markup=reply_markup)
    
    # هندلر بازی حافظه
    elif callback_data == "memory_game":
        game_data = await bot_features.memory_game()
        await query.edit_message_text(
            game_data["message"],
            reply_markup=game_data["reply_markup"]
        )
    
    elif callback_data == "memory_start":
        import random
        
        numbers = [random.randint(1, 100) for _ in range(5)]
        text = f"""
🧠 **به خاطر بسپارید!**

📊 اعداد زیر را به خاطر بسپارید:
{' '.join(map(str, numbers))}

⏰ 3 ثانیه زمان دارید...
⏳ در حال شمارش...
        """
        
        await query.edit_message_text(text)
        await asyncio.sleep(3)
        
        # بعد از 3 ثانیه درخواست ورودی کاربر
        UserStateManager.update_state(user_id, {"waiting_memory_numbers": True, "memory_numbers": numbers})
        
        text = """
🧠 **اعداد را وارد کنید**

📝 اعدادی که به خاطر سپردید را وارد کنید
🔢 با فاصله بین آنها (مثال: 12 34 56)

🎯 موفق باشید!
        """
        
        buttons_data = [
            [("🔙 بازگشت", "back_to_main")]
        ]
        
        reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, "green")
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    # هندلر استیکر ساز
    elif callback_data == "sticker_bg_blue":
        UserStateManager.update_state(user_id, {"sticker_bg": "blue"})
        await _sticker_text_prompt(update, context, "آبی")
    
    elif callback_data == "sticker_bg_purple":
        UserStateManager.update_state(user_id, {"sticker_bg": "purple"})
        await _sticker_text_prompt(update, context, "بنفش")
    
    elif callback_data == "sticker_bg_green":
        UserStateManager.update_state(user_id, {"sticker_bg": "green"})
        await _sticker_text_prompt(update, context, "سبز")
    
    elif callback_data == "sticker_bg_red":
        UserStateManager.update_state(user_id, {"sticker_bg": "red"})
        await _sticker_text_prompt(update, context, "قرمز")
    
    elif callback_data == "sticker_bg_orange":
        UserStateManager.update_state(user_id, {"sticker_bg": "orange"})
        await _sticker_text_prompt(update, context, "نارنجی")
    
    elif callback_data == "sticker_bg_pink":
        UserStateManager.update_state(user_id, {"sticker_bg": "pink"})
        await _sticker_text_prompt(update, context, "صورتی")
    
    elif callback_data == "sticker_text":
        UserStateManager.update_state(user_id, {"waiting_for_sticker_text": True})
        
        text = """
✏️ **نوشتن متن استیکر**

🎨 متن مورد نظر خود را وارد کنید
✨ با طراحی شیشه‌ای و زیبا

📝 مثال: سلام دنیای شیشه‌ای!
        """
        
        buttons_data = [
            [("🔙 بازگشت", "back_to_main")]
        ]
        
        reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, color_scheme)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    # هندلر تنظیمات تم
    elif callback_data.startswith("set_theme_"):
        theme = callback_data.replace("set_theme_", "")
        UserStateManager.set_state(user_id, {"color_scheme": theme})
        
        text = f"""
✨ **تغییر تم موفق**

🎨 تم ربات به {theme} تغییر کرد
✅ تنظیمات ذخیره شد

🏠 به منوی اصلی بازگردید
        """
        
        buttons_data = [
            [("🏠 منوی اصلی", "back_to_main")]
        ]
        
        reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, theme)
        await query.edit_message_text(text, reply_markup=reply_markup)

async def _sticker_text_prompt(update: Update, context: CallbackContext, color_name: str):
    """درخواست متن برای ساخت استیکر"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user_id = update.effective_user.id
    user_state = UserStateManager.get_state(user_id)
    color_scheme = user_state.get("color_scheme", "blue")
    
    text = f"""
🎨 **طرح {color_name} انتخاب شد**

✏️ حالا متن استیکر را بنویسید
🌈 با طراحی شیشه‌ای و مدرن

📝 متن خود را ارسال کنید
    """
    
    buttons_data = [
        [("🔙 بازگشت", "back_to_main")]
    ]
    
    reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, color_scheme)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    UserStateManager.update_state(user_id, {"waiting_for_sticker_text": True})

async def handle_message(update: Update, context: CallbackContext) -> None:
    """مدیریت پیام‌های متنی کاربر"""
    user_id = update.effective_user.id
    text = update.message.text
    user_state = UserStateManager.get_state(user_id)
    
    # بررسی حالت انتظار برای حدس عدد
    if user_state.get("waiting_for_guess"):
        try:
            guess = int(text)
            result = await bot_features.check_guess(guess)
            await update.message.reply_text(
                result["message"],
                reply_markup=result["reply_markup"]
            )
            UserStateManager.update_state(user_id, {"waiting_for_guess": False})
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً یک عدد صحیح وارد کنید!\n"
                "🔢 مثال: 50"
            )
    
    # بررسی حالت انتظار برای متن استیکر
    elif user_state.get("waiting_for_sticker_text"):
        bg_color = user_state.get("sticker_bg", "blue")
        sticker_bytes = await bot_features.create_sticker(text, bg_color)
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.webp")
            )
            await update.message.reply_text(
                f"✨ استیکر شیشه‌ای شما با موفقیت ساخته شد!\n"
                f"🎨 طرح: {bg_color}\n"
                f"📝 متن: {text}\n\n"
                f"🔄 برای ساخت استیکر دیگر از /customsticker استفاده کنید"
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ساخت استیکر!\n"
                "🔧 لطفاً دوباره تلاش کنید"
            )
        
        UserStateManager.update_state(user_id, {"waiting_for_sticker_text": False})
    
    # بررسی حالت انتظار برای بازی حافظه
    elif user_state.get("waiting_memory_numbers"):
        try:
            user_numbers = [int(num.strip()) for num in text.split()]
            correct_numbers = user_state.get("memory_numbers", [])
            
            if user_numbers == correct_numbers:
                result_text = """
🎉 **تبریک! شما برنده شدید!**

✧ همه اعداد را درست به خاطر سپردید
🏆 امتیاز شما: +15
🧠 حافظه عالی دارید!

🎮 برای بازی دوباره کلیک کنید
                """
                color_scheme = "green"
            else:
                result_text = f"""
😔 **متاسفانه!**

❌ اعداد صحیح نبودند
✅ اعداد درست: {' '.join(map(str, correct_numbers))}
🎯 اعداد شما: {' '.join(map(str, user_numbers))}

🔄 دوباره تلاش کنید
                """
                color_scheme = "red"
            
            buttons_data = [
                [("🔄 بازی دوباره", "memory_start"), ("🏠 منوی اصلی", "back_to_main")]
            ]
            
            reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, color_scheme)
            await update.message.reply_text(result_text, reply_markup=reply_markup)
            
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً اعداد را به درستی وارد کنید!\n"
                "📝 مثال: 12 34 56 78 90\n"
                "🔢 اعداد را با فاصله از هم جدا کنید"
            )
        
        UserStateManager.update_state(user_id, {"waiting_memory_numbers": False})
    
    # بررسی حالت انتظار برای بازی کلمات
    elif user_state.get("waiting_for_word"):
        if 'word_game' in bot_features.user_data:
            correct_word = bot_features.user_data['word_game']['word']
            
            if text.strip().lower() == correct_word.lower():
                result_text = f"""
🎉 **آفرین! کلمه صحیح بود!**

✅ کلمه: {correct_word}
🏆 امتیاز شما: +20
🧠 هوش و دانش عالی!

🎮 برای بازی دوباره کلیک کنید
                """
                color_scheme = "green"
            else:
                result_text = f"""
😔 **کلمه اشتباه است!**

❌ حدس شما: {text}
💡 برای راهنمایی از دکمه زیر استفاده کنید
🎯 دوباره تلاش کنید

💭 کلمه {len(correct_word)} حرف دارد
                """
                color_scheme = "orange"
            
            buttons_data = [
                [("💡 راهنمایی", "word_hint"), ("🔄 بازی دوباره", "word_game"), ("🏠 منوی اصلی", "back_to_main")]
            ]
            
            reply_markup = bot_features.create_glassmorphism_keyboard(buttons_data, color_scheme)
            await update.message.reply_text(result_text, reply_markup=reply_markup)
    
    # استیکر سریع با دستور مستقیم
    elif text.startswith("/sticker "):
        sticker_text = text.replace("/sticker ", "")
        sticker_bytes = await bot_features.create_sticker(sticker_text, "blue")
        
        if sticker_bytes:
            sticker_bytes.seek(0)
            await update.message.reply_sticker(
                sticker=InputFile(sticker_bytes, filename="sticker.webp")
            )
            await update.message.reply_text(
                "✨ استیکر شیشه‌ای شما با موفقیت ساخته شد!\n"
                "🎨 برای طرح‌های دیگر از /customsticker استفاده کنید"
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ساخت استیکر!\n"
                "🔧 لطفاً دوباره تلاش کنید"
            )