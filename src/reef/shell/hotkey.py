from pynput import keyboard


def start_hotkey(combo: str, callback):
    """Start a global hotkey listener (e.g. '<cmd>+<shift>+r'). Needs Accessibility permission.
    Returns the started listener. Not started in tests (needs a real input source)."""
    listener = keyboard.GlobalHotKeys({combo: callback})
    listener.start()
    return listener
