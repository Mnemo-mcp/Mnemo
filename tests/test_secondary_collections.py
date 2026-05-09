import json
from pathlib import Path

from mnemo.code_review import add_review, get_rejected_suggestions, get_reviews_for_file
from mnemo.errors import add_error, search_errors
from mnemo.incidents import add_incident, search_incidents
from mnemo.sprint import complete_task, get_current_task, set_current_task


def test_errors_use_storage_adapter(tmp_path: Path):
    add_error(tmp_path, "TimeoutError", "API was slow", "Add retry", tags=["payments"])

    assert "Add retry" in search_errors(tmp_path, "payments")
    data = json.loads((tmp_path / ".mnemo" / "errors.json").read_text(encoding="utf-8"))
    assert data[0]["error"] == "TimeoutError"


def test_incidents_use_storage_adapter(tmp_path: Path):
    add_incident(
        tmp_path,
        "Payments outage",
        "Checkout failed",
        "Gateway timeout",
        "Increased timeout",
        services=["payments"],
    )

    assert "Gateway timeout" in search_incidents(tmp_path, "payments")
    data = json.loads((tmp_path / ".mnemo" / "incidents.json").read_text(encoding="utf-8"))
    assert data[0]["title"] == "Payments outage"


def test_reviews_use_storage_adapter(tmp_path: Path):
    add_review(tmp_path, "Reviewed auth change", ["auth.py"], "Avoid globals", "rejected")

    assert get_reviews_for_file(tmp_path, "auth.py")[0]["feedback"] == "Avoid globals"
    assert get_rejected_suggestions(tmp_path)[0]["summary"] == "Reviewed auth change"


def test_tasks_use_storage_adapter(tmp_path: Path):
    set_current_task(tmp_path, "MNO-204", "Refactor collections", ["errors.py"])
    set_current_task(tmp_path, "MNO-204", files=["incidents.py"], notes="Moved to adapter")

    active = get_current_task(tmp_path)
    assert "MNO-204" in active
    assert "errors.py" in active
    assert "incidents.py" in active

    assert complete_task(tmp_path, "MNO-204", "Done") == "Task MNO-204 marked complete."
    data = json.loads((tmp_path / ".mnemo" / "tasks.json").read_text(encoding="utf-8"))
    assert data[0]["status"] == "completed"
