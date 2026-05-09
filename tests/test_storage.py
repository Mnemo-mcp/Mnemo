import json
from pathlib import Path

from mnemo.storage import Collections, JSONFileAdapter


def test_json_file_adapter_puts_and_gets_list_collection_item(tmp_path: Path):
    storage = JSONFileAdapter(tmp_path)

    storage.put(Collections.MEMORY, "1", {"id": 1, "content": "Use repository pattern"})

    assert storage.get(Collections.MEMORY, "1") == {
        "id": 1,
        "content": "Use repository pattern",
    }
    assert json.loads((tmp_path / ".mnemo" / "memory.json").read_text(encoding="utf-8")) == [
        {"id": 1, "content": "Use repository pattern"}
    ]


def test_json_file_adapter_replaces_existing_list_item(tmp_path: Path):
    storage = JSONFileAdapter(tmp_path)

    storage.put(Collections.TASKS, "ABC-1", {"task_id": "ABC-1", "status": "active"})
    storage.put(Collections.TASKS, "ABC-1", {"task_id": "ABC-1", "status": "completed"})

    assert storage.list(Collections.TASKS) == [{"task_id": "ABC-1", "status": "completed"}]


def test_json_file_adapter_supports_dict_collections(tmp_path: Path):
    storage = JSONFileAdapter(tmp_path)

    storage.put(Collections.CONTEXT, "repo_root", {"value": "/repo"})

    assert storage.get(Collections.CONTEXT, "repo_root") == {"value": "/repo"}
    assert storage.list(Collections.CONTEXT) == [{"key": "repo_root", "value": "/repo"}]


def test_json_file_adapter_can_preserve_native_collection_shape(tmp_path: Path):
    storage = JSONFileAdapter(tmp_path)

    storage.write_collection(Collections.CONTEXT, {"repo_root": "/repo", "initialized": True})

    assert storage.read_collection(Collections.CONTEXT) == {
        "repo_root": "/repo",
        "initialized": True,
    }


def test_json_file_adapter_queries_and_searches(tmp_path: Path):
    storage = JSONFileAdapter(tmp_path)
    storage.put(Collections.ERRORS, "1", {"id": 1, "error": "Timeout", "service": "payments"})
    storage.put(Collections.ERRORS, "2", {"id": 2, "error": "Null ref", "service": "orders"})

    assert storage.query(Collections.ERRORS, {"service": "payments"}) == [
        {"id": 1, "error": "Timeout", "service": "payments"}
    ]
    assert storage.search(Collections.ERRORS, "null orders") == [
        {"id": 2, "error": "Null ref", "service": "orders"}
    ]


def test_json_file_adapter_delete_is_idempotent(tmp_path: Path):
    storage = JSONFileAdapter(tmp_path)
    storage.put(Collections.MEMORY, "1", {"id": 1, "content": "temporary"})

    storage.delete(Collections.MEMORY, "1")
    storage.delete(Collections.MEMORY, "1")

    assert storage.list(Collections.MEMORY) == []
