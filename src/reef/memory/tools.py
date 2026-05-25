from collections.abc import Callable

from reef.memory.store import MemoryStore


def make_memory_tools(store: MemoryStore) -> list[Callable]:
    """Build ADK function tools bound to a MemoryStore. The store is captured in
    the closure so it never appears in the tool signatures the model sees."""

    async def reef_write_memory(key: str, value: str) -> str:
        """Remember a durable preference or fact about the user (persists across sessions).
        Use for things like 'I prefer brief mornings'. key: a short label; value: the detail."""
        # Phase 2: all tool-written memories use a single kind ("preference").
        await store.write("preference", key, value)
        return f"Remembered: {key} = {value}"

    async def reef_read_memory() -> str:
        """Return everything Reef currently remembers about the user."""
        mems = await store.all()
        if not mems:
            return "Nothing remembered yet."
        return "; ".join(f"{m.key}: {m.value}" for m in mems)

    async def reef_log_note(text: str) -> str:
        """Append a timestamped note to the user's personal log (e.g. 'logged day 68 of the streak')."""
        await store.append_log(text)
        return "Logged."

    return [reef_write_memory, reef_read_memory, reef_log_note]
