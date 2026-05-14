"""Simple metrics tracking for tool calls."""

from __future__ import annotations
import time
from collections import defaultdict

_metrics: dict[str, list] = defaultdict(list)
_MAX_PER_TOOL = 50


def record_call(tool_name: str, duration: float, success: bool = True):
    entries = _metrics[tool_name]
    entries.append({'duration': duration, 'success': success, 'timestamp': time.time()})
    if len(entries) > _MAX_PER_TOOL:
        _metrics[tool_name] = entries[-_MAX_PER_TOOL:]


def get_metrics() -> dict:
    result = {}
    for tool, entries in _metrics.items():
        if entries:
            durations = [e['duration'] for e in entries]
            successes = sum(1 for e in entries if e['success'])
            result[tool] = {
                'calls': len(entries),
                'avg_ms': round(sum(durations) / len(durations) * 1000, 1),
                'success_rate': round(successes / len(entries) * 100, 1),
            }
    return result
