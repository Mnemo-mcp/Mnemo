# Mnemo Distribution Channels

All places where Mnemo is published and installable from.

## Install Methods

| Method | Package/Command | Registry |
|--------|----------------|----------|
| **pip** | `pip install mnemo-dev` | [PyPI](https://pypi.org/project/mnemo-dev/) |
| **npx** | `npx @mnemo-dev/mcp` | [npm](https://www.npmjs.com/package/@mnemo-dev/mcp) |
| **Homebrew** | `brew tap Mnemo-mcp/tap && brew install mnemo` | [GitHub tap](https://github.com/Mnemo-mcp/homebrew-tap) |
| **VS Code** | Extension marketplace → "Mnemo" | [Marketplace](https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode) |
| **Binary** | Download from GitHub Releases | [Releases](https://github.com/Mnemo-mcp/Mnemo/releases) |
| **Source** | `git clone` + `pip install -e .` | [GitHub](https://github.com/Mnemo-mcp/Mnemo) |

## Packages

| Package | Name | Version | Location |
|---------|------|---------|----------|
| Python (PyPI) | `mnemo-dev` | 0.5.0 | `pyproject.toml` |
| npm shim | `@mnemo-dev/mcp` | 0.4.0 | `packages/mcp/package.json` |
| VS Code extension | `mnemo-vscode` | 0.5.0 | `vscode-extension/package.json` |
| Homebrew formula | `mnemo` | 0.4.0 | `Mnemo-mcp/homebrew-tap` repo |
| Binary (macOS ARM) | `mnemo-darwin-arm64` | — | GitHub Releases |
| Binary (macOS x64) | `mnemo-darwin-x64` | — | GitHub Releases |
| Binary (Linux x64) | `mnemo-linux-x64` | — | GitHub Releases |
| Binary (Windows) | `mnemo-win-x64.exe` | — | GitHub Releases |

## Repos

| Repo | Purpose | URL |
|------|---------|-----|
| **Mnemo** (main) | Core package, MCP server, engine | https://github.com/Mnemo-mcp/Mnemo |
| **homebrew-tap** | Homebrew formula | https://github.com/Mnemo-mcp/homebrew-tap |
| **Website** | Landing page (Next.js, GitHub Pages) | https://mnemo-mcp.github.io/Mnemo/ |

## CI/CD Pipelines

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | Push to main, PRs | Lint + test (Python 3.10, 3.11, 3.12) |
| `release.yml` | Tag `v*` | Build + publish to PyPI |
| `binary-release.yml` | GitHub Release published | PyInstaller binaries (macOS/Linux/Windows) |
| `pages.yml` | Push to main (`website/` changes) | Deploy Next.js site to GitHub Pages |

## Release Checklist (update ALL on release)

- [ ] `pyproject.toml` → version
- [ ] `mnemo/__init__.py` → `__version__`
- [ ] `vscode-extension/package.json` → version
- [ ] `packages/mcp/package.json` → version
- [ ] `homebrew-tap/Formula/mnemo.rb` → version + SHA256 hashes
- [ ] `CHANGELOG.md` → release notes
- [ ] Git tag `v{X.Y.Z}`
- [ ] `vsce publish` (VS Code)
- [ ] `npm publish` in `packages/mcp/` (npm)
- [ ] Homebrew: update formula hashes after binaries are built
