"""SQLite storage adapter with WAL mode and FTS5 (MNO-817/818)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .utils.logger import get_logger

logger = get_logger("sqlite_adapter")

from .config import mnemo_path
from .storage import Collections, LIST_COLLECTIONS

DB_FILE = "mnemo.db"


class SQLiteAdapter:
    """SQLite-backed storage with WAL mode and FTS5 full-text search."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.base_path = mnemo_path(repo_root)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_path / DB_FILE
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()
        self._auto_migrate()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_schema(self) -> None:
        c = self.conn
        c.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                collection TEXT NOT NULL,
                key TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at REAL DEFAULT 0,
                PRIMARY KEY (collection, key)
            )
        """)
        # FTS5 for full-text search
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS collections_fts USING fts5(
                collection, key, content, tokenize='porter'
            )
        """)
        c.commit()

    def _auto_migrate(self) -> None:
        """Import existing JSON files into SQLite on first run (MNO-818)."""
        # Only migrate if DB is empty
        row = self.conn.execute("SELECT COUNT(*) FROM collections").fetchone()
        if row[0] > 0:
            return

        from .storage import JSONFileAdapter
        json_adapter = JSONFileAdapter(self.repo_root)

        migrated = 0
        for collection in (Collections.MEMORY, Collections.DECISIONS, Collections.CONTEXT,
                           Collections.ERRORS, Collections.INCIDENTS, Collections.REVIEWS,
                           Collections.TASKS, Collections.HASHES):
            data = json_adapter.read_collection(collection)
            if data:
                self._write_raw(collection, data)
                migrated += 1

        if migrated > 0:
            logger.info(f"Migrated {migrated} collections from JSON to SQLite")

    def _write_raw(self, collection: str, data: Any) -> None:
        if isinstance(data, list):
            for item in data:
                key = self._item_key(item) if isinstance(item, dict) else str(hash(str(item)))
                self._upsert(collection, key, item)
        elif isinstance(data, dict):
            for key, value in data.items():
                self._upsert(collection, key, value)
        self.conn.commit()

    def _upsert(self, collection: str, key: str, value: Any) -> None:
        data_str = json.dumps(value, default=str)
        content = json.dumps(value, default=str) if isinstance(value, dict) else str(value)
        self.conn.execute(
            "INSERT OR REPLACE INTO collections (collection, key, data, updated_at) VALUES (?, ?, ?, ?)",
            (collection, key, data_str, time.time()),
        )
        # Update FTS
        self.conn.execute("DELETE FROM collections_fts WHERE collection=? AND key=?", (collection, key))
        self.conn.execute(
            "INSERT INTO collections_fts (collection, key, content) VALUES (?, ?, ?)",
            (collection, key, content[:1000]),
        )

    def get(self, collection: str, key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM collections WHERE collection=? AND key=?",
            (collection, key),
        ).fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def put(self, collection: str, key: str, value: dict[str, Any]) -> None:
        self._upsert(collection, key, value)
        self.conn.commit()

    def list(self, collection: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM collections WHERE collection=? ORDER BY updated_at",
            (collection,),
        ).fetchall()
        results = []
        for row in rows:
            try:
                item = json.loads(row[0])
                if isinstance(item, dict):
                    results.append(item)
            except json.JSONDecodeError:
                pass
        return results

    def query(self, collection: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        if not filters:
            return self.list(collection)
        return [
            item for item in self.list(collection)
            if all(item.get(k) == v for k, v in filters.items())
        ]

    def delete(self, collection: str, key: str) -> None:
        self.conn.execute("DELETE FROM collections WHERE collection=? AND key=?", (collection, key))
        self.conn.execute("DELETE FROM collections_fts WHERE collection=? AND key=?", (collection, key))
        self.conn.commit()

    def search(self, collection: str, query: str, k: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return self.list(collection)[:k]
        # Use FTS5
        try:
            rows = self.conn.execute(
                "SELECT c.data FROM collections_fts f JOIN collections c ON f.collection=c.collection AND f.key=c.key "
                "WHERE f.collection=? AND f.content MATCH ? LIMIT ?",
                (collection, query, k),
            ).fetchall()
            results = []
            for row in rows:
                try:
                    results.append(json.loads(row[0]))
                except json.JSONDecodeError:
                    pass
            return results
        except sqlite3.OperationalError:
            # Fallback to LIKE
            rows = self.conn.execute(
                "SELECT data FROM collections WHERE collection=? AND data LIKE ? LIMIT ?",
                (collection, f"%{query}%", k),
            ).fetchall()
            return [json.loads(r[0]) for r in rows if r[0]]

    def read_collection(self, collection: str) -> list[dict[str, Any]] | dict[str, Any]:
        if collection in LIST_COLLECTIONS:
            return self.list(collection)
        # Dict collections
        rows = self.conn.execute(
            "SELECT key, data FROM collections WHERE collection=?", (collection,)
        ).fetchall()
        result = {}
        for row in rows:
            try:
                result[row[0]] = json.loads(row[1])
            except json.JSONDecodeError:
                result[row[0]] = row[1]
        return result

    def write_collection(self, collection: str, data: list[dict[str, Any]] | dict[str, Any]) -> None:
        # Clear existing
        self.conn.execute("DELETE FROM collections WHERE collection=?", (collection,))
        self.conn.execute("DELETE FROM collections_fts WHERE collection=?", (collection,))
        self._write_raw(collection, data)

    @staticmethod
    def _item_key(item: dict[str, Any]) -> str:
        for field in ("id", "task_id", "key"):
            if field in item:
                return str(item[field])
        return str(hash(json.dumps(item, sort_keys=True, default=str)))

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
