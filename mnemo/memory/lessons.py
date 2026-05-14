"""Lessons system — stores learned patterns with confidence decay and dedup."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from ..config import mnemo_path

LESSONS_FILE = "lessons.json"


def _load(repo_root: Path) -> list[dict]:
    path = mnemo_path(repo_root) / LESSONS_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(repo_root: Path, lessons: list[dict]) -> None:
    path = mnemo_path(repo_root) / LESSONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lessons, indent=2), encoding="utf-8")


def add_lesson(repo_root: Path, content: str, source: str = "") -> dict:
    fingerprint = hashlib.sha256(content.strip().lower().encode()).hexdigest()
    lessons = _load(repo_root)
    for lesson in lessons:
        if lesson.get("fingerprint") == fingerprint and not lesson.get("deleted"):
            lesson["confidence"] = lesson["confidence"] + 0.1 * (1 - lesson["confidence"])
            lesson["last_reinforced"] = time.time()
            lesson["reinforcement_count"] = lesson.get("reinforcement_count", 0) + 1
            _save(repo_root, lessons)
            return lesson
    entry = {
        "id": max((e.get("id", 0) for e in lessons), default=0) + 1,
        "content": content,
        "source": source,
        "fingerprint": fingerprint,
        "confidence": 0.7,
        "created_at": time.time(),
        "last_reinforced": time.time(),
        "reinforcement_count": 0,
        "deleted": False,
    }
    lessons.append(entry)
    _save(repo_root, lessons)
    return entry


def get_lessons(repo_root: Path, min_confidence: float = 0.3) -> list[dict]:
    return [e for e in _load(repo_root) if not e.get("deleted") and e.get("confidence", 0) >= min_confidence]


def decay_lessons(repo_root: Path) -> str:
    lessons = _load(repo_root)
    now = time.time()
    decayed = 0
    deleted = 0
    for lesson in lessons:
        if lesson.get("deleted"):
            continue
        weeks = (now - lesson.get("last_reinforced", now)) / (7 * 86400)
        if weeks >= 1:
            lesson["confidence"] -= 0.05 * weeks
            decayed += 1
            if lesson["confidence"] <= 0.1:
                lesson["deleted"] = True
                deleted += 1
    _save(repo_root, lessons)
    return f"Decayed {decayed} lessons, soft-deleted {deleted}."
