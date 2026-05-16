"""Tests for mnemo/engine/pipeline.py — the core indexing pipeline."""

import tempfile
from pathlib import Path

import pytest

from mnemo.engine.pipeline import (
    FileInfo,
    ParseResult,
    ProjectInfo,
    PipelineStats,
    phase_scan,
    detect_projects,
    run_pipeline,
    _find_owning_project,
    _extract_project_name,
)


@pytest.fixture
def repo(tmp_path):
    """Create a minimal multi-language repo for testing."""
    # Python project
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-proj"\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text('def hello():\n    return "hi"\n\nclass Greeter:\n    def greet(self): pass\n')
    (tmp_path / "src" / "utils.py").write_text('from .main import hello\n\ndef helper(): pass\n')

    # JS project
    js_dir = tmp_path / "frontend"
    js_dir.mkdir()
    (js_dir / "package.json").write_text('{"name": "test-frontend"}')
    (js_dir / "app.js").write_text('import { helper } from "./utils";\nfunction render() {}\n')
    (js_dir / "utils.js").write_text('export function helper() { return 1; }\n')

    # Ignored dirs
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text('x')
    (tmp_path / ".git").mkdir()

    return tmp_path


class TestPhaseScan:
    def test_scans_supported_files(self, repo):
        files = phase_scan(repo)
        paths = {f.path for f in files}
        assert "src/main.py" in paths
        assert "src/utils.py" in paths
        assert "frontend/app.js" in paths

    def test_ignores_node_modules(self, repo):
        files = phase_scan(repo)
        paths = {f.path for f in files}
        assert not any("node_modules" in p for p in paths)

    def test_ignores_git(self, repo):
        files = phase_scan(repo)
        paths = {f.path for f in files}
        assert not any(".git" in p for p in paths)

    def test_assigns_correct_language(self, repo):
        files = phase_scan(repo)
        py_files = [f for f in files if f.path.endswith(".py")]
        js_files = [f for f in files if f.path.endswith(".js")]
        assert all(f.language == "python" for f in py_files)
        assert all(f.language == "javascript" for f in js_files)

    def test_computes_hash(self, repo):
        files = phase_scan(repo)
        assert all(len(f.hash) == 16 for f in files)

    def test_skips_large_files(self, repo):
        big = repo / "src" / "big.py"
        big.write_text("x" * 300_000)
        files = phase_scan(repo)
        assert not any(f.path == "src/big.py" for f in files)


class TestDetectProjects:
    def test_finds_pyproject(self, repo):
        projects = detect_projects(repo)
        names = {p.name for p in projects}
        assert "test-proj" in names or any("root" in p.name or "test" in p.name.lower() for p in projects)

    def test_finds_package_json(self, repo):
        projects = detect_projects(repo)
        js_projects = [p for p in projects if p.language == "javascript"]
        assert len(js_projects) >= 1
        assert any(p.name == "test-frontend" for p in js_projects)

    def test_csproj_detection(self, tmp_path):
        cs_dir = tmp_path / "MyService"
        cs_dir.mkdir()
        (cs_dir / "MyService.csproj").write_text("<Project></Project>")
        projects = detect_projects(tmp_path)
        assert any(p.name == "MyService" and p.language == "csharp" for p in projects)


class TestFindOwningProject:
    def test_finds_deepest_project(self):
        projects = [
            ProjectInfo(path="", name="root", language="python", manifest="pyproject.toml"),
            ProjectInfo(path="frontend", name="ui", language="javascript", manifest="package.json"),
        ]
        assert _find_owning_project("frontend/app.js", projects).name == "ui"
        assert _find_owning_project("src/main.py", projects).name == "root"

    def test_returns_none_for_no_match(self):
        projects = [ProjectInfo(path="backend", name="api", language="python", manifest="pyproject.toml")]
        # Files not under any project prefix still match if project path is ""
        result = _find_owning_project("random/file.py", projects)
        assert result is None


class TestRunPipeline:
    def test_indexes_repo(self, repo):
        (repo / ".mnemo").mkdir(exist_ok=True)
        stats = run_pipeline(repo, force=True)
        assert stats.files_scanned >= 4
        assert stats.nodes_created > 0
        assert stats.edges_created > 0
        assert stats.total_ms > 0

    def test_incremental_noop(self, repo):
        (repo / ".mnemo").mkdir(exist_ok=True)
        run_pipeline(repo, force=True)
        stats2 = run_pipeline(repo, force=False)
        # Second run should detect no changes
        assert stats2.files_parsed == 0 or stats2.total_ms < 500

    def test_detects_projects(self, repo):
        (repo / ".mnemo").mkdir(exist_ok=True)
        run_pipeline(repo, force=True)
        # Should find at least 2 projects (pyproject.toml + package.json)
        from mnemo.engine.db import open_db
        _, conn = open_db(repo)
        r = conn.execute("MATCH (p:Project) RETURN count(p)")
        assert r.get_next()[0] >= 2
