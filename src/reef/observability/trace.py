"""Real-time terminal trace for the running app.

Surfaces what the user said, what Reef said, which tool got called, and what Coral SQL
ran - so you can watch the conversation drive the system from the terminal.

Off by default (tests stay quiet). `main.py` calls `enable()` at startup. Output goes
to stdout with ANSI colors when stdout is a TTY; falls back to plain text otherwise.
"""
from __future__ import annotations

import sys

_enabled = False
_use_color = sys.stdout.isatty()

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
