import asyncio
import os
from pathlib import Path

from google.adk.sessions import DatabaseSessionService

from reef.agent.coral import ensure_coral_available
from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.config import Settings, default_db_path
from reef.memory.store import MemoryStore
from reef.onboarding.profile import save_profile
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


async def main() -> None:
    ensure_coral_available()
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    store = MemoryStore(DB_PATH)
    await store.init()
    await _seed_default_profile_if_missing(store)
    session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{DB_PATH}")
    source = MicAudioSource(settings)
    sink = SpeakerAudioSink(settings)
    session = GeminiLiveSession(settings, store, session_service)
    await session.start()
    try:
        await VoiceLoop(source, sink, session).run()
    finally:
        await session.close()
        await sink.close()

if __name__ == "__main__":
    asyncio.run(main())
