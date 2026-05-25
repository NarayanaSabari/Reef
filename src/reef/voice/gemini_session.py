from typing import AsyncIterator
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.genai import types
from reef.config import Settings
from reef.memory.store import MemoryStore
from reef.memory.tools import make_memory_tools
from reef.agent.tools import get_current_time, set_timer
from reef.agent.coral import build_coral_toolset
from reef.voice.instructions import make_instruction_provider
from reef.voice.ports import VoiceEvent, AudioOut, Interrupted, TurnComplete


class GeminiLiveSession:
    """Adapter over ADK run_live + Gemini Live. Implements the VoiceSession port."""

    def __init__(self, settings: Settings, store: MemoryStore, session_service):
        self._settings = settings
        self._coral = build_coral_toolset()
        tools = [*make_memory_tools(store), get_current_time, set_timer, self._coral]
        self._agent = LlmAgent(
            model=settings.model, name="reef",
            instruction=make_instruction_provider(store),
            tools=tools,
        )
        self._sessions = session_service
        self._runner = Runner(app_name="reef", agent=self._agent, session_service=self._sessions)
        self._queue = LiveRequestQueue()
        self._user_id, self._session_id = "local", "voice"

    async def start(self) -> None:
        existing = await self._sessions.get_session(
            app_name="reef", user_id=self._user_id, session_id=self._session_id
        )
        if existing is None:
            await self._sessions.create_session(
                app_name="reef", user_id=self._user_id, session_id=self._session_id
            )

    async def send_audio(self, pcm: bytes) -> None:
        self._queue.send_realtime(
            types.Blob(data=pcm, mime_type=f"audio/pcm;rate={self._settings.input_sample_rate}")
        )

    async def receive(self) -> AsyncIterator[VoiceEvent]:
        run_config = RunConfig(streaming_mode=StreamingMode.BIDI, response_modalities=["AUDIO"])
        async for event in self._runner.run_live(
            user_id=self._user_id,
            session_id=self._session_id,
            live_request_queue=self._queue,
            run_config=run_config,
        ):
            if getattr(event, "interrupted", False):
                yield Interrupted()
                continue
            content = getattr(event, "content", None)
            for part in (getattr(content, "parts", None) or []):
                data = getattr(getattr(part, "inline_data", None), "data", None)
                if data:
                    yield AudioOut(data)
            if getattr(event, "turn_complete", False):
                yield TurnComplete()

    async def close(self) -> None:
        self._queue.close()
        await self._coral.close()
