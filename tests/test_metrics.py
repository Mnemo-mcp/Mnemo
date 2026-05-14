"""Tests for mnemo/metrics.py — tool call metrics."""
import pytest
from mnemo.utils import metrics


@pytest.fixture(autouse=True)
def clear_metrics():
    """Reset metrics state between tests."""
    metrics._metrics.clear()
    yield


def test_record_call_stores_entries():
    metrics.record_call("mnemo_recall", 0.05)
    result = metrics.get_metrics()
    assert "mnemo_recall" in result
    assert result["mnemo_recall"]["calls"] == 1


def test_get_metrics_correct_stats():
    metrics.record_call("tool_a", 0.1, success=True)
    metrics.record_call("tool_a", 0.2, success=True)
    metrics.record_call("tool_a", 0.3, success=False)
    result = metrics.get_metrics()
    assert result["tool_a"]["calls"] == 3
    assert result["tool_a"]["avg_ms"] == pytest.approx(200.0, abs=0.1)
    assert result["tool_a"]["success_rate"] == pytest.approx(66.7, abs=0.1)


def test_max_entries_per_tool():
    for i in range(60):
        metrics.record_call("tool_b", 0.01)
    result = metrics.get_metrics()
    assert result["tool_b"]["calls"] == 50


def test_multiple_tools_tracked_independently():
    metrics.record_call("tool_x", 0.1, success=True)
    metrics.record_call("tool_y", 0.2, success=False)
    result = metrics.get_metrics()
    assert result["tool_x"]["calls"] == 1
    assert result["tool_x"]["success_rate"] == 100.0
    assert result["tool_y"]["calls"] == 1
    assert result["tool_y"]["success_rate"] == 0.0
