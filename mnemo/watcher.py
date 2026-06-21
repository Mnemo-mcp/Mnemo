#!/usr/bin/env python3.12
"""Mnemo session watcher — tails live Kiro session, captures to memory in real-time."""

import json
import time
from pathlib import Path

SESSION_DIR = Path.home() / ".kiro" / "sessions" / "cli"
MNEMO_BIN = "/Users/nikhil.tiwari/Library/Python/3.12/bin/mnemo"

def find_active_session():
    """Find the most recently modified .jsonl file."""
    jsonl_files = sorted(SESSION_DIR.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    return jsonl_files[0] if jsonl_files else None

def classify_and_capture(text: str, repo_root: str):
    """Send text to mnemo auto_capture."""
    if len(text) < 30:
        return
    import subprocess
    result = subprocess.run(
        [MNEMO_BIN, "tool", "mnemo_auto_capture", "--message", text[:500]],
        capture_output=True, text=True, cwd=repo_root, timeout=5
    )
    output = result.stdout.strip()
    if output.startswith("captured"):
        print(f"  📌 {output}")

def extract_text_from_event(event: dict) -> str:
    """Extract readable text from an event."""
    content = event.get("data", {}).get("content", [])
    texts = []
    for block in content:
        if block.get("kind") == "text" and block.get("data"):
            texts.append(block["data"])
    return "\n".join(texts)

def watch(repo_root: str = "/Users/nikhil.tiwari/CodeRepo/Mnemo"):
    """Tail the active session and capture in real-time."""
    session_file = find_active_session()
    if not session_file:
        print("No active session found.")
        return

    print(f"👁️  Watching: {session_file.name}")
    print(f"📂 Repo: {repo_root}")
    print("---")

    # Start from current end of file
    with open(session_file) as f:
        f.seek(0, 2)  # Seek to end
        lines_seen = 0

        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = event.get("kind")

            if kind == "Prompt":
                text = extract_text_from_event(event)
                if text:
                    print(f"\n👤 User: {text[:100]}...")
                    classify_and_capture(text, repo_root)

            elif kind == "AssistantMessage":
                text = extract_text_from_event(event)
                if text and len(text) > 50:
                    print(f"\n🤖 Agent: {text[:100]}...")
                    # Check for decisions/learnings in agent response
                    for phrase in ["decided to", "I'll use", "the issue was", "the pattern is",
                                   "convention", "going with", "chose", "following"]:
                        if phrase in text.lower():
                            classify_and_capture(text[:300], repo_root)
                            break

            lines_seen += 1
            if lines_seen % 10 == 0:
                mem_path = Path(repo_root) / ".mnemo" / "memory.json"
                if mem_path.exists():
                    count = len(json.loads(mem_path.read_text()))
                    print(f"  💾 Memory: {count} entries")

if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "/Users/nikhil.tiwari/CodeRepo/Mnemo"
    watch(repo)
