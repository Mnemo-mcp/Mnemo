"""Storage abstraction for Mnemo collections."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Protocol

from .config import CONTEXT_FILE, DECISIONS_FILE, MEMORY_FILE, mnemo_path


class Collections:
    """Logical storage collection names."""

    MEMORY = "memory"
    DECISIONS = "decisions"
    CONTEXT = "context"
    HASHES = "hashes"
    ERRORS = "errors"
    INCIDENTS = "incidents"
    REVIEWS = "reviews"
    TASKS = "tasks"
    REPO_MAP = "repo_map"
    KNOWLEDGE = "knowledge"


class StorageAdapter(Protocol):
    """Synchronous storage contract used by local Mnemo tools."""

    def get(self, collection: str, key: str) -> dict[str, Any] | None:
        """Return a single item by key."""

    def put(self, collection: str, key: str, value: dict[str, Any]) -> None:
        """Create or replace a single item."""

    def list(self, collection: str) -> list[dict[str, Any]]:
        """Return all items in a collection."""

    def query(self, collection: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Return items matching exact filter values."""

    def delete(self, collection: str, key: str) -> None:
        """Delete a single item by key."""

    def search(self, collection: str, query: str, k: int = 10) -> list[dict[str, Any]]:
        """Return keyword matches for a collection."""

    def read_collection(self, collection: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Read a collection in its native persisted shape."""

    def write_collection(self, collection: str, data: list[dict[str, Any]] | dict[str, Any]) -> None:
        """Write a collection in its native persisted shape."""


COLLECTION_FILES = {
    Collections.MEMORY: MEMORY_FILE,
    Collections.DECISIONS: DECISIONS_FILE,
    Collections.CONTEXT: CONTEXT_FILE,
    Collections.HASHES: "hashes.json",
    Collections.ERRORS: "errors.json",
    Collections.INCIDENTS: "incidents.json",
    Collections.REVIEWS: "reviews.json",
    Collections.TASKS: "tasks.json",
    Collections.REPO_MAP: "repo_map.json",
}

LIST_COLLECTIONS = {
    Collections.MEMORY,
    Collections.DECISIONS,
    Collections.ERRORS,
    Collections.INCIDENTS,
    Collections.REVIEWS,
    Collections.TASKS,
}


class JSONFileAdapter:
    """Local JSON-file storage backend preserving the current `.mnemo` layout."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.base_path = mnemo_path(repo_root)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def collection_path(self, collection: str) -> Path:
        filename = COLLECTION_FILES.get(collection, f"{collection}.json")
        return self.base_path / filename

    def get(self, collection: str, key: str) -> dict[str, Any] | None:
        data = self._load(collection)
        if isinstance(data, dict):
            value = data.get(key)
            if isinstance(value, dict):
                return value
            if value is not None:
                return {"key": key, "value": value}
            return None

        for item in data:
            if self._item_key(item) == key:
                return item
        return None

    def put(self, collection: str, key: str, value: dict[str, Any]) -> None:
        if collection in LIST_COLLECTIONS:
            items = self._load_list(collection)
            replacement = dict(value)
            if "id" not in replacement and key and "task_id" not in replacement:
                replacement["id"] = key

            for index, item in enumerate(items):
                if self._item_key(item) == key:
                    items[index] = replacement
                    self.replace_all(collection, items)
                    return

            items.append(replacement)
            self.replace_all(collection, items)
            return

        data = self._load_dict(collection)
        data[key] = value
        self._save(collection, data)

    def list(self, collection: str) -> list[dict[str, Any]]:
        data = self._load(collection)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return [
            {"key": key, **value} if isinstance(value, dict) else {"key": key, "value": value}
            for key, value in data.items()
        ]

    def query(self, collection: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        if not filters:
            return self.list(collection)
        return [
            item
            for item in self.list(collection)
            if all(item.get(field) == expected for field, expected in filters.items())
        ]

    def delete(self, collection: str, key: str) -> None:
        if collection in LIST_COLLECTIONS:
            items = [item for item in self._load_list(collection) if self._item_key(item) != key]
            self.replace_all(collection, items)
            return

        data = self._load_dict(collection)
        data.pop(key, None)
        self._save(collection, data)

    def search(self, collection: str, query: str, k: int = 10) -> list[dict[str, Any]]:
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return self.list(collection)[:k]

        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self.list(collection):
            text = json.dumps(item, sort_keys=True).lower()
            score = sum(1 for term in terms if term in text)
            if score:
                scored.append((score, item))

        scored.sort(key=lambda match: match[0], reverse=True)
        return [item for _, item in scored[:k]]

    def replace_all(self, collection: str, items: list[dict[str, Any]]) -> None:
        """Replace a list collection in one write."""
        self._save(collection, items)

    def read_collection(self, collection: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Read a collection in its native persisted shape."""
        return self._load(collection)

    def write_collection(self, collection: str, data: list[dict[str, Any]] | dict[str, Any]) -> None:
        """Write a collection in its native persisted shape."""
        self._save(collection, data)

    def _load(self, collection: str) -> list[dict[str, Any]] | dict[str, Any]:
        path = self.collection_path(collection)
        if not path.exists():
            return [] if collection in LIST_COLLECTIONS else {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return [] if collection in LIST_COLLECTIONS else {}
        if collection in LIST_COLLECTIONS:
            return data if isinstance(data, list) else []
        return data if isinstance(data, dict) else {}

    def _load_list(self, collection: str) -> list[dict[str, Any]]:
        data = self._load(collection)
        return data if isinstance(data, list) else []

    def _load_dict(self, collection: str) -> dict[str, Any]:
        data = self._load(collection)
        return data if isinstance(data, dict) else {}

    def _save(self, collection: str, data: Any) -> None:
        path = self.collection_path(collection)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, indent=2) + "\n"
        # Atomic write: write to temp file then rename
        try:
            fd = tempfile.NamedTemporaryFile(
                mode="w", dir=str(path.parent), suffix=".tmp",
                delete=False, encoding="utf-8",
            )
            fd.write(content)
            fd.flush()
            os.fsync(fd.fileno())
            fd.close()
            os.replace(fd.name, str(path))
        except OSError:
            # Fallback: direct write (Windows edge cases)
            try:
                os.unlink(fd.name)
            except OSError:
                pass
            path.write_text(content, encoding="utf-8")

    @staticmethod
    def _item_key(item: dict[str, Any]) -> str:
        for field in ("id", "task_id", "key"):
            if field in item:
                return str(item[field])
        return ""


def get_storage(repo_root: Path) -> StorageAdapter:
    """Return the default local storage adapter."""
    return JSONFileAdapter(repo_root)
