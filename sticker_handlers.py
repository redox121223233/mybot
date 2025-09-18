import os
import logging
import json
import tempfile
import requests
from PIL import Image
from io import BytesIO

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sticker_handlers")

# --- Sticker Maker Handlers ---

def handle_sticker_maker_toggle(chat_id, message_id=None, ai_manager=None, api=None):
    """فعال یا غیرفعال کردن استیکرساز"""
    if not ai_manager:
        api.send_message(chat_id, "⚠️ سیستم استیکرساز در دسترس نیست.")
        return
    
    # فعال یا غیرفعال کردن استیکرساز
    is_enabled = ai_manager.toggle_ai()
    
    # ارسال پیام مناسب
    if is_enabled:
        # دریافت پیام خوش‌آمدگویی
        greeting = ai_manager.get_greeting()
        api.send_message(chat_id, f"✅ استیکرساز فعال شد!\n\n{greeting}")
    else:
        api.send_message(chat_id, "❌ استیکرساز غیرفعال شد.")

def handle_sticker_maker_input(chat_id, input_data, input_type, message_id=None, caption=None, ai_manager=None, api=None):
    """پردازش ورودی برای استیکرساز"""
    if not ai_manager:
        return
    
    # بررسی فعال بودن استیکرساز
    if not ai_manager.enabled:
        return
    
    # پردازش ورودی توسط استیکرساز
    sticker_data, response_text = ai_manager.process_input(input_data, input_type, chat_id, caption)
    
    # اگر پاسخی وجود دارد، آن را نمایش بده
    if response_text:
        # ایجاد دکمه‌های تأیید و لغو
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ بله، بساز", "callback_data": f"sticker_confirm"},
                    {"text": "❌ خیر", "callback_data": f"sticker_cancel"}
                ]
            ]
        }
        
        # اضافه کردن دکمه‌های انتخاب سبک
        styles = ai_manager.get_available_styles()
        style_buttons = []
        for style in styles:
            style_buttons.append({"text": f"🎨 {style}", "callback_data": f"sticker_style_{style}"})
        
        # اضافه کردن دکمه‌های سبک به صورت ردیفی (حداکثر 3 دکمه در هر ردیف)
        style_rows = []
        for i in range(0, len(style_buttons), 3):
            style_rows.append(style_buttons[i:i+3])
        
        keyboard["inline_keyboard"] = style_rows + keyboard["inline_keyboard"]
        
        send_message(chat_id, response_text, reply_to=message_id, reply_markup=json.dumps(keyboard))

def handle_sticker_confirm(chat_id, callback_query_id, message_id=None, ai_manager=None, answer_callback_query=None, edit_message=None):
    """تأیید ساخت استیکر"""
    if not ai_manager:
        answer_callback_query(callback_query_id, "⚠️ سیستم استیکرساز در دسترس نیست.")
        return
    
    # ساخت استیکر
    sticker_data, response_text = ai_manager.confirm_sticker_creation(chat_id)
    
    # پاسخ به کالبک کوئری
    answer_callback_query(callback_query_id, "در حال ساخت استیکر...")
    
    if sticker_data:
        # ارسال استیکر
        send_sticker_from_data(chat_id, sticker_data, ai_manager.bot_token)
        # ارسال پیام موفقیت
        edit_message(chat_id, message_id, response_text)
    else:
        # ارسال پیام خطا
        edit_message(chat_id, message_id, response_text or "خطا در ساخت استیکر.")

def handle_sticker_cancel(chat_id, callback_query_id, message_id=None, ai_manager=None, answer_callback_query=None, edit_message=None):
    """لغو ساخت استیکر"""
    if not ai_manager:
        answer_callback_query(callback_query_id, "⚠️ سیستم استیکرساز در دسترس نیست.")
        return
    
    # لغو ساخت استیکر
    response = ai_manager.cancel_sticker_creation(chat_id)
    
    # پاسخ به کالبک کوئری
    answer_callback_query(callback_query_id, "درخواست لغو شد.")
    
    # ویرایش پیام
    edit_message(chat_id, message_id, response)

def handle_sticker_style(chat_id, callback_query_id, style, message_id=None, ai_manager=None, answer_callback_query=None, edit_message=None):
    """انتخاب سبک استیکر"""
    if not ai_manager:
        answer_callback_query(callback_query_id, "⚠️ سیستم استیکرساز در دسترس نیست.")
        return
    
    # پاسخ به کالبک کوئری
    answer_callback_query(callback_query_id, f"سبک {style} انتخاب شد.")
    
    # ساخت استیکر با سبک انتخاب شده
    sticker_data, response_text = ai_manager.confirm_sticker_creation(chat_id, style)
    
    if sticker_data:
        # ارسال استیکر
        send_sticker_from_data(chat_id, sticker_data, ai_manager.bot_token)
        # ارسال پیام موفقیت
        edit_message(chat_id, message_id, response_text)
    else:
        # ارسال پیام خطا
        edit_message(chat_id, message_id, response_text or "خطا در ساخت استیکر.")

