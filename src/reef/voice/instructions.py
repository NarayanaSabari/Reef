from reef.memory.store import MemoryStore

BASE_INSTRUCTION = (
    "You are Reef, a concise, friendly macOS voice assistant for a busy founder. "
    "Keep spoken replies short. Use your tools to remember durable preferences and to recall them. "
    "You can answer questions about the user's GitHub by writing a single read-only SQL query through "
    "your Coral tools (e.g. table github.pulls for pull requests, github.requested_reviewers for review requests)."
)

def make_instruction_provider(store: MemoryStore):
    """Return an async ADK InstructionProvider that injects remembered facts into the prompt.
    Signature matches Callable[[ReadonlyContext], Awaitable[str]]; the context is unused
    because memory is read from the store directly."""
    async def provide(context) -> str:
        mems = await store.all()
        if not mems:
            return BASE_INSTRUCTION
        lines = "\n".join(f"- {m.key}: {m.value}" for m in mems)
        return f"{BASE_INSTRUCTION}\n\nWhat you remember about the user:\n{lines}"
    return provide
