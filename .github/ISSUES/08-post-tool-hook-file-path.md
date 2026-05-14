---
title: "postToolUse hook should capture actual file path, not generic message"
labels: enhancement, P2, kiro
---

## Description

Current `postToolUse` hook for `fs_write` just remembers "File modified during session" — it doesn't capture which file was modified or what changed.

## Desired Behavior

The hook receives JSON via stdin with `tool_input` containing the file path. The hook script should parse this and remember the actual file:

```bash
#!/bin/sh
FILE=$(cat | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('path','unknown'))")
mnemo tool mnemo_remember --content "Modified: $FILE"
```

## Tasks

- [ ] Create `.kiro/hooks/mnemo-post-write.sh` that parses stdin JSON
- [ ] Update agent config to use the script
- [ ] Test that file paths are captured correctly
