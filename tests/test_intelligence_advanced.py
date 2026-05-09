from pathlib import Path

from mnemo.intelligence import classify_architecture, context_for_active_task
from mnemo.repo_map import save_summary
from mnemo.sprint import set_current_task


def test_classify_architecture_detects_signals(tmp_path: Path):
    (tmp_path / "src" / "domain").mkdir(parents=True)
    (tmp_path / "src" / "application").mkdir(parents=True)
    (tmp_path / "src" / "infrastructure").mkdir(parents=True)
    (tmp_path / "src" / "presentation").mkdir(parents=True)
    matches = classify_architecture(tmp_path)
    names = {item["name"] for item in matches}
    assert "Clean Architecture" in names


def test_context_for_active_task_uses_indexed_code(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "orders.py").write_text(
        "class OrderService:\n"
        "    def create_order(self, payload):\n"
        "        return payload\n",
        encoding="utf-8",
    )
    save_summary(tmp_path)
    set_current_task(tmp_path, "MNO-402", "Add task-aware retrieval", files=["src/orders.py"])
    output = context_for_active_task(tmp_path)
    assert "Context for Active Task" in output
    assert "src/orders.py" in output
