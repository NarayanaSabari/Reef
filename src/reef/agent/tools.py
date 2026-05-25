from datetime import datetime

def get_current_time() -> str:
    """Return the current local date and time (e.g. for 'what time is it?')."""
    return datetime.now().strftime("%A %d %B %Y, %H:%M")
