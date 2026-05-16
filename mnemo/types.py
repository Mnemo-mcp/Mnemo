"""Mnemo domain types — TypedDict definitions for Memory, Decision, Plan entries."""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from typing import TypedDict, NotRequired
else:
    from typing import TypedDict
    from typing_extensions import NotRequired


class MemoryEntry(TypedDict):
    id: int
    content: str
    category: str
    timestamp: float
    branch: NotRequired[str]
    access_count: NotRequired[int]
    evicted: NotRequired[bool]
    tier: NotRequired[str]
    _summary: NotRequired[str]


class DecisionEntry(TypedDict):
    id: int
    decision: str
    reasoning: str
    timestamp: float
    active: NotRequired[bool]
    superseded_by: NotRequired[int]


class PlanTask(TypedDict):
    task_id: str
    description: str
    status: str
    files: NotRequired[list[str]]
    notes: NotRequired[str]


class CorrectionEntry(TypedDict):
    id: int
    bad_pattern: str
    correction: str
    timestamp: float
    decay: NotRequired[float]


class ProjectInfo(TypedDict):
    name: str
    language: str
    path: str
    manifest: str
