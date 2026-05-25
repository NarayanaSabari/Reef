import pytest

from reef.memory.store import Memory, MemoryStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "reef.db")

async def test_write_then_read_back(db_path):
    store = MemoryStore(db_path)
    await store.init()
    await store.write("preference", "mornings", "brief")
    assert await store.all() == [Memory(kind="preference", key="mornings", value="brief")]

async def test_write_upserts_same_key(db_path):
    store = MemoryStore(db_path)
    await store.init()
    await store.write("preference", "mornings", "brief")
    await store.write("preference", "mornings", "very brief")
    mems = await store.all()
    assert len(mems) == 1 and mems[0].value == "very brief"

async def test_persists_across_restart(db_path):
    store1 = MemoryStore(db_path)
    await store1.init()
    await store1.write("preference", "mornings", "brief")
    store2 = MemoryStore(db_path)
    await store2.init()
    assert await store2.all() == [Memory(kind="preference", key="mornings", value="brief")]

async def test_append_and_read_logs_in_order(db_path):
    store = MemoryStore(db_path)
    await store.init()
    await store.append_log("shipped the billing fix")
    await store.append_log("day 68 of the streak")
    assert await store.recent_logs() == ["shipped the billing fix", "day 68 of the streak"]

async def test_recent_logs_limit(db_path):
    store = MemoryStore(db_path)
    await store.init()
    for i in range(5):
        await store.append_log(f"note {i}")
    assert await store.recent_logs(limit=2) == ["note 3", "note 4"]
