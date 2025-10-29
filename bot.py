import requests
from bs4 import BeautifulSoup
import random
import json
import os
from datetime import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import CallbackContext
import tempfile
import shutil
from PIL import Image, ImageDraw, ImageFont
import io
import time

class TelegramBotFeatures:
    def __init__(self):
        self.user_data = {}
        self.coupons = self.load_coupons()
        self.music_data = self.load_music_data()
        self.api_key = os.getenv('API_KEY', 'your_default_api_key')
        self.game_states = {}  # For tracking game sessions
        self.jokes = self.load_jokes()
        self.facts = self.load_facts()
        
    def load_coupons(self):
        return [
            {"code": "SAVE10", "discount": "10%", "category": "electronics"},
            {"code": "FOOD20", "discount": "20%", "category": "food"},
            {"code": "STYLE15", "discount": "15%", "category": "fashion"},
            {"code": "TECH25", "discount": "25%", "category": "technology"},
            {"code": "HOME30", "discount": "30%", "category": "home"},
        ]
    
    def load_music_data(self):
        return {
            "pop": ["Artist1 - Song1", "Artist2 - Song2", "Artist3 - Song3"],
            "rock": ["Band1 - Track1", "Band2 - Track2", "Band3 - Track3"],
            "classical": ["Composer1 - Piece1", "Composer2 - Piece2", "Composer3 - Piece3"],
            "jazz": ["JazzArtist1 - JazzSong1", "JazzArtist2 - JazzSong2", "JazzArtist3 - JazzSong3"],
        }
    
    def load_jokes(self):
        return [
            "چرا گوسفند به مدرسه نرفت؟ چون太多太多！",
            "یک روز به گوسفند گفت چرا اینقدر سفیدی؟ گفت: از شامپو استفاده می‌کنم! 🐑",
            "معلم به دانش‌آموز: چرا تمرین نکردی؟ دانش‌آموز: از ترس اینکه خوب درس نخوانم! 😅",
            "یک رستوران به بقیه رستوران‌ها چه می‌گوید؟ دست‌مون به دامن شما! 🍽️",
            "چرا کتاب به کتابخانه رفت؟ تا داستانش را تعریف کند! 📚",
        ]
    
    def load_facts(self):
        return [
            "🧠 آیا می‌دانستید؟ مغز انسان حدود 2% وزن بدن را تشکیل می‌دهد اما 20% انرژی را مصرف می‌کند!",
            "🌍 آیا می‌دانستید؟ زمین تنها سیاره‌ای نیست که نام یک خدا را دارد! سیاره‌های دیگر هم نام خدایان روم دارند.",
            "🐙 آیا می‌دانستید؟ هشت‌پا سه قلب دارد!",
            "🦒 آیا می‌دانستید؟ گردن زرافه همان تعداد مهره دارد که گردن انسان (7 عدد)، فقط بلندتر است!",
            "🌙 آیا می‌دانستید؟ ماه به آرامی از زمین دور می‌شود (حدود 3.8 سانتی‌متر در سال)!",
        ]

    async def start_command(self, update: Update, context: CallbackContext):
        welcome_message = """
🎉 به ربات من خوش آمدید! 🎉

من یک ربات چندمنظوره با قابلیت‌های زیر هستم:

📱 **قابلیت‌های اصلی:**
• 🔍 جستجوی پیشرفته اینترنت
• 🎵 دانلود و پخش موسیقی
• 🎬 جستجوی فیلم و سریال
• 💬 چت با هوش مصنوعی
• 🌦️ اطلاعات آب و هوا
• 📊 قیمت ارزهای دیجیتال
• 🎮 بازی و سرگرمی
• 🛍️ جستجوی کالا و قیمت‌ها
• 📰 اخبار روز
• 🎨 ساخت استیکر و تصاویر

برای شروع، دستور /help را وارد کنید یا یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        keyboard = [
            [InlineKeyboardButton("🔍 جستجو", callback_data="search"),
             InlineKeyboardButton("🎵 موسیقی", callback_data="music")],
            [InlineKeyboardButton("🎬 فیلم", callback_data="movie"),
             InlineKeyboardButton("🤖 چت با AI", callback_data="chat")],
            [InlineKeyboardButton("🌦️ آب و هوا", callback_data="weather"),
             InlineKeyboardButton("💰 قیمت ارز", callback_data="crypto")],
            [InlineKeyboardButton("🎮 بازی", callback_data="game"),
             InlineKeyboardButton("🛍️ خرید", callback_data="shopping")],
            [InlineKeyboardButton("🃏 سرگرمی", callback_data="fun"),
             InlineKeyboardButton("🎲 بازی جدید", callback_data="new_game")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: CallbackContext):
        help_text = """
