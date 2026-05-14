"""Tests for mnemo/audit.py — audit trail."""
import json
import pytest
from mnemo.utils.audit import record_audit, get_audit_log


def test_record_audit_creates_file(tmp_path):
    record_audit(tmp_path, "create", "mem-1", "memory", "test detail")
    audit_file = tmp_path / ".mnemo" / "audit.json"
    assert audit_file.exists()


def test_get_audit_log_returns_entries(tmp_path):
    record_audit(tmp_path, "create", "mem-1", "memory", "detail1")
    record_audit(tmp_path, "delete", "mem-2", "memory", "detail2")
    entries = get_audit_log(tmp_path)
    assert len(entries) == 2


def test_cap_at_1000_entries(tmp_path):
    for i in range(1005):
        record_audit(tmp_path, "op", f"id-{i}", "memory")
    audit_file = tmp_path / ".mnemo" / "audit.json"
    entries = json.loads(audit_file.read_text())
    assert len(entries) == 1000
    # Should keep the last 1000 (i.e., id-5 through id-1004)
    assert entries[0]["target_id"] == "id-5"
    assert entries[-1]["target_id"] == "id-1004"


def test_entry_schema(tmp_path):
    record_audit(tmp_path, "update", "dec-1", "decision", "changed reasoning")
    entries = get_audit_log(tmp_path)
    entry = entries[0]
    assert "timestamp" in entry
    assert isinstance(entry["timestamp"], float)
    assert entry["operation"] == "update"
    assert entry["target_id"] == "dec-1"
    assert entry["target_type"] == "decision"
    assert entry["details"] == "changed reasoning"


def test_get_audit_log_empty(tmp_path):
    entries = get_audit_log(tmp_path)
    assert entries == []


def test_get_audit_log_limit(tmp_path):
    for i in range(10):
        record_audit(tmp_path, "op", f"id-{i}", "memory")
    entries = get_audit_log(tmp_path, limit=3)
    assert len(entries) == 3
    assert entries[-1]["target_id"] == "id-9"
