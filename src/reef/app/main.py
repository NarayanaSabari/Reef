import asyncio
from reef.config import Settings
from reef.audio.mic_source import MicAudioSource
from reef.audio.speaker_sink import SpeakerAudioSink
from reef.voice.gemini_session import GeminiLiveSession
from reef.voice.loop import VoiceLoop

async def main() -> None:
    settings = Settings.from_env()
    source = MicAudioSource(settings)
    sink = SpeakerAudioSink(settings)
    session = GeminiLiveSession(settings)
    await session.start()
    try:
        await VoiceLoop(source, sink, session).run()
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