📖 **راهنمای کامل ربات:**

🔍 **جستجوی اینترنت:**
• /search <متن> - جستجوی گوگل
• /image <متن> - جستجوی تصویر

🎵 **موسیقی:**
• /music <نام آهنگ> - جستجوی موسیقی
• /download <لینک> - دانلود موسیقی

🎬 **فیلم و سریال:**
• /movie <نام فیلم> - جستجوی فیلم
• /series <نام سریال> - جستجوی سریال

🤖 **هوش مصنوعی:**
• /ai <سوال> - پرسش از AI
• /chat <متن> - چت با هوش مصنوعی

🌦️ **آب و هوا:**
• /weather <شهر> - آب و هوای شهر

💰 **ارز دیجیتال:**
• /crypto <نام ارز> - قیمت ارز دیجیتال
• /btc - قیمت بیت‌کوین
• /eth - قیمت اتریوم

🎮 **بازی:**
• /game - شروع بازی
• /quiz - مسابقه
• /riddle - معما
• /number_game - بازی حدس عدد
• /rock_paper_scissors - سنگ کاغذ قیچی
• /memory_game - بازی حافظه
• /word_chain - زنجیره کلمات
• /trivia - اطلاعات عمومی

🃏 **سرگرمی:**
• /joke - جوک جدید
• /fact - اطلاعات جالب
• /8ball - توپ جادویی 8
• /roll_dice - تاس اندازی
• /coin_flip - شیر یا خط
• /compliment - تعریف کردن
• /quote - نقل قول
• /poem - شعر تصادفی

🛍️ **خرید:**
• /price <کالا> - قیمت کالا
• /coupon - کوپن‌های تخفیف

🎨 **سازندگان:**
• /sticker <متن> - ساخت استیکر
• /meme <متن> - ساخت میم

📰 **اخبار:**
• /news - اخبار روز
• /technews - اخبار تکنولوژی

📊 **سایر:**
• /time - زمان فعلی
• /calc <محاسبه> - ماشین حساب
• /translate <متن> - ترجمه

