def main_menu_markup():
    return {"keyboard":[[{"text":"🎁 تست رایگان"},{"text":"⭐ اشتراک"}],[{"text":"🎭 استیکرساز"}]], "resize_keyboard":True}

def welcome_inline_markup():
    keyboard = [
        [{"text":"✨ ساخت استیکر جدید","callback_data":"new_sticker"},{"text":"📚 قالب‌های آماده","callback_data":"show_templates"}],
        [{"text":"💎 خرید اشتراک","callback_data":"show_subscription"},{"text":"🎁 تست رایگان","callback_data":"show_free_trial"}]
    ]
    return {"inline_keyboard": keyboard}
