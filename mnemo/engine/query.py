"""Safe parameterized Cypher query execution for LadybugDB (Kuzu)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import real_ladybug as lbug

from .db import open_db, get_db_path


def execute(conn: lbug.Connection, cypher: str, params: dict[str, Any] | None = None) -> list[list[Any]]:
    """Execute a Cypher query with parameters, return all rows as lists.

    Use $param_name in Cypher and pass params={"param_name": value}.
    """
    result = conn.execute(cypher, params or {})
    rows = []
    while result.has_next():
        rows.append(result.get_next())
    return rows


def execute_one(conn: lbug.Connection, cypher: str, params: dict[str, Any] | None = None) -> list[Any] | None:
    """Execute a query and return the first row, or None."""
    result = conn.execute(cypher, params or {})
    if result.has_next():
        return result.get_next()
    return None


def execute_scalar(conn: lbug.Connection, cypher: str, params: dict[str, Any] | None = None) -> Any:
    """Execute a query and return the first column of the first row."""
    row = execute_one(conn, cypher, params)
    return row[0] if row else None


def with_connection(repo_root: Path):
    """Context manager that opens a DB connection and closes it after use."""
    class _Ctx:
        def __enter__(self):
            if not get_db_path(repo_root).exists():
                raise FileNotFoundError(f"No graph database at {get_db_path(repo_root)}. Run `mnemo init` first.")
            self.db, self.conn = open_db(repo_root)
            return self.conn

        def __exit__(self, *_):
            pass  # Kuzu connections don't require explicit close

    return _Ctx()
