from services import ai
from utils.keyboards import send_message

def handle_sticker_input(chat_id, file_id, file_type):
    # در حالت ساده فقط پاسخی می‌دهیم
    send_message(chat_id, f"📥 فایل {file_type} دریافت شد (id={file_id})")
    # اینجا می‌تونیم به سرویس AI پاس بدیم یا روی تمپلیت اعمال کنیم
    # result = ai.apply_template("default", "متن تست")
    # ... ارسال فایل نهایی
