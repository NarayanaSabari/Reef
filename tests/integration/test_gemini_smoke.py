import asyncio
import os
import pathlib
import wave

import pytest
from google.adk.sessions import DatabaseSessionService

from reef.config import Settings
from reef.memory.store import MemoryStore
from reef.voice.gemini_session import GeminiLiveSession
from reef.voice.ports import AudioOut

pytestmark = pytest.mark.integration

FIXTURE = pathlib.Path(__file__).parent.parent / "fixtures" / "hello_16k.wav"

def _read_pcm(path: pathlib.Path) -> bytes:
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        return w.readframes(w.getnframes())

@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="needs GOOGLE_API_KEY")
@pytest.mark.skipif(not FIXTURE.exists(), reason="needs tests/fixtures/hello_16k.wav")
async def test_gemini_session_returns_audio(tmp_path):
    store = MemoryStore(str(tmp_path / "reef.db"))
    await store.init()
    session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{tmp_path / 'reef.db'}")
    sess = GeminiLiveSession(Settings.from_env(), store, session_service)
    await sess.start()
    pcm = _read_pcm(FIXTURE)
    for i in range(0, len(pcm), 640):
        await sess.send_audio(pcm[i:i + 640])
    # 1.5s of silence so the server VAD reliably marks end-of-speech.
    silence = b"\x00\x00" * 320   # 20 ms of int16 mono silence at 16 kHz
    for _ in range(75):
        await sess.send_audio(silence)
    got_audio = False
    async def consume():
        nonlocal got_audio
        async for ev in sess.receive():
            if isinstance(ev, AudioOut) and ev.data:
                got_audio = True
                return
    # 60s covers ADK setup (DB session + Coral MCP spawn + tool registration) +
    # Gemini Live first-response latency. Direct google-genai responds in ~6s; ADK adds setup overhead.
    await asyncio.wait_for(consume(), timeout=60)
    await sess.close()
    assert got_audio