def send_sticker_from_data(chat_id, sticker_data, bot_token):
    """ارسال استیکر از داده‌های باینری"""
    try:
        # ذخیره موقت فایل استیکر
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as temp_file:
            temp_path = temp_file.name
            # تبدیل تصویر به فرمت WebP
            image = Image.open(BytesIO(sticker_data))
            image.save(temp_path, format='WEBP')
        
        # ارسال استیکر
        files = {'sticker': open(temp_path, 'rb')}
        data = {'chat_id': chat_id}
        API = f"https://api.telegram.org/bot{bot_token}/"
        response = requests.post(f"{API}sendSticker", files=files, data=data)
        
        # حذف فایل موقت
        os.unlink(temp_path)
        
        return response.json().get('ok', False)
    except Exception as e:
        logger.error(f"Error sending sticker: {e}")
        return False

def get_file(file_id, bot_token):
    """دریافت فایل از تلگرام"""
    try:
        API = f"https://api.telegram.org/bot{bot_token}/"
        # دریافت اطلاعات فایل
        file_info = requests.get(f"{API}getFile?file_id={file_id}").json()
        if not file_info.get('ok'):
            logger.error(f"Error getting file info: {file_info}")
            return None
        
        file_path = file_info.get('result', {}).get('file_path')
        if not file_path:
            logger.error("No file path in response")
            return None
        
        # دانلود فایل
        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        response = requests.get(file_url)
        if response.status_code != 200:
            logger.error(f"Error downloading file: {response.status_code}")
            return None
        
        return BytesIO(response.content)
    except Exception as e:
        logger.error(f"Error in get_file: {e}")
        return None

def create_sticker_from_text(text, template_id=None, font_name=None, font_size=None, font_color=None, bg_color=None):
    """ساخت استیکر از متن"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import arabic_reshaper
        from bidi.algorithm import get_display
        import os
        import random
        
        # تنظیمات پیش‌فرض
        if not font_name:
            # انتخاب یک فونت فارسی تصادفی
            fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
            available_fonts = [f for f in os.listdir(fonts_dir) if f.endswith('.ttf')]
            if available_fonts:
                font_name = os.path.join(fonts_dir, random.choice(available_fonts))
            else:
                font_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arial.ttf')
        
        if not font_size:
            font_size = 60
        
        if not font_color:
            font_color = (255, 255, 255)  # سفید
        
        if not bg_color:
            bg_color = (0, 0, 0, 0)  # شفاف
        
        # اندازه استیکر
        width, height = 512, 512
        
        # ایجاد تصویر
        if template_id:
            # استفاده از قالب
            templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
            template_file = os.path.join(templates_dir, f"{template_id}_bg.png")
            if not os.path.exists(template_file):
                template_file = os.path.join(templates_dir, f"{template_id}_bg.jpg")
            
            if os.path.exists(template_file):
                img = Image.open(template_file).convert("RGBA")
                img = img.resize((width, height))
            else:
                img = Image.new('RGBA', (width, height), bg_color)
        else:
            img = Image.new('RGBA', (width, height), bg_color)
        
        # ایجاد شیء طراحی
        draw = ImageDraw.Draw(img)
        
        # بارگذاری فونت
        font = ImageFont.truetype(font_name, font_size)
        
        # تبدیل متن فارسی به شکل صحیح
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        
        # محاسبه اندازه متن
        text_width, text_height = draw.textsize(bidi_text, font=font)
        
        # محاسبه موقعیت متن (وسط تصویر)
        position = ((width - text_width) / 2, (height - text_height) / 2)
        
        # رسم متن روی تصویر
        draw.text(position, bidi_text, font=font, fill=font_color)
        
        # تبدیل تصویر به بایت‌ها
        from io import BytesIO
        output = BytesIO()
        img.save(output, format='PNG')
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error creating sticker from text: {e}")
        return None

def process_callback_query(callback_query, ai_manager=None, answer_callback_query=None, edit_message=None):
    """پردازش کالبک کوئری‌های مربوط به استیکرساز"""
    query_id = callback_query.get('id')
    chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
    message_id = callback_query.get('message', {}).get('message_id')
    data = callback_query.get('data', '')
    
    # پردازش دکمه‌های استیکرساز
    if data == 'sticker_confirm':
        handle_sticker_confirm(chat_id, query_id, message_id, ai_manager, answer_callback_query, edit_message)
        return True
    elif data == 'sticker_cancel':
        handle_sticker_cancel(chat_id, query_id, message_id, ai_manager, answer_callback_query, edit_message)
        return True
    elif data.startswith('sticker_style_'):
        style = data.replace('sticker_style_', '')
        handle_sticker_style(chat_id, query_id, style, message_id, ai_manager, answer_callback_query, edit_message)
        return True
    elif data == 'sticker_toggle':
        # این مورد باید در فایل اصلی ربات پردازش شود
        return False
        
    # اگر کالبک کوئری مربوط به استیکرساز نبود
    return False
