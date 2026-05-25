from datetime import datetime, timedelta


def get_current_time() -> str:
    """Return the current local date and time (e.g. for 'what time is it?')."""
    return datetime.now().strftime("%A %d %B %Y, %H:%M")

def set_timer(minutes: int) -> str:
    """Acknowledge a timer for N minutes (the alert is delivered by the notification system)."""
    end = (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")
    return f"Timer set for {minutes} minutes - I'll let you know at {end}."
