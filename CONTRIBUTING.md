# Contributing to Mnemo

## Development Setup

```bash
git clone https://github.com/Mnemo-mcp/Mnemo.git
cd Mnemo
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
python3 -m pytest tests/ -x -q
```

For verbose output:

```bash
python3 -m pytest tests/ -v
```

## Checklists for Common Changes

### Adding a New MCP Tool

1. Add the tool function in the appropriate module
2. Register it in `mnemo/tool_registry.py`
3. Add a test in `tests/`
4. Update the MCP Tools table in `README.md`

### Adding a Graph Node Type

1. Update the graph builder in `mnemo/graph/`
2. Add the node type to `NODE_COLORS` in `mnemo/ui/templates/dashboard.html`
3. Add a test covering the new node type
4. Update the Knowledge Graph tables in `README.md`

### Changing Memory Schema

1. Update `mnemo/memory.py` (or relevant storage module)
2. Ensure backward compatibility — old `.mnemo/memory.json` files must still load
3. Add a migration path or graceful fallback for missing fields
4. Add/update tests

### Bumping Version

1. Update version in `pyproject.toml`
2. Update any version references in docs if applicable

## Code Style

- Follow existing patterns in the codebase
- Use type hints for all function signatures
- Add docstrings to public functions and classes
- Keep functions focused and small
- Use `from __future__ import annotations` in new files
- Imports: stdlib → third-party → local, separated by blank lines

## PR Process

1. Fork the repo and create a feature branch from `main`
2. Make your changes following the style guidelines above
3. Run `python3 -m pytest tests/ -x -q` and ensure all tests pass
4. Write a clear PR title (under 70 chars) and description
5. Link any related issues
6. Request review — one approval required to merge
