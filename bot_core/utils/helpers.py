from datetime import datetime, timezone
from typing import Dict, Any
import re
from ..config import DAILY_LIMIT

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    return int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())

def _reset_daily_if_needed(u: Dict[str, Any]):
    if u.get("day_start", 0) < _today_start_ts():
        u["day_start"] = _today_start_ts()
        u["ai_used"] = 0

def _quota_left(u: Dict[str, Any], is_admin: bool) -> int:
    if is_admin:
        return 999999
    _reset_daily_if_needed(u)
    limit = u.get("daily_limit") or DAILY_LIMIT
    return max(0, limit - u.get("ai_used", 0))

def _seconds_to_reset(u: Dict[str, Any]) -> int:
    _reset_daily_if_needed(u)
    now = int(datetime.now(timezone.utc).timestamp())
    end_of_day = u["day_start"] + 86400
    return max(0, end_of_day - now)

def _fmt_eta(secs: int) -> str:
    h, m = divmod(secs, 3600)
    m //= 60
    if h > 0:
        return f"{h} ساعت و {m} دقیقه"
    if m > 0:
        return f"{m} دقیقه"
    return "کمتر از یک دقیقه"

def is_valid_pack_name(name: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9_]{0,49}(?<!_)(?<!__)$", name))
