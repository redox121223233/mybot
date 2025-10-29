import random
import asyncio
from typing import Dict, List
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# بازی‌ها و سرگرمی‌ها
games_router = Router()

# ذخیره وضعیت بازی‌ها
game_sessions: Dict[int, Dict] = {}

# کلمات برای بازی حدس کلمه
WORD_GAMES = {
    'easy': [
        {'word': 'گربه', 'hint': 'حیوان خانگی، موش‌گیر', 'category': 'حیوانات'},
        {'word': 'ماشین', 'hint': 'وسیله نقلیه، چهار چرخ', 'category': 'وسایل نقلیه'},
        {'word': 'سیب', 'hint': 'میوه، قرمز یا سبز', 'category': 'میوه‌ها'},
        {'word': 'کتاب', 'hint': 'برای خواندن،纸质品', 'category': 'اشیاء'},
        {'word': 'آفتاب', 'hint': 'منبع نور و گرما', 'category': 'طبیعت'}
    ],
    'medium': [
        {'word': 'پایتخت', 'hint': 'مرکز یک کشور', 'category': 'جغرافیا'},
        {'word': 'کامپیوتر', 'hint': 'دستگاه الکترونیکی هوشمند', 'category': 'تکنولوژی'},
        {'word': 'دوچرخه', 'hint': 'وسیله نقلیه بدون موتور، دو چرخ', 'category': 'وسایل نقلیه'},
        {'word': 'کشاورز', 'hint': 'شخصی که در مزرعه کار می‌کند', 'category': 'مشاغل'},
        {'word': 'کوهنوردی', 'hint': 'ورزش صعود به قله‌ها', 'category': 'ورزش‌ها'}
    ],
    'hard': [
        {'word': 'فلسفه', 'hint': 'علم تفکر و اندیشه', 'category': 'علوم'},
        {'word': 'تکنولوژی', 'hint': 'دانش کاربردی علمی', 'category': 'علوم'},
        {'word': 'روانشناسی', 'hint': 'علم مطالعه رفتار و ذهن', 'category': 'علوم'},
        {'word': 'معماری', 'hint': 'هنر ساختمان‌سازی', 'category': 'هنر'},
        {'word': 'دانشگاه', 'hint': 'مرکز آموزش عالی', 'category': 'آموزش'}
    ]
}

# جوک‌ها و لطیفه‌ها
JOKES = [
    "چرا ریاضیات دان غمگین بود؟ چون خیلی مسائل داشت! 😄",
    "معلم به دانش‌آموز: چرا توی امتحان خواب بودی؟\nدانش‌آموز: چون ذهنم در حال استراحت بود! 😴",
    "یک روز گوجه به گوجه دیگر گفت: چرا قرمز شدی؟\nگفت: دیدم خیار سبز شده، خجالت کشیدم! 🍅😊",
    "چرا ماهی به پول نرسید؟ چون همیشه تو آب بود! 🐠💰",
    "مردم به دکتر گفتند: دکتر ما فراموشکار شدیم!\nدکتر گفت: کی؟\nمردم گفتند: چی؟\nدکتر گفت: کی؟ 🤔"
]

# معماها
RIDDLES = [
    {'question': 'چه چیزی همیشه جلو می‌رود ولی هرگز به جایی نمی‌رسد؟', 'answer': 'زمان'},
    {'question': 'چه چیزی دهان دارد ولی صحبت نمی‌کند؟', 'answer': 'رودخانه'},
    {'question': 'چه چیزی سر دارد ولی گردن ندارد؟', 'answer': 'سکه'},
    {'question': 'چه چیزی می‌تواند پرواز کند ولی بال ندارد؟', 'answer': 'ابر'},
    {'question': 'چه چیزی شب‌ها می‌خوابد ولی روزها بیدار است؟', 'answer': 'ستاره'}
]

