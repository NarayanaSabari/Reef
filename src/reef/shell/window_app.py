"""Pywebview window app for Reef — the macOS-app shell.

Native WebView window styled to match the Reef wireframes (calm grayscale on warm
cream, Geist + Instrument Serif). Three surfaces in one window:

  • Onboarding wizard  — 4 steps (Welcome → Connect Google → Profile → Done)
  • Chat (timeline)    — V4 Timeline: time / who / content + source badges,
                         driven by trace events pushed from Python
  • Settings sheet     — V1 Sidebar overlay (Google · Profile · Memory · Defaults
                         · Privacy · About), opens over any route

The HTML/CSS/JS lives in `ui/window.html` (kept editable as its own file). This
module is the Python orchestrator: it loads the HTML, exposes a `js_api` bridge
that JS calls via `window.pywebview.api.*`, and runs the asyncio voice loop in a
daemon thread (pywebview owns the main thread).

Run:
    uv run reef-app                  # window app (the default `reef-app` script)
    uv run reef-menubar              # legacy menubar-only mode
    uv run reef                      # terminal mode

Architecture:
- pywebview owns the main thread (WKWebView event loop).
- A daemon thread runs `asyncio.run(_async_main(api))` which holds the voice loop.
- JS bridge calls cross into asyncio via `asyncio.run_coroutine_threadsafe`.
- The trace module is wired to push every line into the WebView DOM via
  `window.evaluate_js`, so transcripts / tool calls / Coral SQL stream into the
  Timeline as they happen.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import Any

import webview
from google.adk.sessions import DatabaseSessionService

from reef.agent.coral import ensure_coral_available
from reef.app.main import _compose_brief, _seed_default_profile_if_missing
from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.config import Settings, default_db_path
from reef.memory.store import MemoryStore
from reef.observability import trace
from reef.onboarding.profile import save_profile
from reef.shell.notify import notify
from reef.voice.gemini_session import GeminiLiveSession
from reef.voice.loop import VoiceLoop

# ---------------------------------------------------------------------------

UI_PATH = Path(__file__).parent / "ui" / "window.html"


def _is_onboarded_sync(db_path: str) -> bool:
    """Synchronous check used by `init_route()` before the async loop is up.
    True iff the memory store already has the 'onboarded' flag written."""
    if not Path(db_path).exists():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute(
                "SELECT value FROM memory WHERE kind='profile' AND key='onboarded'"
            )
            row = cur.fetchone()
            return bool(row and row[0] == "true")
    except sqlite3.Error:
        return False


def _coral_version() -> str:
    """Best-effort `coral --version` for the About pane. Never raises."""
    try:
        proc = subprocess.run(
            ["coral", "--version"], capture_output=True, text=True, timeout=2
        )
        return (proc.stdout or proc.stderr).strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "not installed"


class Api:
    """Bridge between the WebView (JS) and the asyncio voice loop.

    JS calls `window.pywebview.api.<method>(args)`. Each return value is a
    Promise on the JS side; we either return synchronously or hop into the
    asyncio loop via `_call_async()`.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._mic_gate: asyncio.Event | None = None
        self._quit_event: asyncio.Event | None = None
        self._store: MemoryStore | None = None
        self._settings: Settings | None = None
        self._window: webview.Window | None = None
        self._listening = False
        self._db_path = default_db_path()

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    # --- helpers --------------------------------------------------------

    def _call_async(self, coro, *, default: Any = None, timeout: float = 5.0) -> Any:
        """Run a coroutine on the voice-loop thread, block until done."""
        if self._loop is None:
            return default
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return fut.result(timeout=timeout)
        except Exception as e:  # noqa: BLE001
            trace.info(f"_call_async error: {type(e).__name__}: {e}")
            return default

    # --- routing --------------------------------------------------------

    def init_route(self) -> dict:
        """First JS call after the page is ready. Decides whether to land the
        user in onboarding or chat based on whether they've completed setup."""
        onboarded = _is_onboarded_sync(self._db_path)
        return {"route": "chat" if onboarded else "onboarding", "step": 1}

    # --- onboarding -----------------------------------------------------

    def save_profile(self, data: dict) -> dict:
        """Persist the profile values from the wizard step 3.
        Missing fields fall back to env defaults so the agent isn't left
        nameless if the user blanks the inputs."""
        async def _go() -> None:
            assert self._store is not None
            name = (data.get("name") or "").strip() or "Venkat"
            owner = (data.get("github_owner") or "").strip() or "NarayanaSabari"
            repo = (data.get("github_repo") or "").strip() or "Reef"
            await save_profile(
                self._store, name=name, aliases=[],
                github_owner=owner, github_repo=repo,
            )
            trace.info(f"profile saved · name={name} · gh={owner}/{repo}")
        self._call_async(_go())
        return {"ok": True}

    def stub_mark_connected(self) -> dict:
        """Wizard 'Connect Google' stub: marks google_connected=true in profile.
        Real OAuth flow lands in the next spec. This lets the UI shell be
        exercised end-to-end (and the Settings sheet show 'connected') before
        the real auth path arrives."""
        async def _go() -> None:
            assert self._store is not None
            await self._store.write("profile", "google_connected", "true")
            await self._store.write("profile", "google_email", "(stubbed)")
            trace.info("google connected · stubbed (real OAuth lands next)")
        self._call_async(_go())
        return {"ok": True}

    def complete_onboarding(self) -> dict:
        """Wizard step 4 'Open Reef' — flag the user as onboarded so future
        launches go straight to chat."""
        async def _go() -> None:
            assert self._store is not None
            await self._store.write("profile", "onboarded", "true")
            trace.info("onboarding complete")
        self._call_async(_go())
        return {"ok": True}

    # --- settings -------------------------------------------------------

    def get_settings_snapshot(self) -> dict:
        """One-shot read for the Settings sheet. Returns everything the sheet
        renders so we keep the JS dumb."""
        async def _go() -> dict:
            assert self._store is not None
            rows = await self._store.all()
            profile = {m.key: m.value for m in rows if m.kind == "profile"}
            memories = [m.value for m in rows if m.kind == "preference"]
            return {
                "google_connected": profile.get("google_connected") == "true",
                "google_email": profile.get("google_email") or None,
                "profile": {
                    "name": profile.get("name"),
                    "github_owner": profile.get("github_owner"),
                    "github_repo": profile.get("github_repo"),
                },
                "memories": memories,
                "model": (self._settings.model if self._settings else None),
                "ptt_key": __import__("os").environ.get("REEF_PTT_KEY"),
                "brief_after_seconds": __import__("os").environ.get(
                    "REEF_BRIEF_AFTER_SECONDS"
                ),
                "coral_version": _coral_version(),
            }
        return self._call_async(_go(), default={
            "google_connected": False, "profile": {}, "memories": [],
            "model": None, "coral_version": "unknown",
        })

    def disconnect_google(self) -> dict:
        """Wipe the (stubbed) google connection. The real implementation will
        also clear keychain entries and remove the gmail/gcal/gdrive/contacts
        Coral sources."""
        async def _go() -> None:
            assert self._store is not None
            await self._store.write("profile", "google_connected", "false")
            await self._store.write("profile", "google_email", "")
            trace.info("google disconnected (stubbed)")
        self._call_async(_go())
        return {"ok": True}

    # --- mic / brief (preserved from previous version) ------------------

    def toggle_mic(self) -> dict:
        if self._loop is None or self._mic_gate is None:
            return {"listening": False}
        if self._listening:
            self._loop.call_soon_threadsafe(self._mic_gate.clear)
            self._listening = False
            trace.info("mic gate -> OFF")
        else:
            self._loop.call_soon_threadsafe(self._mic_gate.set)
            self._listening = True
            trace.info("mic gate -> ON")
        return {"listening": self._listening}

    def brief_now(self) -> None:
        if self._loop is None or self._store is None:
            return
        store = self._store

        async def _fire() -> None:
            brief = await _compose_brief(store)
            notify("Reef morning brief", brief)
            trace.info(f"manual brief: {brief}")

        asyncio.run_coroutine_threadsafe(_fire(), self._loop)

    # --- internal: push trace events to the WebView ---------------------

    def push_event(self, kind: str, label: str, text: str) -> None:
        if self._window is None:
            return
        payload = json.dumps({"kind": kind, "label": label, "text": text})
        with contextlib.suppress(Exception):
            self._window.evaluate_js(f"window.appendEvent({payload});")


