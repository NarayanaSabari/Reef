"""Pywebview-based window app for Reef - the macOS-app shell.

Opens a real window (native WKWebView under the hood) with a chat-style transcript,
a big mic-toggle button, and live streaming of every transcript / tool call / Coral
SQL via the trace subscriber. Runs the asyncio voice loop in a daemon thread.

Run:
    uv run reef-app                  # this window app (the default `reef-app` script)
    uv run reef-menubar              # the menubar-only variant
    uv run reef                      # terminal mode

Architecture:
- pywebview owns the main thread (WKWebView event loop).
- A daemon thread runs `asyncio.run(_async_main(api))` which holds the voice loop.
- Menu/button callbacks fire on the WebView thread; they cross into asyncio via
  `loop.call_soon_threadsafe(...)`.
- The trace module is wired to push every line into the WebView DOM via
  `window.evaluate_js`, so you see the conversation + tool calls + SQL stream in
  the app, exactly like the terminal trace.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from pathlib import Path

import webview
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

# --- the UI (HTML/CSS/JS in one place so deployment is just the .py file) ---

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Reef</title>
<style>
  :root{
    --bg:#0f1115; --bg-elev:#1a1d24; --line:#262b35;
    --text:#e8ebef; --muted:#8b95a7;
    --you:#5fb3e8; --reef:#c084fc; --tool:#fbbf24; --coral:#34d399; --info:#6b7280;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;background:var(--bg);color:var(--text);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;
    overflow:hidden}
  .app{display:grid;grid-template-rows:auto 1fr auto;height:100%}
  header{padding:14px 20px;background:var(--bg-elev);border-bottom:1px solid var(--line);
    display:flex;align-items:center;justify-content:space-between}
  h1{font-size:16px;font-weight:600;letter-spacing:-0.01em}
  h1 .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--coral);
    margin-right:8px;vertical-align:middle}
  .status{color:var(--muted);font-size:12px}
  main{overflow-y:auto;padding:18px 20px;scroll-behavior:smooth}
  .entry{margin-bottom:10px;display:flex;gap:10px;align-items:flex-start}
  .label{font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:0.06em;
    padding:3px 7px;border-radius:4px;flex-shrink:0;background:#23272f;color:var(--muted);
    min-width:48px;text-align:center;margin-top:2px}
  .entry .text{flex:1;word-break:break-word;white-space:pre-wrap}
  .entry[data-kind="you"] .label{color:var(--you);background:rgba(95,179,232,0.12)}
  .entry[data-kind="you"] .text{color:#bfdcef}
  .entry[data-kind="reef"] .label{color:var(--reef);background:rgba(192,132,252,0.12)}
  .entry[data-kind="reef"] .text{color:#e1ccff}
  .entry[data-kind="tool"] .label{color:var(--tool);background:rgba(251,191,36,0.10)}
  .entry[data-kind="tool"] .text{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:12px;color:#f3d989}
  .entry[data-kind="coral"] .label{color:var(--coral);background:rgba(52,211,153,0.10)}
  .entry[data-kind="coral"] .text{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:12px;color:#a7e9c8}
  .entry[data-kind="info"]{opacity:0.6}
  .entry[data-kind="info"] .label{color:var(--info)}
  .entry[data-kind="info"] .text{color:var(--muted);font-size:12px}
  footer{padding:14px 20px;background:var(--bg-elev);border-top:1px solid var(--line);
    display:flex;gap:10px;align-items:center;justify-content:center}
  button{background:#23272f;color:var(--text);border:1px solid var(--line);
    padding:10px 18px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;
    transition:all .12s ease;font-family:inherit}
  button:hover{background:#2d323b;border-color:#3a3f4a}
  button.primary{background:#3b82f6;border-color:#3b82f6;color:white}
  button.primary:hover{background:#2563eb;border-color:#2563eb}
  button.primary.listening{background:#dc2626;border-color:#dc2626}
  button.primary.listening:hover{background:#b91c1c}
  .pulse{display:inline-block;width:8px;height:8px;border-radius:50%;background:white;
    margin-right:8px;animation:pulse 1.2s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}
  .empty{color:var(--muted);text-align:center;padding:40px 20px;font-size:13px}
</style>
</head>
<body>
<div class="app">
  <header>
    <h1><span class="dot"></span>Reef</h1>
    <div class="status" id="status">Initializing…</div>
  </header>
  <main id="transcript">
    <div class="empty" id="empty">Click <strong>Talk to Reef</strong> below to start a conversation.</div>
  </main>
  <footer>
    <button id="mic" class="primary" onclick="onMicToggle()">🎤 Talk to Reef</button>
    <button onclick="window.pywebview.api.brief_now()">📅 Brief now</button>
  </footer>
</div>
<script>
  let listening = false;
  function setStatus(s){ document.getElementById('status').textContent = s; }
  function setListening(on){
    listening = on;
    const btn = document.getElementById('mic');
    if (on){
      btn.classList.add('listening');
      btn.innerHTML = '<span class="pulse"></span>Listening — click to stop';
      setStatus('🎙 listening');
    } else {
      btn.classList.remove('listening');
      btn.textContent = '🎤 Talk to Reef';
      setStatus('idle');
    }
  }
  async function onMicToggle(){
    const r = await window.pywebview.api.toggle_mic();
    setListening(!!r.listening);
  }
  window.appendEvent = function(ev){
    const empty = document.getElementById('empty');
    if (empty) empty.remove();
    const main = document.getElementById('transcript');
    const div = document.createElement('div');
    div.className = 'entry';
    div.setAttribute('data-kind', ev.kind);
    const lbl = document.createElement('span');
    lbl.className = 'label';
    lbl.textContent = ev.label;
    const txt = document.createElement('span');
    txt.className = 'text';
    txt.textContent = ev.text;
    div.appendChild(lbl);
    div.appendChild(txt);
    main.appendChild(div);
    main.scrollTop = main.scrollHeight;
  }
</script>
</body>
</html>"""


