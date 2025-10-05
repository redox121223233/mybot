import asyncio
import threading
import traceback
from typing import Awaitable, Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    if _loop and _loop.is_running():
        return _loop
    with _lock:
        if _loop and _loop.is_running():
            return _loop
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=_run_loop, args=(loop,), daemon=True)
        thread.start()
        _loop = loop
        _thread = thread
        return loop


def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def submit(coro: Awaitable) -> asyncio.Future:
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    future.add_done_callback(_handle_future_error)
    return future


def run_sync(coro: Awaitable):
    return submit(coro).result()


def _handle_future_error(future: asyncio.Future) -> None:
    try:
        future.result()
    except Exception as exc:  # pragma: no cover - logging only
        print(f"Async task failed: {exc}")
        traceback.print_exc()
