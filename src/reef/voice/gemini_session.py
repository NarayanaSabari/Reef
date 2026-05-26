from collections.abc import AsyncIterator

from google.adk.agents import LlmAgent
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.genai import types

from reef.agent.coral_query import coral_query
from reef.agent.tools import get_current_time, set_timer
from reef.config import Settings
from reef.memory.store import MemoryStore
from reef.memory.tools import make_memory_tools
from reef.observability import trace
from reef.voice.instructions import make_instruction_provider
from reef.voice.ports import AudioOut, Interrupted, TurnComplete, VoiceEvent


class GeminiLiveSession:
    """Adapter over ADK run_live + Gemini Live. Implements the VoiceSession port."""

    def __init__(self, settings: Settings, store: MemoryStore, session_service: BaseSessionService):
        self._settings = settings
        # Voice agent uses a single Coral function tool (not the McpToolset's 5 tools) so the
        # preview Live models stay reliable across turns (see reef/agent/coral_query.py docstring).
        tools = [*make_memory_tools(store), get_current_time, set_timer, coral_query]
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
            # --- terminal trace: surface what's happening in real time ---
            # Only emit finalized transcripts (skip partials) to keep output clean.
            if not getattr(event, "partial", False):
                input_tr = getattr(event, "input_transcription", None)
                if input_tr is not None:
                    trace.you(getattr(input_tr, "text", "") or "")
                output_tr = getattr(event, "output_transcription", None)
                if output_tr is not None:
                    trace.reef(getattr(output_tr, "text", "") or "")

            if getattr(event, "interrupted", False):
                yield Interrupted()
                continue

            content = getattr(event, "content", None)
            for part in (getattr(content, "parts", None) or []):
                # Tool call/response trace + the standard audio passthrough.
                fc = getattr(part, "function_call", None)
                if fc is not None and getattr(fc, "name", None):
                    trace.tool_call(fc.name, dict(getattr(fc, "args", None) or {}))
                fr = getattr(part, "function_response", None)
                if fr is not None and getattr(fr, "name", None):
                    trace.tool_response(fr.name, getattr(fr, "response", None))
                data = getattr(getattr(part, "inline_data", None), "data", None)
                if data:
                    yield AudioOut(data)
            if getattr(event, "turn_complete", False):
                yield TurnComplete()

    async def close(self) -> None:
        self._queue.close()
