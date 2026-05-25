import asyncio
from pathlib import Path

from google.adk.sessions import DatabaseSessionService

from reef.agent.coral import ensure_coral_available
from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.config import Settings, default_db_path
from reef.memory.store import MemoryStore
from reef.voice.gemini_session import GeminiLiveSession
from reef.voice.loop import VoiceLoop

DB_PATH = default_db_path()

async def main() -> None:
    ensure_coral_available()
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    store = MemoryStore(DB_PATH)
    await store.init()
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
