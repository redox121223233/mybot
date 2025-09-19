from utils.logger import logger
try:
    from services import legacy
    cb_fn = getattr(legacy, "handle_callback_query", None) or getattr(legacy, "handle_callback", None)
except Exception:
    legacy = None
    cb_fn = None

def handle_callback(cb):
    if cb_fn:
        try:
            return cb_fn(cb)
        except Exception as e:
            logger.error("Error in legacy callback handler: %s", e)
    # fallback
    try:
        from utils.telegram_api import answer_callback_query, send_message
        cid = cb.get("message",{}).get("chat",{}).get("id")
        answer_callback_query(cb.get("id"), "عملیات انجام شد")
    except:
        pass
    return "ok"
