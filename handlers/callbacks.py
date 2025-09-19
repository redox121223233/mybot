
from utils.logger import logger
from services import legacy as legacy_services

api = legacy_services.api
subscription_manager = legacy_services.subscription_manager

def handle_callback(cb):
    data = cb.get("data")
    from_id = cb.get("from", {}).get("id")
    logger.info("handle_callback %s: %s", from_id, data)

    if data == "buy_sub":
        api.send_message(from_id, "برای خرید اشتراک راهنمایی ...")
    elif data == "check_sub":
        sub = subscription_manager.get_subscription(from_id)
        if sub:
            api.send_message(from_id, f"اشتراک شما: {sub}")
        else:
            api.send_message(from_id, "اشتراک فعالی ندارید.")
    else:
        api.answer_callback_query(cb.get("id"), "عملیات نامشخص.")
