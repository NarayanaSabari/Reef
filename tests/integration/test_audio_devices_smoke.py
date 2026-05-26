import asyncio
import struct

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
    """Mic must yield 3 non-empty chunks AND contain real signal (not pure zeros).

    The signal check catches the silent-mic class of bug: when the host process lacks
    macOS microphone permission, the OS silently returns zero-filled buffers without
    raising any error. Even an ambient room produces a peak well above 50 on a real
    mic, so a peak of 0 is a sentinel for "permission denied / no real input".
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "x")  # Settings needs a key to construct
    src = MicAudioSource(Settings.from_env())
    chunks = []
    async def grab():
        async for c in src.stream():
            chunks.append(c)
            if len(chunks) >= 10:   # ~200 ms of audio - plenty to detect ambient noise
                return
    await asyncio.wait_for(grab(), timeout=5)
    assert len(chunks) == 10 and all(isinstance(c, bytes) and c for c in chunks)
    pcm = b"".join(chunks)
    samples = struct.unpack(f"<{len(pcm)//2}h", pcm)
    peak = max(abs(s) for s in samples)
    assert peak > 50, (
        f"microphone returned silence (peak={peak}); likely the parent process lacks "
        "macOS Microphone permission - grant it in System Settings → Privacy & Security → Microphone."
    )

@skip_no_audio
async def test_speaker_plays_silence_without_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    sink = SpeakerAudioSink(Settings.from_env())
    await sink.play(b"\x00\x00" * 480)  # 20 ms of silence @24k
    await sink.flush()