برای هر دستور می‌توانید از منوی هم استفاده کنید!
        """
        await update.message.reply_text(help_text)

    # 🎮 NEW ENTERTAINMENT GAMES 🎮

    async def number_game(self, update: Update, context: CallbackContext):
        """بازی حدس عدد - حدس عدد بین 1 تا 100"""
        user_id = update.effective_user.id
        
        if user_id not in self.game_states:
            self.game_states[user_id] = {}
        
        # Generate random number
        self.game_states[user_id]['number'] = random.randint(1, 100)
        self.game_states[user_id]['attempts'] = 0
        self.game_states[user_id]['game_type'] = 'number'
        
        await update.message.reply_text(
            "🔢 **بازی حدس عدد شروع شد!**\n\n"
            "من یک عدد بین 1 تا 100 انتخاب کرده‌ام.\n"
            "تلاش کن آن را حدس بزنی!\n\n"
            "حدس خود را بنویس، مثلا: 75"
        )

    async def rock_paper_scissors(self, update: Update, context: CallbackContext):
        """بازی سنگ کاغذ قیچی"""
        keyboard = [
            [InlineKeyboardButton("🪨 سنگ", callback_data="rps_rock"),
             InlineKeyboardButton("📄 کاغذ", callback_data="rps_paper")],
            [InlineKeyboardButton("✂️ قیچی", callback_data="rps_scissors")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **سنگ، کاغذ، قیچی!**\n\n"
            "انتخاب کن:",
            reply_markup=reply_markup
        )

    async def memory_game(self, update: Update, context: CallbackContext):
        """بازی حافظه - به یاد سپردن دنباله emoji"""
        user_id = update.effective_user.id
        
        if user_id not in self.game_states:
            self.game_states[user_id] = {}
        
        emojis = ["🍎", "🍌", "🍇", "🍓", "🍒", "🍑", "🥝", "🍉"]
        sequence_length = 3
        sequence = random.sample(emojis, sequence_length)
        
        self.game_states[user_id]['memory_sequence'] = sequence
        self.game_states[user_id]['game_type'] = 'memory'
        
        sequence_text = " ".join(sequence)
        
        await update.message.reply_text(
            f"🧠 **بازی حافظه!**\n\n"
            f"این دنباله را به خاطر بسپار:\n\n"
            f"{sequence_text}\n\n"
            f"5 ثانیه فرصت داری...\n\n"
            f"(بعداً دنباله را دقیقاً به همین ترتیب بنویس)"
        )
        
        # Wait and then clear
        await asyncio.sleep(5)
        await update.message.reply_text("❌ حالا دنباله را بنویس! (ایموجی‌ها را با فاصله بنویس)")

    async def word_chain(self, update: Update, context: CallbackContext):
        """زنجیره کلمات - بازی با کلمات فارسی"""
        if not context.args:
            await update.message.reply_text(
                "🔗 **زنجیره کلمات!**\n\n"
                "من با یک کلمه شروع می‌کنم و تو باید با آخرین حرف آن کلمه شروع کنی.\n\n"
                "مثلا: من می‌گویم «ماشین» تو باید با «ن» شروع کنی مثل «نارنجی».\n\n"
                "برای شروع دستور رو با یک کلمه بفرست: /word_chain ماشین"
            )
            return
        
        user_word = " ".join(context.args).strip()
        last_char = user_word[-1]
        
        # Simple validation - check if it ends with a valid Persian letter
        if not (ord('ا') <= ord(last_char) <= ord('ی')):
            await update.message.reply_text("⚠️ لطفاً یک کلمه فارسی معتبر وارد کن!")
            return
        
        # Get a word that starts with the last character
        words_by_start = {
            'ا': ['ابریشم', 'انار', 'انگور', 'آب', 'آفتاب'],
            'ب': ['بهار', 'باغ', 'ببر', 'برف', 'بالش'],
            'پ': ['پارچ', 'پرنده', 'پنجره', 'پول', 'پل'],
            'ت': ['توت', 'ترمه', 'تابستان', 'تلفن', 'تلویزیون'],
            'ث': ['ثابت', 'ثروت', 'ثلج', 'ثمره'],
            'ج': ['جنگل', 'جوجه', 'جواهر', 'جعبه', 'جاده'],
            'چ': ['چای', 'چرخ', 'چکش', 'چمن', 'چراغ'],
            'ح': ['حیوان', 'حافظ', 'حباب', 'حساب', 'حوض'],
            'خ': ['خورشید', 'خلاقیت', 'خیابان', 'خواب', 'خانواده'],
            'د': ['درخت', 'دریا', 'دلفین', 'دوربین', 'دیوار'],
            'ذ': ['ذغال', 'ذهاب', 'ذره', 'ذوق'],
            'ر': ['رودخانه', 'رنگین‌کمان', 'رعد', 'روبات', 'ریحان'],
            'ز': ['زمین', 'زنجبیل', 'زرافه', 'زنبور', 'زمستانه'],
            'ژ': ['ژاله', 'ژنراتور', 'ژاپن', 'ژنو'],
            'س': ['سفره', 'سمفونی', 'سفید', 'سنگ', 'سفر'],
            'ش': ['شیرینی', 'شب', 'شمع', 'شادی', 'شیشه'],
            'ص': ['صبح', 'صندوق', 'صنعت', 'صدا', 'صفحه'],
            'ض': ['ضد', 'ضربان', 'ضخامت', 'ضرب'],
            'ط': ['طلا', 'طوفان', 'طبیعت', 'طالع', 'طرح'],
            'ظ': ['ظرف', 'ظرافت', 'ظهر', 'ظرفیت'],
            'ع': ['عسل', 'عکاسی', 'عطر', 'عشق', 'عمل'],
            'غ': ['غذا', 'غروب', 'غبار', 'غربت', 'غنچه'],
            'ف': ['فیل', 'فردا', 'فصل', 'فکر', 'فضا'],
            'ق': ['قند', 'قایق', 'قلم', 'قفس', 'قرار'],
            'ک': ['کوه', 'کتاب', 'کشتی', 'کفش', 'کامپیوتر'],
            'گ': ['گل', 'گربه', 'گندم', 'گیتار', 'گرس'],
            'ل': ['لپ‌تاپ', 'لباس', 'لیمو', 'لوستر', 'لاک'],
            'م': ['ماه', 'ماشین', 'مادر', 'میز', 'مرکب'],
            'ن': ['نور', 'نقاشی', 'نجوا', 'نان', 'نبات'],
            'و': ['وسیله', 'وزش', 'ورد', 'وصف', 'ورزش'],
            'ه': ['هواپیما', 'هندوانه', 'هیکل', 'هدیه', 'هیولا'],
            'ی': ['یخ', 'یاس', 'یارو', 'یادداشت', 'یخچال'],
        }
        
        if last_char in words_by_start:
            my_word = random.choice(words_by_start[last_char])
            await update.message.reply_text(
                f"🔗 **زنجیره کلمات!**\n\n"
                f"تو گفتی: {user_word}\n"
                f"من می‌گویم: {my_word}\n\n"
                f"حالا تو با «{my_word[-1]}» شروع کن!"
            )
        else:
            await update.message.reply_text("⚠️ نتونستم کلمه‌ای پیدا کنم! یه کلمه دیگه امتحان کن.")

    async def trivia_quiz(self, update: Update, context: CallbackContext):
        """مسابقه اطلاعات عمومی"""
        questions = [
            {
                "question": "پایتخت ایران کجاست؟",
                "options": ["اصفهان", "تهران", "مشهد", "شیراز"],
                "answer": 1,
                "explanation": "تهران پایتخت ایران است."
            },
            {
                "question": "بزرگ‌ترین سیاره منظومه شمسی کدام است؟",
                "options": ["زمین", "مریخ", "مشتری", "زحل"],
                "answer": 2,
                "explanation": "مشتری بزرگ‌ترین سیاره منظومه شمسی است."
            },
            {
                "question": "چند ساعت در یک روز وجود دارد؟",
                "options": ["12", "24", "36", "48"],
                "answer": 1,
                "explanation": "هر روز 24 ساعت دارد."
            },
            {
                "question": "رنگین‌کمان چند رنگ دارد؟",
                "options": ["5", "6", "7", "8"],
                "answer": 2,
                "explanation": "رنگین‌کمان 7 رنگ دارد: قرمز، نارنجی، زرد، سبز، آبی، نیلی، بنفش."
            },
            {
                "question": "سریع‌ترین حیوان زمین کدام است؟",
                "options": ["شیر", "پلنگ", "چیتا", "اسب"],
                "answer": 2,
                "explanation": "چیتا با سرعت 110-120 کیلومتر بر ساعت سریع‌ترین حیوان زمین است."
            }
        ]
        
        question = random.choice(questions)
        user_id = update.effective_user.id
        
        if user_id not in self.game_states:
            self.game_states[user_id] = {}
        
        self.game_states[user_id]['trivia_answer'] = question['answer']
        self.game_states[user_id]['trivia_explanation'] = question['explanation']
        
        keyboard = []
        for i, option in enumerate(question["options"]):
            keyboard.append([InlineKeyboardButton(option, callback_data=f"trivia_{i}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🧠 **مسابقه اطلاعات عمومی!**\n\n"
            f"❓ {question['question']}\n\n"
            f"جواب درست را انتخاب کن:",
            reply_markup=reply_markup
        )

    async def magic_8_ball(self, update: Update, context: CallbackContext):
        """توپ جادویی 8 - پاسخ به سوالات بله/خیر"""
        if not context.args:
            await update.message.reply_text(
                "🎱 **توپ جادویی 8!**\n\n"
                "یک سوال بله/خیر بپرس و من جواب می‌دم!\n\n"
                "مثال: /8ball آیا فردا بارون میاد؟"
            )
            return
        
        responses = [
            "✅ بله، قطعاً!",
            "❌ نه، هرگز!",
            "🤔 بعید به نظر می‌رسه...",
            "💫 شانس خوبیه!",
            "🔮 آره، به زودی!",
            "⚡ فعلاً نه!",
            "🌟 قطعاً همینطوره!",
            "🎯 تمرکز کن و دوباره بپرس!",
            "💚 بهتره نپرسی!",
            "🌺 آره، چرا که نه!",
        ]
        
        question = " ".join(context.args)
        answer = random.choice(responses)
        
        await update.message.reply_text(
            f"🎱 **توپ جادویی 8**\n\n"
            f"سوال: {question}\n"
            f"پاسخ: {answer}"
        )

    async def roll_dice(self, update: Update, context: CallbackContext):
        """تاس اندازی"""
        sides = 6
        if context.args:
            try:
                sides = int(context.args[0])
                if sides < 2 or sides > 100:
                    sides = 6
            except:
                sides = 6
        
        dice_emojis = {
            1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
        }
        
        result = random.randint(1, sides)
        dice_emoji = dice_emojis.get(result, f"🎲 {result}")
        
        await update.message.reply_text(
            f"🎲 **تاس اندازی!**\n\n"
            f"تاس {sides} وجهی: {dice_emoji}"
        )

    async def coin_flip(self, update: Update, context: CallbackContext):
        """شیر یا خط"""
        result = random.choice(["شیر", "خط"])
        emoji = "🦅" if result == "شیر" else "🪙"
        
        await update.message.reply_text(
            f"🪙 **شیر یا خط!**\n\n"
            f"نتیجه: {result} {emoji}"
        )

    async def tell_joke(self, update: Update, context: CallbackContext):
        """تعریف یک جوک"""
        joke = random.choice(self.jokes)
        
        await update.message.reply_text(
            f"😄 **جوک جدید!**\n\n"
            f"{joke}\n\n"
            f"😂 خندیدی؟"
        )

    async def tell_fact(self, update: Update, context: CallbackContext):
        """گفتن یک اطلاعات جالب"""
        fact = random.choice(self.facts)
        
        await update.message.reply_text(fact)

    async def give_compliment(self, update: Update, context: CallbackContext):
        """تعریف کردن به کاربر"""
        compliments = [
            "🌟 تو فوق‌العاده‌ای!",
            "💫 انرژی مثبت تو عالیه!",
            "🎨 خلاقیت تو بی‌نظیره!",
            "🌺 لبخند تو دنیا رو روشن می‌کنه!",
            "🚀 تو می‌تونی هر کاری رو انجام بدی!",
            "💎 تو یه شخصیت ارزشمند هستی!",
            "🌈 حضور تو حال دیگران رو خوب می‌کنه!",
            "⭐ تو یه ستاره‌ی درخشان هستی!",
            "🦋 شیوایی تو بی‌نظیره!",
            "🌸 تو به دنیا زیبایی می‌بخشی!",
        ]
        
        compliment = random.choice(compliments)
        
        await update.message.reply_text(compliment)

    async def random_quote(self, update: Update, context: CallbackContext):
        """نقل قول تصادفی"""
        quotes = [
            "🌟 **گوته:** «نیت ما آینده را شکل می‌دهد.»",
            "💫 **اینشتین:** «تخیل مهم‌تر از دانش است.»",
            "🎨 **پیکاسو:** «هر کودکی یک هنرمند است.»",
            "🌺 **روزvelt:** «تنها چیزی که باید از آن بترسیم، خود ترس است.»",
            "🚀 **اسپیلبرگ:** «رویاهایتان را دنبال کنید.»",
            "💎 **کنفوسیوس:** «سفر هزار مایلی با یک قدم شروع می‌شود.»",
            "🌈 **گاندی:** «تغیاری که می‌خواهی در جهان ببینی، با خودت شروع کن.»",
            "⭐ **مادر ترزا:** «کارهای کوچک با عشق بزرگ انجام شوند.»",
        ]
        
        quote = random.choice(quotes)
        await update.message.reply_text(quote)

    async def random_poem(self, update: Update, context: CallbackContext):
        """شعر تصادفی"""
        poems = [
            "🌹 **حافظ:**\n\n«اگر دل تو ز علم پر شد، جای عشب باز کن\nزین قرص قمر، هرچه بخشی، باز ارزانی کن»",
            
            "🌙 **سعدی:**\n\n«بنی آدم اعضای یکدیگرند\nکه در آفرینش ز یک گوهرند»",
            
            "🌸 **مولانا:**\n\n«عشق آنجاست که بادی بر نگردد\nهرچه بگذرد ز عشق، نیکو گردد»",
            
            "🦋 **خیام:**\n\n«به باغ مگو ای ساقی بهار چه خوبان\nماه به چه کار آید اگر درخت نباشد»",
            
            "🌺 **شاملو:**\n\n«باید که از دست دادن، آموخت\nباید از صفر آغاز کرد»",
        ]
        
        poem = random.choice(poems)
        await update.message.reply_text(
            f"📖 **شعر تصادفی**\n\n{poem}"
        )

    # 🎮 ORIGINAL GAME METHODS (Updated) 🎮

    async def play_game(self, game_type: str = "quiz"):
        if game_type == "quiz":
            questions = [
                {"question": "پایتخت ایران کجاست؟", "options": ["تهران", "اصفهان", "مشهد", "شیراز"], "answer": 0},
                {"question": "۲+۲ چند می‌شود؟", "options": ["۳", "۴", "۵", "۶"], "answer": 1},
                {"question": "بزرگ‌ترین اقیانوس کدام است؟", "options": ["اطلس", "هند", "آرام", "منجمد شمالی"], "answer": 2},
            ]
            
            question = random.choice(questions)
            keyboard = []
            
            for i, option in enumerate(question["options"]):
                keyboard.append([InlineKeyboardButton(option, callback_data=f"quiz_answer_{i}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            return {
                "question": question["question"],
                "reply_markup": reply_markup,
                "answer": question["answer"]
            }
        
        elif game_type == "riddle":
            riddles = [
                {"riddle": "چه چیزی دم در است اما خانه نیست؟", "answer": "کلید"},
                {"riddle": "چه چیزی همیشه به اسم بالا می‌آید اما هرگز پاییین نمی‌آید؟", "answer": "سن"},
                {"riddle": "چه چیزی چشم دارد اما نمی‌بیند؟", "answer": "سوزن"},
            ]
            
            riddle = random.choice(riddles)
            return f"🧩 معما: {riddle['riddle']}\n\n🤔 برای دیدن جواب، روی دکمه زیر کلیک کنید:"

    # 📱 ORIGINAL METHODS (Unchanged) 📱

    async def search_internet(self, query: str):
        try:
            url = f"https://duckduckgo.com/html/?q={query}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result')[:5]:
                title = result.find('a', class_='result__a')
                snippet = result.find('a', class_='result__snippet')
                
                if title:
                    title_text = title.get_text(strip=True)
                    link = title.get('href', '')
                    snippet_text = snippet.get_text(strip=True) if snippet else "بدون توضیحات"
                    results.append(f"🔗 {title_text}\n📝 {snippet_text}\n🌐 {link}\n")
            
            return "\n".join(results) if results else "نتیجه‌ای یافت نشد!"
        except Exception as e:
            return f"خطا در جستجو: {str(e)}"

    async def search_music(self, query: str):
        try:
            results = [
                f"🎵 {query} -Artist 1\n🔗 https://music.example.com/{query.replace(' ', '-')}-1",
                f"🎵 {query} -Artist 2\n🔗 https://music.example.com/{query.replace(' ', '-')}-2",
                f"🎵 {query} -Artist 3\n🔗 https://music.example.com/{query.replace(' ', '-')}-3",
            ]
            return "\n\n".join(results)
        except Exception as e:
            return f"خطا در جستجوی موسیقی: {str(e)}"

    async def get_weather(self, city: str):
        try:
            weather_data = {
                "tehran": {"temp": "28°C", "condition": "آفتابی", "humidity": "30%"},
                "mashhad": {"temp": "25°C", "condition": "نیمه‌ابری", "humidity": "40%"},
                "isfahan": {"temp": "26°C", "condition": "آفتابی", "humidity": "35%"},
                "shiraz": {"temp": "30°C", "condition": "آفتابی", "humidity": "25%"},
            }
            
            city_lower = city.lower()
            if city_lower in weather_data:
                data = weather_data[city_lower]
                return f"🌤️ **آب و هوای {city.title()}**\n\n🌡️ دما: {data['temp']}\n☁️ وضعیت: {data['condition']}\n💧 رطوبت: {data['humidity']}"
            else:
                return f"❌ شهر {city} یافت نشد. لطفاً شهر معتبر وارد کنید."
        except Exception as e:
            return f"خطا در دریافت آب و هوا: {str(e)}"

    async def get_crypto_price(self, symbol: str):
        try:
            prices = {
                "btc": {"price": "$45,000", "change": "+2.5%"},
                "eth": {"price": "$3,200", "change": "+1.8%"},
                "bnb": {"price": "$320", "change": "-0.5%"},
                "ada": {"price": "$1.20", "change": "+3.2%"},
                "sol": {"price": "$120", "change": "+4.1%"},
            }
            
            symbol_lower = symbol.lower()
            if symbol_lower in prices:
                data = prices[symbol_lower]
                return f"💰 **{symbol.upper()}**\n\n💵 قیمت: {data['price']}\n📈 تغییر: {data['change']}"
            else:
                return f"❌ ارز {symbol.upper()} یافت نشد. ارزهای موجود: BTC, ETH, BNB, ADA, SOL"
        except Exception as e:
            return f"خطا در دریافت قیمت: {str(e)}"

    async def create_sticker(self, text: str):
        try:
            img = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("fonts/arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2
            
            draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
        except Exception as e:
            print(f"Error creating sticker: {e}")
            return None

    async def search_products(self, product_name: str):
        try:
            products = [
                {
                    "name": f"{product_name} - برند A",
                    "price": "۱,۵۰۰,۰۰۰ تومان",
                    "rating": "۴.۵",
                    "link": f"https://shop.example.com/{product_name.replace(' ', '-')}-a"
                },
                {
                    "name": f"{product_name} - برند B",
                    "price": "۱,۲۰۰,۰۰۰ تومان",
                    "rating": "۴.۲",
                    "link": f"https://shop.example.com/{product_name.replace(' ', '-')}-b"
                },
                {
                    "name": f"{product_name} - برند C",
                    "price": "۱,۸۰۰,۰۰۰ تومان",
                    "rating": "۴.۸",
                    "link": f"https://shop.example.com/{product_name.replace(' ', '-')}-c"
                },
            ]
            
            results = []
            for product in products:
                results.append(f"🛍️ {product['name']}\n💰 قیمت: {product['price']}\n⭐ امتیاز: {product['rating']}\n🔗 {product['link']}\n")
            
            return "\n".join(results)
        except Exception as e:
            return f"خطا در جستجوی محصول: {str(e)}"

    async def get_coupons(self, category: str = None):
        try:
            if category:
                filtered_coupons = [c for c in self.coupons if c["category"] == category.lower()]
            else:
                filtered_coupons = self.coupons
            
            if not filtered_coupons:
                return "❌ کوپنی برای این دسته یافت نشد!"
            
            results = []
            for coupon in filtered_coupons:
                results.append(f"🎫 کد: {coupon['code']}\n💰 تخفیف: {coupon['discount']}\n📂 دسته: {coupon['category']}\n")
            
            return "\n".join(results)
        except Exception as e:
            return f"خطا در دریافت کوپن‌ها: {str(e)}"

    async def translate_text(self, text: str, target_lang: str = "en"):
        try:
            translations = {
                "en": f"Translation of '{text}' to English",
                "fa": f"ترجمه '{text}' به فارسی",
                "ar": f"ترجمة '{text}' إلى العربية",
                "es": f"Traducción de '{text}' al español",
            }
            
            if target_lang in translations:
                return translations[target_lang]
            else:
                return f"❌ زبان {target_lang} پشتیبانی نمی‌شود. زبان‌های موجود: en, fa, ar, es"
        except Exception as e:
            return f"خطا در ترجمه: {str(e)}"

    async def calculate(self, expression: str):
        try:
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                return "❌ عبارت نامعتبر است!"
            
            result = eval(expression)
            return f"🧮 نتیجه: {expression} = {result}"
        except Exception as e:
            return f"❌ خطا در محاسبه: {str(e)}"

    async def get_news(self, category: str = "general"):
        try:
            news = {
                "general": [
                    "📰 خبر مهم: اتفاق جدید در جهان رخ داده است",
                    "📰 تکنولوژی: شرکت بزرگ فناوری محصول جدیدی را عرضه کرد",
                    "📰 ورزشی: تیم مهمی در مسابقات پیروز شد",
                ],
                "tech": [
                    "🧠 هوش مصنوعی: پیشرفت‌های جدید در زمینه AI",
                    "📱 موبایل: گوشی جدید با قابلیت‌های فوق‌العاده",
                    "🌐 اینترنت: شبکه‌های اجتماعی با تغییرات جدید",
                ],
                "sports": [
                    "⚽ فوتبال: نتایج مهم هفته گذشته",
                    "🏀 بسکتبال: بازیکن ستاره رکورد جدید زد",
                    "🎾 تنیس: قهرمانی جدید مشخص شد",
                ],
            }
            
            if category in news:
                articles = news[category]
                return "\n\n".join(articles)
            else:
                return f"❌ دسته {category} یافت نشد. دسته‌های موجود: general, tech, sports"
        except Exception as e:
            return f"خطا در دریافت اخبار: {str(e)}"

# ایجاد نمونه از کلاس
bot_features = TelegramBotFeatures()