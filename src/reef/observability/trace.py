"""Real-time terminal trace for the running app.

Surfaces what the user said, what Reef said, which tool got called, and what Coral SQL
ran - so you can watch the conversation drive the system from the terminal.

Off by default (tests stay quiet). `main.py` calls `enable()` at startup. Output goes
to stdout with ANSI colors when stdout is a TTY; falls back to plain text otherwise.
"""
from __future__ import annotations

import sys
from typing import Callable, Optional

_enabled = False
_use_color = sys.stdout.isatty()
# Optional subscriber - the window app installs one to mirror trace lines into the UI.
# Signature: sink(kind, label, text) -> None. Exceptions are swallowed so the UI can't
# break the app.
_sink: Optional[Callable[[str, str, str], None]] = None


def set_sink(callback: Optional[Callable[[str, str, str], None]]) -> None:
    """Install (or remove) a callback that mirrors every emitted trace line.
    Used by the window app to stream events into the WebView."""
    global _sink
    _sink = callback

_RESET = "\033[0m"
_COLORS = {
    "you":   "\033[36m",   # cyan
    "reef":  "\033[35m",   # magenta
    "tool":  "\033[33m",   # yellow
    "coral": "\033[32m",   # green
    "info":  "\033[90m",   # dim grey
}


def enable() -> None:
    """Turn tracing on (main.py calls this once at startup)."""
    global _enabled
    _enabled = True


def is_enabled() -> bool:
    return _enabled


def _line(color_key: str, label: str, text: str) -> None:
    if not _enabled:
        return
    if _use_color:
        prefix = f"{_COLORS.get(color_key, '')}[{label}]{_RESET}"
    else:
        prefix = f"[{label}]"
    print(f"{prefix} {text}", flush=True)
    if _sink is not None:
        try:
            _sink(color_key, label, text)
        except Exception:
            pass   # never let a sink break the app


def you(text: str) -> None:
    """A finalized user-utterance transcription from Gemini."""
    if text and text.strip():
        _line("you", "you", text.strip())


def reef(text: str) -> None:
    """A finalized model-utterance transcription from Gemini."""
    if text and text.strip():
        _line("reef", "reef", text.strip())


def tool_call(name: str, args: dict | None) -> None:
    args = args or {}
    arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    _line("tool", "tool→", f"{name}({arg_str})")


def tool_response(name: str, response: object) -> None:
    text = str(response)
    if len(text) > 200:
        text = text[:200] + "…"
    _line("tool", "tool←", f"{name}: {text}")


def coral_sql(sql: str) -> None:
    _line("coral", "coral", sql.strip())


def coral_result(summary: str) -> None:
    _line("coral", "coral←", summary)


def info(text: str) -> None:
    _line("info", "info", text)
