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

class TelegramBotFeatures:
    def __init__(self):
        self.user_data = {}
        self.coupons = self.load_coupons()
        self.music_data = self.load_music_data()
        self.api_key = os.getenv('API_KEY', 'your_default_api_key')
    
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
            # شبیه‌سازی جستجوی موسیقی
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
            # شبیه‌سازی دریافت آب و هوا
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
            # شبیه‌سازی قیمت ارز دیجیتال
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
            # ایجاد تصویر استیکر
            img = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # تلاش برای استفاده از فونت فارسی
            try:
                font = ImageFont.truetype("fonts/arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            # محاسبه موقعیت متن
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2
            
            # رسم متن
            draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)
            
            # ذخیره تصویر
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
        except Exception as e:
            print(f"Error creating sticker: {e}")
            return None
    
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
                {"riddle": "چه چیزی همیشه به سمت بالا می‌رود اما هرگز پایین نمی‌آید؟", "answer": "سن"},
                {"riddle": "چه چیزی چشم دارد اما نمی‌بیند؟", "answer": "سوزن"},
            ]
            
            riddle = random.choice(riddles)
            return f"🧩 معما: {riddle['riddle']}\n\n💭 برای دیدن جواب، روی دکمه زیر کلیک کنید:"
    
    async def search_products(self, product_name: str):
        try:
            # شبیه‌سازی جستجوی محصول
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
            # شبیه‌سازی ترجمه
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
            # محاسبه امن
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                return "❌ عبارت نامعتبر است!"
            
            result = eval(expression)
            return f"🧮 نتیجه: {expression} = {result}"
        except Exception as e:
            return f"❌ خطا در محاسبه: {str(e)}"
    
    async def get_news(self, category: str = "general"):
        try:
            # شبیه‌سازی دریافت اخبار
            news = {
                "general": [
                    "📰 خبر مهم: اتفاق جدید در جهان رخ داده است",
                    "📰 تکنولوژی: شرکت بزرگ فناوری محصول جدیدی را عرضه کرد",
                    "📰 ورزشی: تیم مهمی در مسابقات پیروز شد",
                ],
                "tech": [
                    "💻 هوش مصنوعی: پیشرفت‌های جدید در زمینه AI",
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