from dataclasses import dataclass

import aiosqlite


@dataclass(frozen=True)
class Memory:
    kind: str
    key: str
    value: str

class MemoryStore:
    """Durable key-value memory in a local SQLite file. Opens a connection per op (simple + test-friendly)."""
    def __init__(self, db_path: str):
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS memory ("
                " kind TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,"
                " created_at TEXT NOT NULL DEFAULT (datetime('now')),"
                " PRIMARY KEY (kind, key))"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS log ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL,"
                " created_at TEXT NOT NULL DEFAULT (datetime('now')))"
            )
            await db.commit()

    async def write(self, kind: str, key: str, value: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO memory(kind,key,value) VALUES(?,?,?) "
                "ON CONFLICT(kind,key) DO UPDATE SET value=excluded.value, created_at=datetime('now')",
                (kind, key, value),
            )
            await db.commit()

    async def all(self) -> list[Memory]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute("SELECT kind,key,value FROM memory ORDER BY created_at, key")
            return [Memory(kind=r[0], key=r[1], value=r[2]) for r in await cur.fetchall()]

    async def append_log(self, text: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("INSERT INTO log(text) VALUES(?)", (text,))
            await db.commit()

    async def recent_logs(self, limit: int = 20) -> list[str]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT text FROM (SELECT id, text FROM log ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (limit,),
            )
            return [r[0] for r in await cur.fetchall()]