def games_menu_kb():
    """ساخت کیبورد منوی بازی‌ها"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 حدس کلمه", callback_data="game:word_guess")
    kb.button(text="🎲 عدد شانس", callback_data="game:lucky_number") 
    kb.button(text="🧩 معما", callback_data="game:riddle")
    kb.button(text="😂 جوک روز", callback_data="game:joke")
    kb.button(text="📚 اطلاعات جالب", callback_data="game:fun_fact")
    kb.button(text="🔙 بازگشت به منوی اصلی", callback_data="menu:home")
    kb.adjust(2, 2, 2)
    return kb.as_markup()

def word_guess_difficulty_kb():
    """ساخت کیبورد سخت بازی حدس کلمه"""
    kb = InlineKeyboardBuilder()
    kb.button(text="😊 آسان", callback_data="word_guess:easy")
    kb.button(text="😐 متوسط", callback_data="word_guess:medium")
    kb.button(text="😈 سخت", callback_data="word_guess:hard")
    kb.button(text="🔙 بازگشت", callback_data="game:menu")
    kb.adjust(2, 2)
    return kb.as_markup()

def word_guess_game_kb(word: str, attempts_left: int):
    """ساخت کیبورد بازی حدس کلمه"""
    kb = InlineKeyboardBuilder()
    
    # دکمه‌های الفبا (فارسی و انگلیسی)
    persian_letters = ['ا', 'ب', 'پ', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'ژ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی']
    english_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    
    # تشخیص زبان کلمه
    if any(char in word for char in persian_letters):
        letters = persian_letters
    else:
        letters = english_letters
    
    # اضافه کردن دکمه‌های حروف
    for i, letter in enumerate(letters):
        if i % 6 == 0 and i > 0:
            kb.adjust(6)
        kb.button(text=letter, callback_data=f"guess_letter:{letter}")
    
    kb.button(text="🔁 انصراف", callback_data="game:menu")
    kb.adjust(6)
    return kb.as_markup()

@games_router.callback_query(F.data == "game:menu")
async def on_game_menu(cb: CallbackQuery, bot: Bot):
    """نمایش منوی بازی‌ها"""
    await cb.message.edit_text(
        "🎮 **منوی بازی و سرگرمی**\n\n"
        "یکی از بازی‌های زیر را انتخاب کنید:",
        reply_markup=games_menu_kb()
    )
    await cb.answer()

@games_router.callback_query(F.data == "game:word_guess")
async def on_word_guess_start(cb: CallbackQuery, bot: Bot):
    """شروع بازی حدس کلمه"""
    await cb.message.edit_text(
        "🎯 **بازی حدس کلمه**\n\n"
        "سختی بازی را انتخاب کنید:",
        reply_markup=word_guess_difficulty_kb()
    )
    await cb.answer()

@games_router.callback_query(F.data.startswith("word_guess:"))
async def on_word_guess_difficulty(cb: CallbackQuery, bot: Bot):
    """شروع بازی حدس کلمه با سختی مشخص"""
    difficulty = cb.data.split(":")[1]
    uid = cb.from_user.id
    
    # انتخاب کلمه تصادفی
    word_data = random.choice(WORD_GAMES[difficulty])
    word = word_data['word']
    hint = word_data['hint']
    category = word_data['category']
    
    # ذخیره وضعیت بازی
    game_sessions[uid] = {
        'type': 'word_guess',
        'word': word,
        'hint': hint,
        'category': category,
        'difficulty': difficulty,
        'attempts_left': 6,
        'guessed_letters': set(),
        'wrong_guesses': []
    }
    
    # نمایش کلمه با خط تیره
    display_word = ''.join(['_' if char != ' ' else ' ' for char in word])
    
    difficulty_emoji = {'easy': '😊', 'medium': '😐', 'hard': '😈'}
    
    await cb.message.edit_text(
        f"🎯 **حدس کلمه - {difficulty_emoji[difficulty]}**\n\n"
        f"📂 دسته: {category}\n"
        f"💭 راهنمایی: {hint}\n"
        f"🎯 کلمه: {display_word}\n"
        f"❤️ فرصت باقی‌مانده: {game_sessions[uid]['attempts_left']}\n\n"
        f"یک حرف حدس بزنید:",
        reply_markup=word_guess_game_kb(word, game_sessions[uid]['attempts_left'])
    )
    await cb.answer()

@games_router.callback_query(F.data.startswith("guess_letter:"))
async def on_guess_letter(cb: CallbackQuery, bot: Bot):
    """حدس زدن حرف در بازی حدس کلمه"""
    uid = cb.from_user.id
    letter = cb.data.split(":")[1]
    
    if uid not in game_sessions or game_sessions[uid]['type'] != 'word_guess':
        await cb.answer("بازی فعال نیست!", show_alert=True)
        return
    
    game = game_sessions[uid]
    
    if letter in game['guessed_letters']:
        await cb.answer("این حرف را قبلاً امتحان کردید!", show_alert=True)
        return
    
    game['guessed_letters'].add(letter)
    
    if letter in game['word']:
        # حرف درست حدس زده شد
        display_word = ''.join([
            char if char in game['guessed_letters'] or char == ' ' else '_' 
            for char in game['word']
        ])
        
        # بررسی برنده شدن
        if '_' not in display_word:
            del game_sessions[uid]
            await cb.message.edit_text(
                f"🎉 **تبریک! شما برنده شدید!** 🎉\n\n"
                f"کلمه: {game['word']}\n"
                f"🏆 امتیاز شما: +{10 * len(game['word'])}\n\n"
                f"برای بازی دیگر منوی بازی را انتخاب کنید:",
                reply_markup=games_menu_kb()
            )
            await cb.answer()
            return
    else:
        # حرف اشتباه حدس زده شد
        game['wrong_guesses'].append(letter)
        game['attempts_left'] -= 1
        
        display_word = ''.join([
            char if char in game['guessed_letters'] or char == ' ' else '_' 
            for char in game['word']
        ])
        
        # بررسی بازنده شدن
        if game['attempts_left'] <= 0:
            del game_sessions[uid]
            await cb.message.edit_text(
                f"😢 **متاسفانه شما باختید!** 😢\n\n"
                f"کلمه: {game['word']}\n"
                f"حروف اشتباه: {', '.join(game['wrong_guesses'])}\n\n"
                f"برای بازی دیگر منوی بازی را انتخاب کنید:",
                reply_markup=games_menu_kb()
            )
            await cb.answer()
            return
    
    difficulty_emoji = {'easy': '😊', 'medium': '😐', 'hard': '😈'}
    
    await cb.message.edit_text(
        f"🎯 **حدس کلمه - {difficulty_emoji[game['difficulty']}**\n\n"
        f"📂 دسته: {game['category']}\n"
        f"💭 راهنمایی: {game['hint']}\n"
        f"🎯 کلمه: {display_word}\n"
        f"❤️ فرصت باقی‌مانده: {game['attempts_left']}\n"
        f"❌ حروف اشتباه: {', '.join(game['wrong_guesses']) if game['wrong_guesses'] else 'هیچ'}\n\n"
        f"یک حرف حدس بزنید:",
        reply_markup=word_guess_game_kb(game['word'], game['attempts_left'])
    )
    await cb.answer()

@games_router.callback_query(F.data == "game:lucky_number")
async def on_lucky_number(cb: CallbackQuery, bot: Bot):
    """بازی عدد شانس"""
    uid = cb.from_user.id
    
    # انتخاب عدد تصادفی 1 تا 100
    lucky_number = random.randint(1, 100)
    user_lucky = random.randint(1, 100)
    
    if lucky_number == user_lucky:
        result_text = "🎉 **شما برنده شدید!** 🎉\n\n"
        prize = random.choice(["🎁 جایزه ویژه", "💎 امتیاز دو برابر", "⭐ ستاره طلایی"])
        result_text += f"عدد شانس: {lucky_number}\n"
        result_text += f"عدد شما: {user_lucky}\n"
        result_text += f"🎁 {prize}"
    else:
        result_text = "😊 **امتحان دوباره!** 😊\n\n"
        result_text += f"عدد شانس: {lucky_number}\n"
        result_text += f"عدد شما: {user_lucky}\n"
        result_text += "فاصله شما با برد: " + str(abs(lucky_number - user_lucky))
    
    await cb.message.edit_text(
        f"🎲 **بازی عدد شانس**\n\n"
        f"{result_text}\n\n"
        f"برای بازی دیگر منوی بازی را انتخاب کنید:",
        reply_markup=games_menu_kb()
    )
    await cb.answer()

@games_router.callback_query(F.data == "game:riddle")
async def on_riddle(cb: CallbackQuery, bot: Bot):
    """بازی معما"""
    riddle = random.choice(RIDDLES)
    uid = cb.from_user.id
    
    # ذخیره معما فعلی
    game_sessions[uid] = {
        'type': 'riddle',
        'riddle': riddle,
        'attempts': 0
    }
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 پاسخم را بگویم", callback_data="riddle_answer")
    kb.button(text="🔁 معمای دیگر", callback_data="game:riddle")
    kb.button(text="🔙 بازگشت", callback_data="game:menu")
    kb.adjust(1, 2)
    
    await cb.message.edit_text(
        f"🧩 **معمای امروز** 🧩\n\n"
        f"❓ {riddle['question']}\n\n"
        f"به فکر باشید... 😊",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@games_router.callback_query(F.data == "riddle_answer")
async def on_riddle_answer(cb: CallbackQuery, bot: Bot):
    """پاسخ به معما"""
    uid = cb.from_user.id
    
    if uid not in game_sessions or game_sessions[uid]['type'] != 'riddle':
        await cb.answer("معمای فعالی وجود ندارد!", show_alert=True)
        return
    
    riddle = game_sessions[uid]['riddle']
    del game_sessions[uid]
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🧩 معمای دیگر", callback_data="game:riddle")
    kb.button(text="🔙 بازگشت", callback_data="game:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"🧩 **پاسخ معما** 🧩\n\n"
        f"❓ {riddle['question']}\n\n"
        f"💡 **پاسخ:** {riddle['answer']}\n\n"
        f"چقدر هوشمند بودید؟ 🧠✨",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@games_router.callback_query(F.data == "game:joke")
async def on_joke(cb: CallbackQuery, bot: Bot):
    """نمایش جوک روز"""
    joke = random.choice(JOKES)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="😂 جوک دیگر", callback_data="game:joke")
    kb.button(text="🔙 بازگشت", callback_data="game:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"😂 **جوک امروز** 😂\n\n"
        f"{joke}\n\n"
        f"خندیدنی بود؟ 😄",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@games_router.callback_query(F.data == "game:fun_fact")
async def on_fun_fact(cb: CallbackQuery, bot: Bot):
    """نمایش اطلاعات جالب"""
    fun_facts = [
        "🧠 مغز انسان حدود 2% از وزن بدن را تشکیل می‌دهد ولی 20% از اکسیژن را مصرف می‌کند!",
        "🌍 زمین تنها سیاره‌ای در منظومه شمسی است که به نام یک خدای گیرس گرفته نشده است!",
        "🐘 فیل‌ها تنها حیواناتی هستند که نمی‌توانند بپرند! (و البته نمی‌خواهند بپرند!)",
        "⏹️ زمان در سیاهچاله متوقف می‌شود!",
        "🍯 عسل فاسد نمی‌شود - در مقابر مصر با قدمت 3000 سال عسل قابل خورش پیدا شده است!",
        "🌙 ماه هر سال حدود 3.8 سانتی‌متر از زمین دور می‌شود!",
        "🐧 پنگوئن‌ها می‌توانند تا سرعت 35 کیلومتر در ساعت شنا کنند!",
        "🎵 موسیقی می‌تواند به کاهش درد و اضطراب کمک کند!",
        "🌈 رنگ قرمز در rainbow اولین رنگی است که چشم انسان در نوزادی تشخیص می‌دهد!",
        "⚡ صاعقه می‌تواند دمای 30000 درجه سانتی‌گراد داشته باشد - 5 برابر دمای سطح خورشید!"
    ]
    
    fact = random.choice(fun_facts)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 اطلاعات دیگر", callback_data="game:fun_fact")
    kb.button(text="🔙 بازگشت", callback_data="game:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"📚 **اطلاعات جالب امروز** 📚\n\n"
        f"{fact}\n\n"
        f"جالب نبود؟ 🤓✨",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

# تابع برای اضافه کردن به ربات اصلی
def get_games_router():
    """روتر بازی‌ها را برمی‌گرداند"""
    return games_router