class Api:
    """Bridge between the WebView (JS) and the asyncio voice loop."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._mic_gate: asyncio.Event | None = None
        self._quit_event: asyncio.Event | None = None
        self._store: MemoryStore | None = None
        self._window: webview.Window | None = None
        self._listening = False

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    # --- called from JS via window.pywebview.api.* ---

    def toggle_mic(self) -> dict:
        if self._loop is None or self._mic_gate is None:
            return {"listening": False}
        if self._listening:
            self._loop.call_soon_threadsafe(self._mic_gate.clear)
            self._listening = False
            trace.info("mic gate -> OFF (window)")
        else:
            self._loop.call_soon_threadsafe(self._mic_gate.set)
            self._listening = True
            trace.info("mic gate -> ON (window)")
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

    # --- internal: push trace events to the WebView ---

    def push_event(self, kind: str, label: str, text: str) -> None:
        if self._window is None:
            return
        payload = json.dumps({"kind": kind, "label": label, "text": text})
        with contextlib.suppress(Exception):
            self._window.evaluate_js(f"window.appendEvent({payload});")


async def _async_main(api: Api) -> None:
    """Build the voice stack and run the loop; stays alive until quit_event is set."""
    trace.enable()
    ensure_coral_available()
    db = default_db_path()
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    store = MemoryStore(db)
    await store.init()
    await _seed_default_profile_if_missing(store)
    session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{db}")

    api._loop = asyncio.get_running_loop()
    api._mic_gate = asyncio.Event()        # muted at startup
    api._quit_event = asyncio.Event()
    api._store = store

    source = MicAudioSource(settings, gate=api._mic_gate)
    sink = SpeakerAudioSink(settings)
    session = GeminiLiveSession(settings, store, session_service)
    await session.start()
    trace.info(f"window app ready — model={settings.model}")
    api.push_event("info", "info", "Ready. Click 'Talk to Reef' to start.")

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
    """User closed the window — tell the agent thread to wind down."""
    if api._loop is not None and api._quit_event is not None:
        api._loop.call_soon_threadsafe(api._quit_event.set)


def main() -> None:
    api = Api()
    window = webview.create_window(
        "Reef",
        html=HTML,
        js_api=api,
        width=820, height=640,
        min_size=(560, 420),
        background_color="#0f1115",
        text_select=True,
    )
    api.attach_window(window)
    window.events.closed += lambda: _on_window_closed(api)

    # Stream trace lines into the WebView (mirrors stdout output).
    trace.set_sink(lambda kind, label, text: api.push_event(kind, label, text))

    # Run the asyncio voice loop in a daemon thread; webview owns the main thread.
    def _run_agent() -> None:
        try:
            asyncio.run(_async_main(api))
        except Exception as e:  # noqa: BLE001
            api.push_event("info", "error", f"{type(e).__name__}: {e}")

    threading.Thread(target=_run_agent, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
