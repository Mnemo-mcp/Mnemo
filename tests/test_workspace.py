"""Sandbox tests for mnemo/workspace/ — multi-repo linking and cross-repo queries."""

import json
from pathlib import Path

import pytest

from mnemo.workspace import (
    _normalize_links,
    cross_repo_impact,
    cross_repo_semantic_query,
    discover_repos,
    format_links,
    get_linked_repos,
    link_repo,
    unlink_repo,
)


def _make_repo(tmp_path: Path, name: str, init_mnemo: bool = True) -> Path:
    """Create a fake repo directory with optional .mnemo."""
    repo = tmp_path / name
    repo.mkdir()
    (repo / ".git").mkdir()
    if init_mnemo:
        mnemo = repo / ".mnemo"
        mnemo.mkdir()
        (mnemo / "memory.json").write_text("[]")
    return repo


class TestNormalizeLinks:
    """Test links.json normalization logic."""

    def test_list_of_dicts(self):
        data = [{"name": "foo", "path": "/tmp/foo"}]
        assert _normalize_links(data) == [{"name": "foo", "path": "/tmp/foo"}]

    def test_list_of_strings(self):
        result = _normalize_links(["/tmp/foo", "/tmp/bar"])
        assert len(result) == 2
        assert result[0]["name"] == "foo"
        assert result[0]["path"] == "/tmp/foo"

    def test_dict_with_links_key(self):
        data = {"links": [{"name": "a", "path": "/tmp/a"}]}
        assert _normalize_links(data) == [{"name": "a", "path": "/tmp/a"}]

    def test_empty_list(self):
        assert _normalize_links([]) == []

    def test_invalid_data(self):
        assert _normalize_links(None) == []
        assert _normalize_links("string") == []
        assert _normalize_links(42) == []


class TestLinkRepo:
    """Test linking repos together."""

    def test_link_valid_repo(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other")

        result = link_repo(main, other)
        assert "Linked: other" in result
        assert "indexed" in result

    def test_link_uninitialized_repo(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other", init_mnemo=False)

        result = link_repo(main, other)
        assert "Linked: other" in result
        assert "needs `mnemo init`" in result

    def test_link_nonexistent_path(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        result = link_repo(main, tmp_path / "nonexistent")
        assert "does not exist" in result

    def test_link_not_a_repo(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        plain_dir = tmp_path / "plain"
        plain_dir.mkdir()
        result = link_repo(main, plain_dir)
        assert "Not a repo" in result

    def test_link_duplicate_rejected(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other")

        link_repo(main, other)
        result = link_repo(main, other)
        assert "Already linked" in result

    def test_link_persists_to_disk(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other")

        link_repo(main, other)
        links_path = main / ".mnemo" / "links.json"
        assert links_path.exists()
        data = json.loads(links_path.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "other"


class TestUnlinkRepo:
    """Test unlinking repos."""

    def test_unlink_by_name(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other")
        link_repo(main, other)

        result = unlink_repo(main, "other")
        assert "Unlinked" in result

        linked = get_linked_repos(main)
        assert len(linked) == 0

    def test_unlink_nonexistent(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        result = unlink_repo(main, "nosuchrepo")
        assert "No linked repos" in result

    def test_unlink_from_multiple(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        a = _make_repo(tmp_path, "repo_a")
        b = _make_repo(tmp_path, "repo_b")
        link_repo(main, a)
        link_repo(main, b)

        unlink_repo(main, "repo_a")
        linked = get_linked_repos(main)
        assert len(linked) == 1
        assert linked[0].name == "repo_b"


class TestGetLinkedRepos:
    """Test retrieval of linked repos."""

    def test_empty_when_no_links_file(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        assert get_linked_repos(main) == []

    def test_returns_only_existing_initialized_repos(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        good = _make_repo(tmp_path, "good")  # has .mnemo
        uninit = _make_repo(tmp_path, "uninit", init_mnemo=False)

        link_repo(main, good)
        link_repo(main, uninit)

        linked = get_linked_repos(main)
        # Only returns repos that have .mnemo
        assert any(r.name == "good" for r in linked)
        assert not any(r.name == "uninit" for r in linked)

    def test_handles_corrupt_links_file(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        (main / ".mnemo" / "links.json").write_text("not json!!!")
        assert get_linked_repos(main) == []


class TestDiscoverRepos:
    """Test auto-discovery of repos under a directory."""

    def test_discovers_git_repos(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        _make_repo(tmp_path, "service_a")
        _make_repo(tmp_path, "service_b")

        result = discover_repos(main, tmp_path)
        assert "service_a" in result
        assert "service_b" in result

    def test_skips_self(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        discover_repos(main, tmp_path)
        # Should not link itself
        linked = get_linked_repos(main)
        assert not any(r.resolve() == main.resolve() for r in linked)

    def test_nonexistent_directory(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        result = discover_repos(main, tmp_path / "nope")
        assert "not found" in result

    def test_empty_directory(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        empty = tmp_path / "empty"
        empty.mkdir()
        result = discover_repos(main, empty)
        assert "No git repos" in result


class TestFormatLinks:
    """Test format_links display output."""

    def test_no_links(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        result = format_links(main)
        assert "No linked repos" in result

    def test_shows_linked_repos(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other")
        link_repo(main, other)

        result = format_links(main)
        assert "other" in result
        assert "indexed" in result


class TestCrossRepoSearch:
    """Test cross-repo semantic query and impact analysis."""

    def test_cross_search_with_no_links(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        # Should return empty results (no vectors indexed)
        results = cross_repo_semantic_query(main, "memory", "test query")
        assert isinstance(results, list)

    def test_cross_impact_no_links(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        result = cross_repo_impact(main, "AuthService")
        assert "Cross-Repo Impact" in result
        assert "No linked repos" in result

    def test_cross_impact_with_linked_repo(self, tmp_path):
        main = _make_repo(tmp_path, "main")
        other = _make_repo(tmp_path, "other")
        link_repo(main, other)

        result = cross_repo_impact(main, "AuthService")
        assert "Cross-Repo Impact" in result
        assert "other" in result
