import asyncio

import pytest
import sounddevice as sd

from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.config import Settings

pytestmark = pytest.mark.integration

def _no_audio_devices() -> bool:
    try:
        devices = sd.query_devices()
        has_input = any(d["max_input_channels"] > 0 for d in devices)
        has_output = any(d["max_output_channels"] > 0 for d in devices)
        return not (has_input and has_output)
    except Exception:
        return True

skip_no_audio = pytest.mark.skipif(_no_audio_devices(), reason="no audio input/output device available")

@skip_no_audio
async def test_mic_yields_chunks(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "x")  # Settings needs a key to construct
    src = MicAudioSource(Settings.from_env())
    chunks = []
    async def grab():
        async for c in src.stream():
            chunks.append(c)
            if len(chunks) >= 3:
                return
    await asyncio.wait_for(grab(), timeout=5)
    assert len(chunks) == 3 and all(isinstance(c, bytes) and c for c in chunks)

@skip_no_audio
async def test_speaker_plays_silence_without_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    sink = SpeakerAudioSink(Settings.from_env())
    await sink.play(b"\x00\x00" * 480)  # 20 ms of silence @24k
    await sink.flush()
