"""Breaking change detector - compare current API signatures against baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS, mnemo_path
from ..repo_map import _extract_file, _should_ignore, MAX_FILE_SIZE

BASELINE_FILE = "api_baseline.json"


def _load_baseline(repo_root: Path) -> dict:
    path = mnemo_path(repo_root) / BASELINE_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_baseline(repo_root: Path, baseline: dict) -> None:
    path = mnemo_path(repo_root) / BASELINE_FILE
    path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")


def _current_git_tag(repo_root: Path) -> str | None:
    """Get the latest git tag if HEAD is tagged."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _baseline_tag(repo_root: Path) -> str | None:
    """Get the tag the baseline was saved at."""
    baseline = _load_baseline(repo_root)
    return baseline.get("tag")


def _extract_public_api(repo_root: Path) -> dict[str, list[str]]:
    """Extract all public class/method signatures from the codebase."""
    api: dict[str, list[str]] = {}

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            if "test" in rel.lower():
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue
            info = _extract_file(source, language)
            if not info:
                continue

            sigs = []
            for cls in info.get("classes", []):
                name = cls["name"]
                if name.startswith("_"):
                    continue
                impl = f" : {cls['implements']}" if cls.get("implements") else ""
                sigs.append(f"class {name}{impl}")
                for method in cls.get("methods", []):
                    mname = method.split("(")[0].split()[-1] if method else ""
                    if mname and not mname.startswith("_"):
                        sigs.append(f"  {method}")

            for func in info.get("functions", []):
                fname = func.split("(")[0].replace("def ", "").strip()
                if not fname.startswith("_"):
                    sigs.append(func)

            if sigs:
                api[rel] = sigs

    return api


def save_baseline(repo_root: Path) -> str:
    """Snapshot current public API as the baseline."""
    api = _extract_public_api(repo_root)
    tag = _current_git_tag(repo_root)
    baseline = {"timestamp": time.time(), "api": api, "tag": tag or ""}
    _save_baseline(repo_root, baseline)
    total = sum(len(v) for v in api.values())
    tag_info = f" at tag {tag}" if tag else ""
    return f"Baseline saved{tag_info}: {len(api)} files, {total} public symbols."


def detect_breaking_changes(repo_root: Path) -> str:
    """Compare current API against saved baseline. Auto-saves baseline on new tags."""
    # Auto-baseline: if HEAD is at a new tag, save baseline first
    current_tag = _current_git_tag(repo_root)
    saved_tag = _baseline_tag(repo_root)
    if current_tag and current_tag != saved_tag:
        save_baseline(repo_root)
        return f"New tag detected ({current_tag}). Baseline auto-saved. No breaking changes to compare yet."

    baseline = _load_baseline(repo_root)
    if not baseline or not baseline.get("api"):
        return "No API baseline found. Run `mnemo_breaking_changes` with action='baseline' first to snapshot current API."

    old_api = baseline["api"]
    new_api = _extract_public_api(repo_root)

    removed_files = []
    removed_symbols = []
    changed_symbols = []

    for file, old_sigs in old_api.items():
        if file not in new_api:
            removed_files.append(file)
            continue
        new_sigs = new_api[file]
        new_names = {s.split("(")[0].strip() for s in new_sigs}
        for sig in old_sigs:
            old_name = sig.split("(")[0].strip()
            if old_name not in new_names:
                removed_symbols.append({"file": file, "symbol": sig})
            elif sig not in new_sigs:
                # Signature changed
                changed_symbols.append({"file": file, "old": sig, "new": next(
                    (s for s in new_sigs if s.split("(")[0].strip() == old_name), "?"
                )})

    if not removed_files and not removed_symbols and not changed_symbols:
        return "No breaking changes detected against baseline."

    lines = ["# Breaking Changes Detected\n"]

    if removed_files:
        lines.append(f"## Removed Files ({len(removed_files)})\n")
        for f in removed_files:
            lines.append(f"- ❌ `{f}`")
        lines.append("")

    if removed_symbols:
        lines.append(f"## Removed Symbols ({len(removed_symbols)})\n")
        for s in removed_symbols[:30]:
            lines.append(f"- ❌ `{s['file']}`: `{s['symbol']}`")
        lines.append("")

    if changed_symbols:
        lines.append(f"## Changed Signatures ({len(changed_symbols)})\n")
        for s in changed_symbols[:30]:
            lines.append(f"- ⚠️  `{s['file']}`:")
            lines.append(f"  - Was: `{s['old']}`")
            lines.append(f"  - Now: `{s['new']}`")
        lines.append("")

    return "\n".join(lines)
