import os, wave, asyncio, pathlib
import pytest
from reef.config import Settings
from reef.voice.ports import AudioOut
from reef.voice.gemini_session import GeminiLiveSession

pytestmark = pytest.mark.integration

FIXTURE = pathlib.Path(__file__).parent.parent / "fixtures" / "hello_16k.wav"

def _read_pcm(path: pathlib.Path) -> bytes:
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        return w.readframes(w.getnframes())

@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="needs GOOGLE_API_KEY")
@pytest.mark.skipif(not FIXTURE.exists(), reason="needs tests/fixtures/hello_16k.wav")
async def test_gemini_session_returns_audio():
    sess = GeminiLiveSession(Settings.from_env())
    await sess.start()
    pcm = _read_pcm(FIXTURE)
    for i in range(0, len(pcm), 640):
        await sess.send_audio(pcm[i:i + 640])
    got_audio = False
    async def consume():
        nonlocal got_audio
        async for ev in sess.receive():
            if isinstance(ev, AudioOut) and ev.data:
                got_audio = True
                return
    await asyncio.wait_for(consume(), timeout=25)
    await sess.close()
    assert got_audio
