import asyncio
import contextlib
import json
import os
import subprocess
from pathlib import Path

from google.adk.sessions import DatabaseSessionService

from reef.agent.coral import ensure_coral_available
from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.config import Settings, default_db_path
from reef.memory.store import MemoryStore
from reef.observability import trace
from reef.onboarding.profile import save_profile
from reef.shell.notify import notify
from reef.voice.gemini_session import GeminiLiveSession
from reef.voice.loop import VoiceLoop

DB_PATH = default_db_path()


async def _seed_default_profile_if_missing(store: MemoryStore) -> None:
    """Bake the user's name + default GitHub repo into memory so the InstructionProvider
    auto-injects them into the prompt. Lets the agent answer 'any PRs waiting on my review?'
    without first asking for owner/repo. Override via voice ('remember my github repo is X')
    or REEF_NAME / REEF_GH_OWNER / REEF_GH_REPO env vars."""
    if any(m.kind == "profile" and m.key == "github_owner" for m in await store.all()):
        return
    await save_profile(
        store,
        name=os.environ.get("REEF_NAME", "Venkat"),
        aliases=[],
        github_owner=os.environ.get("REEF_GH_OWNER", "NarayanaSabari"),
        github_repo=os.environ.get("REEF_GH_REPO", "Reef"),
    )


def _coral_json(sql: str) -> list:
    try:
        proc = subprocess.run(
            ["coral", "sql", "--format", "json", sql],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return []
        return json.loads(proc.stdout) or []
    except Exception:
        return []


async def _compose_brief(store: MemoryStore) -> str:
    """Build a one-line morning brief from the user's profile + Coral counts (best-effort)."""
    profile = {m.key: m.value for m in await store.all() if m.kind == "profile"}
    name = profile.get("name", "there")
    owner = profile.get("github_owner")
    repo = profile.get("github_repo")
    parts = [f"Good morning, {name}."]
    if owner and repo:
        rows = _coral_json(
            f"SELECT COUNT(*) AS c FROM github.pulls "
            f"WHERE owner='{owner}' AND repo='{repo}' AND state='open'"
        )
        pr_count = (rows[0].get("c") if rows else 0) or 0
        parts.append(f"{pr_count} open PRs on {repo}.")
    meetings = _coral_json("SELECT COUNT(*) AS c FROM demo_calendar.events")
    if meetings:
        parts.append(f"{(meetings[0].get('c') or 0)} meetings scheduled.")
    return " ".join(parts)


def _maybe_install_ptt_hotkey() -> tuple[asyncio.Event | None, object | None]:
    """If REEF_PTT_KEY is set, install a global hotkey that toggles a mic-gate Event.
    Returns (gate, listener) or (None, None). Needs Accessibility permission granted
    to the terminal app the first time the key is pressed."""
    key = os.environ.get("REEF_PTT_KEY")
    if not key:
        return None, None
    try:
        from pynput import keyboard
    except Exception as e:
        trace.info(f"pynput unavailable, PTT disabled: {e}")
        return None, None
    gate = asyncio.Event()  # starts closed: mic muted until first key press
    loop = asyncio.get_running_loop()

    def _toggle() -> None:
        if gate.is_set():
            loop.call_soon_threadsafe(gate.clear)
            trace.info(f"PTT [{key}] -> mic OFF")
        else:
            loop.call_soon_threadsafe(gate.set)
            trace.info(f"PTT [{key}] -> mic ON")

    listener = keyboard.GlobalHotKeys({key: _toggle})
    listener.start()
    trace.info(f"push-to-talk enabled: press {key} to toggle mic (Accessibility required)")
    return gate, listener


async def _schedule_morning_brief(store: MemoryStore) -> None:
    """Background task: at REEF_BRIEF_AFTER_SECONDS seconds after launch, post a macOS
    notification with a composed brief. Skipped unless the env var is set (no-op default).
    For the demo: `REEF_BRIEF_AFTER_SECONDS=120 uv run python -m reef.app.main` -> a
    notification fires two minutes after startup."""
    delay_str = os.environ.get("REEF_BRIEF_AFTER_SECONDS")
    if not delay_str:
        return
    try:
        delay = int(delay_str)
    except ValueError:
        return
    trace.info(f"morning brief scheduled in {delay}s (REEF_BRIEF_AFTER_SECONDS)")
    await asyncio.sleep(delay)
    brief = await _compose_brief(store)
    notify("Reef morning brief", brief)
    trace.info(f"morning-brief notification posted: {brief}")


async def main() -> None:
    trace.enable()
    ensure_coral_available()
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    trace.info(f"starting reef (model={settings.model}, db={DB_PATH})")
    store = MemoryStore(DB_PATH)
    await store.init()
    await _seed_default_profile_if_missing(store)
    session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{DB_PATH}")
    # Optional push-to-talk: set REEF_PTT_KEY=<f1> (or any pynput combo) to gate the mic
    # behind a toggleable hotkey. Default = mic always on (half-duplex muting handles echo).
    # Needs Accessibility permission for the terminal app on first key event.
    mic_gate, _hotkey_listener = _maybe_install_ptt_hotkey()
    source = MicAudioSource(settings, gate=mic_gate)
    sink = SpeakerAudioSink(settings)
    session = GeminiLiveSession(settings, store, session_service)
    await session.start()
    trace.info(f"voice loop active — session={session._session_id} — speak to me (Ctrl+C to quit)")
    brief_task = asyncio.create_task(_schedule_morning_brief(store))
    try:
        await VoiceLoop(source, sink, session).run()
    finally:
        trace.info("shutting down…")
        brief_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await brief_task
        await session.close()
        await sink.close()

def cli() -> None:
    """Sync entry point for the `reef` console script (project.scripts in pyproject.toml).
    The async `main()` is kept as-is so the unit test that asserts iscoroutinefunction passes."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
