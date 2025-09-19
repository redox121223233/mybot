from utils.telegram_api import send_message
def handle_trial_activation(chat_id, message_id=None):
    send_message(chat_id, "✅ دوره آزمایشی فعال شد (نمونه).")
def show_subscription_menu(chat_id, message_id=None):
    send_message(chat_id, "💎 منوی اشتراک: پلن 1 - 1 ماه - 100")
def handle_subscription_purchase(chat_id, plan_id, message_id=None):
    send_message(chat_id, f"درخواست خرید پلن {plan_id} دریافت شد.")
def handle_template_selection(chat_id, template_id, message_id=None):
    send_message(chat_id, f"قالب {template_id} انتخاب شد.")
