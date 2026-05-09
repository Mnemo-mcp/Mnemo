from pathlib import Path

from mnemo.mcp_server import handle_tool_call
from mnemo.repo_map import save_summary
from mnemo.sprint import set_current_task


def test_mnemo_context_for_task_tool(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mnemo").mkdir(exist_ok=True)
    src = tmp_path / "service.py"
    src.write_text("def calculate_risk(input):\n    return input\n", encoding="utf-8")
    save_summary(tmp_path)
    set_current_task(tmp_path, "RISK-1", "Implement risk calculations", files=["service.py"])

    result = handle_tool_call("mnemo_context_for_task", {"repo_path": str(tmp_path)})
    text = result["content"][0]["text"]
    assert "Active Task" in text
    assert "service.py" in text
