"""Built-in non-source tools the agent always has: clock + timer.

Both are kept tiny and free-functioned (no closures over agent state) because
ADK Live's tool-count budget is small — we already spend slots on memory +
coral_query. These two need no I/O surface beyond the OS clock + osascript.
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta

from reef.observability import trace
from reef.shell.notify import notify


def get_current_time() -> str:
    """Return the current local date and time (e.g. for 'what time is it?')."""
    return datetime.now().strftime("%A %d %B %Y, %H:%M")


def set_timer(minutes: int) -> str:
    """Set a timer for N minutes. When it fires, the user gets a macOS
    notification AND a trace line in the chat timeline.

    `minutes=0` is allowed and treated as ~1 second (useful for demos / tests).
    """
    secs = max(1, int(minutes) * 60)
    end = (datetime.now() + timedelta(seconds=secs)).strftime("%H:%M")
    _schedule(secs, minutes)
    return f"Timer set for {minutes} minutes — I'll ping you at {end}."


# ---------------------------------------------------------------------------
# scheduling — picks the running asyncio loop when available (the normal path
# inside Gemini's tool call); falls back to a daemon thread for tests / any
# sync caller. Either way the same `_fire()` runs at the deadline.

def _schedule(seconds: int, minutes: int) -> None:
    def _fire() -> None:
        message = f"Your {minutes}-minute timer is done."
        notify("Reef · timer", message)
        trace.info(f"timer fired: {message}")

    try:
        loop = asyncio.get_running_loop()
        loop.call_later(seconds, _fire)
    except RuntimeError:
        # No running loop — schedule on a daemon thread instead so callers
        # outside the asyncio context (tests, scripts) still get the alert.
        threading.Timer(seconds, _fire).start()
