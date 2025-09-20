import logging
from services import legacy as legacy_services

logger = logging.getLogger(__name__)

# ذخیره وضعیت کاربران
USER_STATE = {}

def handle_message(msg):
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    chat_id = msg["chat"]["id"]

    logger.info(f"handle_message {user_id}: {text}")

    # وضعیت جاری کاربر
    state = USER_STATE.get(user_id, {"step": None, "data": {}})

    # ---------- شروع ربات ----------
    if text == "/start":
        show_main_menu(chat_id)
        USER_STATE[user_id] = {"step": None, "data": {}}
        return

    # ---------- منوی اصلی ----------
    if text == "🎭 استیکرساز":
        legacy_services.api.send_message(chat_id, "📝 اسم پک استیکر رو وارد کن:", reply_markup=back_button())
        USER_STATE[user_id] = {"step": "await_pack_name", "data": {}}
        return

    if text == "🤖 هوش مصنوعی":
        legacy_services.api.send_message(chat_id, "📸 متنتو یا عکستو بفرست، بگو چطور طراحی بشه.", reply_markup=back_button())
        USER_STATE[user_id] = {"step": "ai_input", "data": {}}
        return

    if text == "⭐ اشتراک":
        legacy_services.api.send_message(chat_id, "🔑 بخش اشتراک هنوز در حال توسعه‌ست.", reply_markup=back_button())
        return

    if text == "🎁 تست رایگان":
        legacy_services.api.send_message(chat_id, "🎉 تست رایگان فعال شد! از منو استفاده کن.", reply_markup=back_button())
        return

    if text == "ℹ️ درباره ما":
        legacy_services.api.send_message(chat_id, "👨‍💻 ساخته شده توسط REDOX", reply_markup=back_button())
        return

    # ---------- دکمه بازگشت ----------
    if text == "🔙 بازگشت":
        show_main_menu(chat_id)
        USER_STATE[user_id] = {"step": None, "data": {}}
        return

    # ---------- استیکرساز ----------
    if state["step"] == "await_pack_name":
        state["data"]["pack_name"] = text
        USER_STATE[user_id] = {"step": "await_photo", "data": state["data"]}
        legacy_services.api.send_message(chat_id, "📸 حالا عکس استیکر رو بفرست.", reply_markup=back_button())
        return

    if state["step"] == "await_photo" and "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        state["data"]["file_id"] = file_id
        USER_STATE[user_id] = {"step": "await_text", "data": state["data"]}
        legacy_services.api.send_message(chat_id, "✍️ حالا متن استیکر رو بفرست.", reply_markup=back_button())
        return

    if state["step"] == "await_text":
        text_on_sticker = text
        pack_name = state["data"].get("pack_name")
        file_id = state["data"].get("file_id")

        if not pack_name or not file_id:
            legacy_services.api.send_message(chat_id, "❌ خطا! دوباره از اول شروع کن.", reply_markup=back_button())
            return

        # ساخت استیکر
        try:
            sticker_path = legacy_services.sticker_manager.create_sticker(file_id, text_on_sticker, pack_name)
            legacy_services.api.send_photo(chat_id, sticker_path, caption=f"✅ استیکر ساخته شد ({pack_name})")
        except Exception as e:
            logger.error(f"خطا در ساخت استیکر: {e}")
            legacy_services.api.send_message(chat_id, "❌ مشکلی پیش اومد. دوباره تلاش کن.")

        USER_STATE[user_id] = {"step": None, "data": {}}
        return

    # ---------- هوش مصنوعی ----------
    if state["step"] == "ai_input":
        # فعلاً فقط متن رو تکرار می‌کنیم (بعداً AIManager وصل می‌کنیم)
        legacy_services.api.send_message(chat_id, f"🤖 پردازش شد: {text}", reply_markup=back_button())
        USER_STATE[user_id] = {"step": None, "data": {}}
        return

    # ---------- پیش‌فرض ----------
    legacy_services.api.send_message(chat_id, "متوجه نشدم. از منوی اصلی استفاده کنید.", reply_markup=main_menu())


# ---------- منوها ----------
def main_menu():
    return {
        "keyboard": [
            ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
            ["⭐ اشتراک", "🎁 تست رایگان"],
            ["ℹ️ درباره ما"]
        ],
        "resize_keyboard": True
    }

def back_button():
    return {
        "keyboard": [["🔙 بازگشت"]],
        "resize_keyboard": True
    }

def show_main_menu(chat_id):
    legacy_services.api.send_message(chat_id, "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:", reply_markup=main_menu())
