import json
from pathlib import Path

from mnemo.repo_map import _load_hashes, _save_hashes


def test_hash_index_uses_storage_adapter(tmp_path: Path):
    hashes = {"src/app.py": "abc123"}

    _save_hashes(tmp_path, hashes)

    assert _load_hashes(tmp_path) == hashes
    data = json.loads((tmp_path / ".mnemo" / "hashes.json").read_text(encoding="utf-8"))
    assert data == hashes
