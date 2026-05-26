"""Assembled rumps menubar app — the macOS-app shell for Reef.

Run: `uv run reef-app`  (or: `uv run python -m reef.shell.app`)

Architecture:
- rumps.App runs on the MAIN thread (NSRunLoop owns it).
- The asyncio voice loop runs in a DAEMON thread (asyncio.run inside it).
- Menu callbacks fire on the rumps/main thread; they cross into the asyncio
  world via `loop.call_soon_threadsafe(...)` (event.set/clear) or
  `asyncio.run_coroutine_threadsafe(...)` (one-shot coroutines).

Menu:
  - "Talk to Reef" toggles the mic gate (push-to-talk style; default starts MUTED so
    Reef doesn't hear stray ambient audio at launch).
  - "Morning brief now" triggers an immediate brief notification.
  - "Quit Reef" sets a quit event, lets the voice loop wind down, and exits.
"""
from __future__ import annotations

import asyncio
import contextlib
import threading
from pathlib import Path

import rumps
from google.adk.sessions import DatabaseSessionService

from reef.agent.coral import ensure_coral_available
from reef.app.main import _compose_brief, _seed_default_profile_if_missing
from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.config import Settings, default_db_path
from reef.memory.store import MemoryStore
from reef.observability import trace
from reef.shell.notify import notify
from reef.voice.gemini_session import GeminiLiveSession
from reef.voice.loop import VoiceLoop


class ReefApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Reef", quit_button=None)
        self._listen_item = rumps.MenuItem("Talk to Reef", callback=self._toggle_listen)
        self._brief_item = rumps.MenuItem("Morning brief now", callback=self._brief_now)
        quit_item = rumps.MenuItem("Quit Reef", callback=self._quit)
        self.menu = [self._listen_item, self._brief_item, None, quit_item]

        # Asyncio side — populated when the agent thread is up.
        self._loop: asyncio.AbstractEventLoop | None = None
        self._mic_gate: asyncio.Event | None = None
        self._quit_event: asyncio.Event | None = None
        self._store: MemoryStore | None = None
        self._listening = False

        threading.Thread(target=self._run_agent, daemon=True).start()

    # --- asyncio side (daemon thread) ---

    def _run_agent(self) -> None:
        try:
            asyncio.run(self._async_main())
        except Exception as e:  # noqa: BLE001
            notify("Reef", f"Voice loop crashed: {type(e).__name__}: {e}")

    async def _async_main(self) -> None:
        trace.enable()
        ensure_coral_available()
        db = default_db_path()
        Path(db).parent.mkdir(parents=True, exist_ok=True)
        settings = Settings.from_env()
        store = MemoryStore(db)
        await store.init()
        await _seed_default_profile_if_missing(store)
        session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{db}")

        self._loop = asyncio.get_running_loop()
        self._mic_gate = asyncio.Event()   # closed at launch -> mic muted until user toggles
        self._quit_event = asyncio.Event()
        self._store = store

        source = MicAudioSource(settings, gate=self._mic_gate)
        sink = SpeakerAudioSink(settings)
        session = GeminiLiveSession(settings, store, session_service)
        await session.start()
        trace.info(f"menubar app ready — session={session._session_id}")
        notify("Reef", "Ready. Click the menubar icon → 'Talk to Reef' to start.")

        loop_task = asyncio.create_task(VoiceLoop(source, sink, session).run())
        quit_task = asyncio.create_task(self._quit_event.wait())
        try:
            await asyncio.wait({loop_task, quit_task}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            trace.info("shutting down agent…")
            await session.close()   # ends pump_events → VoiceLoop exits
            if not loop_task.done():
                with contextlib.suppress(Exception):
                    await loop_task
            await sink.close()

    # --- menu callbacks (main / rumps thread) ---

    def _toggle_listen(self, _sender) -> None:
        if self._loop is None or self._mic_gate is None:
            return
        if self._listening:
            self._loop.call_soon_threadsafe(self._mic_gate.clear)
            self._listen_item.title = "Talk to Reef"
            self._listening = False
            trace.info("mic gate -> OFF (menubar)")
        else:
            self._loop.call_soon_threadsafe(self._mic_gate.set)
            self._listen_item.title = "● Listening — click to stop"
            self._listening = True
            trace.info("mic gate -> ON (menubar)")

    def _brief_now(self, _sender) -> None:
        if self._loop is None or self._store is None:
            return
        store = self._store

        async def _fire() -> None:
            brief = await _compose_brief(store)
            notify("Reef morning brief", brief)
            trace.info(f"manual brief posted: {brief}")

        asyncio.run_coroutine_threadsafe(_fire(), self._loop)

    def _quit(self, _sender) -> None:
        if self._loop is not None and self._quit_event is not None:
            self._loop.call_soon_threadsafe(self._quit_event.set)
        rumps.quit_application()


def main() -> None:
    ReefApp().run()


if __name__ == "__main__":
    main()
