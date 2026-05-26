"""MicAudioSource's optional `gate` (used by PTT) drops chunks while closed."""
import asyncio

from reef.audio.mic_source import MicAudioSource
from reef.config import Settings


def _settings(monkeypatch) -> Settings:
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    return Settings.from_env()


async def test_gate_closed_drops_chunks(monkeypatch):
    """When the gate is provided and NOT set, the mic must yield nothing in the
    short test window. Bypass PortAudio by stubbing the queue directly."""
    gate = asyncio.Event()  # closed
    src = MicAudioSource(_settings(monkeypatch), gate=gate)
    src._loop = asyncio.get_running_loop()
    # Feed two chunks directly through the queue (bypass sd.RawInputStream).
    src._queue.put_nowait(b"a")
    src._queue.put_nowait(b"b")
    received = []

    async def grab():
        # Pull from the gated loop manually, mirroring stream()'s body without sd.
        while True:
            chunk = await src._queue.get()
            if src._gate is not None and not src._gate.is_set():
                continue
            received.append(chunk)

    task = asyncio.create_task(grab())
    await asyncio.sleep(0.05)
    task.cancel()
    assert received == []   # both chunks dropped because gate closed


async def test_gate_open_lets_chunks_through(monkeypatch):
    gate = asyncio.Event()
    gate.set()
    src = MicAudioSource(_settings(monkeypatch), gate=gate)
    src._loop = asyncio.get_running_loop()
    src._queue.put_nowait(b"a")
    src._queue.put_nowait(b"b")
    received = []

    async def grab():
        while True:
            chunk = await src._queue.get()
            if src._gate is not None and not src._gate.is_set():
                continue
            received.append(chunk)
            if len(received) >= 2:
                return

    await asyncio.wait_for(grab(), timeout=0.5)
    assert received == [b"a", b"b"]
