import subprocess


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(title: str, message: str) -> None:
    """Post a basic macOS notification via osascript (fire-and-forget).
    Tap-to-deep-link needs UNUserNotificationCenter in a bundled app - deferred."""
    script = f"display notification {_q(message)} with title {_q(title)}"
    subprocess.run(["osascript", "-e", script], check=False)
