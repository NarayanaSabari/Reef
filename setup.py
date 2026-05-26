"""py2app bundling scaffolding for Reef.

CURRENT STATUS (2026-05-26): the build below FAILS with
    error: install_requires is no longer supported
because py2app 0.28 explicitly rejects projects that declare `install_requires`
(`py2app/build_app.py:657`), and modern setuptools translates pyproject.toml's
`[project] dependencies` into install_requires. Pinning setuptools doesn't help -
the check is inside py2app, not setuptools.

Two viable paths forward (deferred — the menubar app is already runnable via
`uv run reef-app` and that's the macOS-app shell we ship for now):
  1. Switch to briefcase (BeeWare): native pyproject.toml-aware Python app bundler.
       uv pip install briefcase
       briefcase new   # creates briefcase config in pyproject.toml
       briefcase build macOS && briefcase package macOS
  2. Wait for / contribute a py2app fix that ignores install_requires when present
     in pyproject.toml (issue is well-known upstream).

What this scaffolding gets right (so the path is short when one of the above lands):
  - The Info.plist (LSUIElement, NSMicrophoneUsageDescription, bundle identifier).
  - The packages/includes list py2app would need.
"""
from setuptools import setup

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Reef",
        "CFBundleDisplayName": "Reef",
        "CFBundleIdentifier": "com.narayanasabari.reef",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "LSUIElement": True,
        "NSMicrophoneUsageDescription":
            "Reef listens to your voice to act on your requests (memory, GitHub, calendar/email).",
        "NSHumanReadableCopyright": "Reef — local-first voice agent.",
        "NSHighResolutionCapable": True,
    },
    "packages": [
        "reef",
        "google", "google.adk", "google.genai",
        "mcp",
        "sounddevice", "rumps", "pynput",
        "websockets", "sqlalchemy", "aiosqlite", "greenlet",
        "pydantic", "anyio", "httpx",
    ],
    "includes": [
        "asyncio", "wave", "json", "subprocess",
        "uuid", "time", "contextlib",
        "_cffi_backend",
    ],
    "excludes": ["pytest", "py2app", "mypy", "ruff"],
}

setup(
    app=["src/reef/shell/app.py"],
    options={"py2app": OPTIONS},
)