# ---------------------------------------------------------------------------


async def _async_main(api: Api) -> None:
    """Build the voice stack and run the loop; stays alive until quit_event is set."""
    trace.enable()
    ensure_coral_available()
    db = default_db_path()
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    store = MemoryStore(db)
    await store.init()
    # Seed defaults so a user who skips onboarding still has a working profile.
    # Onboarding (when completed) overwrites these.
    await _seed_default_profile_if_missing(store)
    session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{db}")

    api._loop = asyncio.get_running_loop()
    api._mic_gate = asyncio.Event()        # muted at startup
    api._quit_event = asyncio.Event()
    api._store = store
    api._settings = settings

    source = MicAudioSource(settings, gate=api._mic_gate)
    sink = SpeakerAudioSink(settings)
    session = GeminiLiveSession(settings, store, session_service)
    await session.start()
    trace.info(f"window app ready — model={settings.model}")

    loop_task = asyncio.create_task(VoiceLoop(source, sink, session).run())
    quit_task = asyncio.create_task(api._quit_event.wait())
    try:
        await asyncio.wait({loop_task, quit_task}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        trace.info("shutting down agent…")
        await session.close()
        if not loop_task.done():
            with contextlib.suppress(Exception):
                await loop_task
        await sink.close()


def _on_window_closed(api: Api) -> None:
    if api._loop is not None and api._quit_event is not None:
        api._loop.call_soon_threadsafe(api._quit_event.set)


def main() -> None:
    api = Api()
    html = UI_PATH.read_text(encoding="utf-8")
    window = webview.create_window(
        "Reef",
        html=html,
        js_api=api,
        width=820, height=640,
        min_size=(560, 420),
        background_color="#f0eee9",
        text_select=True,
    )
    api.attach_window(window)
    window.events.closed += lambda: _on_window_closed(api)

    # Stream every trace line into the WebView Timeline.
    trace.set_sink(lambda kind, label, text: api.push_event(kind, label, text))

    def _run_agent() -> None:
        try:
            asyncio.run(_async_main(api))
        except Exception as e:  # noqa: BLE001
            api.push_event("info", "error", f"{type(e).__name__}: {e}")

    threading.Thread(target=_run_agent, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
