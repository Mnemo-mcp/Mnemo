"""LadybugDB connection and schema management."""

from __future__ import annotations

import shutil
from pathlib import Path

import real_ladybug as lbug

from .schema import SCHEMA_STATEMENTS


def get_db_path(repo_root: Path) -> Path:
    return repo_root / ".mnemo" / "graph.lbug"


def open_db(repo_root: Path) -> tuple[lbug.Database, lbug.Connection]:
    """Open or create the LadybugDB database for a repo."""
    db_path = get_db_path(repo_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = lbug.Database(str(db_path))
    conn = lbug.Connection(db)
    return db, conn


def init_schema(conn: lbug.Connection) -> None:
    """Create all node and relationship tables if they don't exist."""
    for stmt in SCHEMA_STATEMENTS:
        try:
            conn.execute(stmt)
        except RuntimeError:
            # Table already exists
            pass


def reset_db(repo_root: Path) -> None:
    """Delete and recreate the database."""
    db_path = get_db_path(repo_root)
    if db_path.exists():
        # LadybugDB stores as single file or directory
        if db_path.is_dir():
            shutil.rmtree(db_path)
        else:
            db_path.unlink()
    # Also remove WAL/lock files
    for suffix in (".wal", ".lock"):
        p = db_path.with_suffix(db_path.suffix + suffix)
        if p.exists():
            p.unlink()
