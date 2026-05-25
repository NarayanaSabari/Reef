import pytest
from reef.memory.store import MemoryStore
from reef.memory.tools import make_memory_tools

@pytest.fixture
async def store(tmp_path):
    s = MemoryStore(str(tmp_path / "reef.db"))
    await s.init()
    return s

def _by_name(tools):
    return {t.__name__: t for t in tools}

async def test_write_memory_tool_persists_and_confirms(store):
    tools = _by_name(make_memory_tools(store))
    msg = await tools["reef_write_memory"](key="mornings", value="brief")
    assert "brief" in msg
    assert [(m.key, m.value) for m in await store.all()] == [("mornings", "brief")]

async def test_read_memory_tool_lists_memories(store):
    await store.write("preference", "mornings", "brief")
    tools = _by_name(make_memory_tools(store))
    out = await tools["reef_read_memory"]()
    assert "mornings" in out and "brief" in out

async def test_read_memory_tool_when_empty(store):
    tools = _by_name(make_memory_tools(store))
    assert "nothing" in (await tools["reef_read_memory"]()).lower()

async def test_log_note_tool_appends(store):
    tools = _by_name(make_memory_tools(store))
    await tools["reef_log_note"](text="shipped the billing fix")
    assert await store.recent_logs() == ["shipped the billing fix"]
