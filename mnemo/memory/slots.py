"""Structured memory slots for bounded context regions."""

from __future__ import annotations
import json
import re
from pathlib import Path
from ..config import mnemo_path

CORE_BUDGET = 2000
ARCHIVAL_BUDGET = 4000

# Priority order (higher index = lower priority for paging)
SLOT_PRIORITY = ['project_context', 'conventions', 'user_preferences', 'pending_items', 'known_gotchas']

DEFAULT_SLOTS = {
    'project_context': {'content': '', 'size_limit': 2000, 'pinned': True},
    'user_preferences': {'content': '', 'size_limit': 2000, 'pinned': True},
    'conventions': {'content': '', 'size_limit': 2000, 'pinned': True},
    'pending_items': {'content': '', 'size_limit': 3000, 'pinned': False},
    'known_gotchas': {'content': '', 'size_limit': 2000, 'pinned': False},
}

_recall_counter = 0

_FILE_PATH_RE = re.compile(r'(?:[\w./\\-]+/[\w./\\-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cs|rb|php|c|cpp|h|hpp|kt|swift|scala|json|yaml|yml|toml|md|sh))\b')
_TODO_RE = re.compile(r'\b(todo|need to|should)\b', re.I)


def get_slot(repo_root: Path, name: str) -> str:
    slots = _load_slots(repo_root)
    slot = slots.get(name, {})
    return slot.get('content', '')


def set_slot(repo_root: Path, name: str, content: str) -> str:
    slots = _load_slots(repo_root)
    if name not in slots:
        slots[name] = {'content': '', 'size_limit': 2000, 'pinned': False}
    limit = slots[name].get('size_limit', 2000)
    if len(content) > limit:
        overflow = content[limit:]
        content = content[:limit]
        # Move overflow to archival companion slot
        archival_name = f"{name}_archival"
        if archival_name not in slots:
            slots[archival_name] = {'content': '', 'size_limit': ARCHIVAL_BUDGET, 'pinned': False}
        existing_archival = slots[archival_name].get('content', '')
        new_archival = (existing_archival + '\n' + overflow).strip()[:ARCHIVAL_BUDGET]
        slots[archival_name]['content'] = new_archival
    slots[name]['content'] = content
    _save_slots(repo_root, slots)
    return f"Slot '{name}' updated ({len(content)} chars)"


def get_pinned_slots(repo_root: Path) -> str:
    slots = _load_slots(repo_root)
    lines = []
    for name, slot in slots.items():
        if slot.get('pinned') and slot.get('content'):
            lines.append(f"**{name}**: {slot['content']}")
    return '\n'.join(lines)


def get_working_context(repo_root: Path) -> str:
    """Return working context within CORE_BUDGET, paging overflow to archival."""

    slots = _load_slots(repo_root)
    result_parts = []
    total = 0
    for name in SLOT_PRIORITY:
        slot = slots.get(name, {})
        content = slot.get('content', '')
        if not content:
            continue
        if total + len(content) <= CORE_BUDGET:
            result_parts.append(f"**{name}**: {content}")
            total += len(content)
        else:
            # Fit what we can, page the rest
            remaining = CORE_BUDGET - total
            if remaining > 0:
                result_parts.append(f"**{name}**: {content[:remaining]}")
            break
    return '\n'.join(result_parts)


def reflect_slots(repo_root: Path) -> str:
    """Reflect on recent memories to update slots. Returns summary of changes."""
    from ..storage import Collections, get_storage
    storage = get_storage(repo_root)
    memories = storage.read_collection(Collections.MEMORY)
    if not isinstance(memories, list):
        return "No memories to reflect on."
    recent = memories[-10:]
    if not recent:
        return "No recent memories."

    changes = []
    # Extract TODOs
    todos = []
    for m in recent:
        content = m.get('content', '')
        if _TODO_RE.search(content):
            todos.append(content[:100])
    if todos:
        existing = get_slot(repo_root, 'pending_items')
        new_items = [t for t in todos if t not in existing]
        if new_items:
            updated = (existing + '\n' + '\n'.join(new_items)).strip()
            set_slot(repo_root, 'pending_items', updated)
            changes.append(f"pending_items +{len(new_items)}")

    # Extract file references → project_context
    files_found = set()
    for m in recent:
        files_found.update(_FILE_PATH_RE.findall(m.get('content', '')))
    if files_found:
        existing = get_slot(repo_root, 'project_context')
        new_files = [f for f in files_found if f not in existing]
        if new_files:
            updated = (existing + '\nFiles: ' + ', '.join(new_files)).strip()
            set_slot(repo_root, 'project_context', updated)
            changes.append(f"project_context +{len(new_files)} files")

    # Extract patterns → conventions
    patterns = [m.get('content', '')[:100] for m in recent if m.get('category') == 'pattern']
    if patterns:
        existing = get_slot(repo_root, 'conventions')
        new_patterns = [p for p in patterns if p not in existing]
        if new_patterns:
            updated = (existing + '\n' + '\n'.join(new_patterns)).strip()
            set_slot(repo_root, 'conventions', updated)
            changes.append(f"conventions +{len(new_patterns)}")

    return f"Reflected: {', '.join(changes)}" if changes else "No new slot updates."


def _load_slots(repo_root: Path) -> dict:
    path = mnemo_path(repo_root) / 'slots.json'
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {k: dict(v) for k, v in DEFAULT_SLOTS.items()}


def _save_slots(repo_root: Path, slots: dict):
    path = mnemo_path(repo_root) / 'slots.json'
    path.write_text(json.dumps(slots, indent=2))


def detect_frequent_topics(repo_root: Path) -> None:
    """Auto-create slots for search queries repeated 3+ times (MNO-027)."""
    from collections import Counter
    from ..utils.observations import _load_observations

    obs = _load_observations(repo_root)
    search_queries: list[str] = []
    for o in obs:
        if "search" in o.get("tool_name", ""):
            q = o.get("input_summary", "").strip()
            if q:
                search_queries.append(q)

    if not search_queries:
        return

    counts = Counter(search_queries)
    slots = _load_slots(repo_root)
    for query, count in counts.most_common(5):
        if count < 3:
            break
        # Derive slot name from query
        slot_name = re.sub(r'[^a-z0-9]+', '_', query[:30].lower()).strip('_')
        if not slot_name or slot_name in slots:
            continue
        slots[slot_name] = {'content': f'Auto-created for frequent query: {query[:100]}', 'size_limit': 2000, 'pinned': False}
    _save_slots(repo_root, slots)
