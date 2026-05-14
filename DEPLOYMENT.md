# Mnemo Release & Deployment Playbook

> Use this document for every release. Follow steps in order. Check off as you go.

## Package Names & Locations

| Platform | Package Name | URL |
|----------|-------------|-----|
| PyPI | `mnemo-dev` | https://pypi.org/project/mnemo-dev/ |
| npm | `@mnemo-dev/mcp` | https://www.npmjs.com/package/@mnemo-dev/mcp |
| Homebrew | `mnemo` (tap: `Mnemo-mcp/tap`) | https://github.com/Mnemo-mcp/homebrew-tap |
| VS Code | `mnemo-vscode` (publisher: Nikhil1057) | VS Code Marketplace |
| GitHub | `Mnemo-mcp/Mnemo` | https://github.com/Mnemo-mcp/Mnemo |
| Website | GitHub Pages | https://mnemo-mcp.github.io/Mnemo/ |

## Files That Contain Version Numbers

Update ALL of these when bumping version:

| File | Field |
|------|-------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `mnemo/__init__.py` | `__version__ = "X.Y.Z"` |
| `packages/mcp/package.json` | `"version": "X.Y.Z"` |
| `vscode-extension/package.json` | `"version": "X.Y.Z"` |
| `homebrew-tap/Formula/mnemo.rb` | `version "X.Y.Z"` |

## Files That Reference Package Names

If package name ever changes, update:

| File | What to update |
|------|---------------|
| `README.md` | `pip install mnemo-dev`, `npx @mnemo-dev/mcp` |
| `vscode-extension/README.md` | Links section |
| `website/components/Install.tsx` | Install commands in tabs |
| `packages/mcp/README.md` | Package description |
| `.github/workflows/release.yml` | PyPI publish config |

---

## Release Process (Step by Step)

### 1. Pre-Release Checks

```bash
# Ensure tests pass
python3 -m pytest tests/ -q

# Ensure lint passes
python3 -m ruff check .

# Verify tool count
python3 -c "from mnemo.tool_registry import registered_names; print(f'{len(registered_names())} tools')"
```

### 2. Bump Version

```bash
# Update all version files (replace X.Y.Z with new version)
sed -i '' 's/version = ".*"/version = "X.Y.Z"/' pyproject.toml
sed -i '' 's/__version__ = ".*"/__version__ = "X.Y.Z"/' mnemo/__init__.py
cd packages/mcp && npm version X.Y.Z --no-git-tag-version && cd ../..
```

### 3. Update CHANGELOG

Add entry to `CHANGELOG.md` with:
- New features
- Bug fixes
- Breaking changes (if any)

### 4. Commit & Tag

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

### 5. PyPI (Automatic)

- Triggered by: tag push (`release.yml` workflow)
- Verify: https://pypi.org/project/mnemo-dev/X.Y.Z/
- If fails: check workflow logs, re-run from Actions tab

### 6. npm Publish (Manual)

```bash
cd packages/mcp
npm publish --access public
```

- Requires: npm login + org membership in `@mnemo-dev`
- Verify: https://www.npmjs.com/package/@mnemo-dev/mcp

### 7. GitHub Release (Manual)

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes
```

Or create at: https://github.com/Mnemo-mcp/Mnemo/releases/new?tag=vX.Y.Z

- This triggers `binary-release.yml` → builds macOS arm64, macOS x64, Linux x64

### 8. Homebrew Formula (Manual)

After binaries are built (~5 min after GitHub Release):

```bash
# Download and hash binaries
curl -sL "https://github.com/Mnemo-mcp/Mnemo/releases/download/vX.Y.Z/mnemo-darwin-arm64" | shasum -a 256
curl -sL "https://github.com/Mnemo-mcp/Mnemo/releases/download/vX.Y.Z/mnemo-darwin-x64" | shasum -a 256
curl -sL "https://github.com/Mnemo-mcp/Mnemo/releases/download/vX.Y.Z/mnemo-linux-x64" | shasum -a 256

# Update formula
cd /path/to/homebrew-tap
# Edit Formula/mnemo.rb: update version + sha256 values
git add Formula/mnemo.rb
git commit -m "vX.Y.Z: update SHA256 from release binaries"
git push origin main
```

### 9. VS Code Extension (Manual)

```bash
cd vscode-extension
# Update version in package.json (already done in step 2 if using npm version)
vsce publish
```

- Requires: `vsce` CLI + Personal Access Token
- Verify: VS Code Marketplace

### 10. Website (Automatic)

- Triggered by: push to `main` with changes in `website/`
- If content needs updating, edit `website/components/*.tsx`
- Verify: https://mnemo-mcp.github.io/Mnemo/

---

## Rollback Procedures

### PyPI
PyPI doesn't allow re-uploading the same version. If broken:
1. Bump to X.Y.Z+1 (patch)
2. Fix the issue
3. Re-release

### npm
```bash
npm unpublish @mnemo-dev/mcp@X.Y.Z  # within 72 hours only
# Or publish a fix version
```

### Homebrew
```bash
cd homebrew-tap
git revert HEAD
git push origin main
```

### GitHub Release
Delete the release from the web UI, fix, re-create.

---

## CI/CD Workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | Push to main, PRs | Lint + test (Python 3.10-3.12) |
| `release.yml` | Tag `v*` pushed | Build + publish to PyPI |
| `binary-release.yml` | GitHub Release created | Build binaries (3 platforms) |
| `pages.yml` | Push to main (website/) | Build Next.js + deploy to Pages |

---

## Verification Checklist (Post-Release)

- [ ] `pip install mnemo-dev==X.Y.Z && mnemo --version` shows correct version
- [ ] `npx @mnemo-dev/mcp` runs (or shows helpful error if mnemo not installed)
- [ ] `brew tap Mnemo-mcp/tap && brew install mnemo && mnemo --version` works
- [ ] https://mnemo-mcp.github.io/Mnemo/ loads correctly
- [ ] https://pypi.org/project/mnemo-dev/ shows new version
- [ ] https://www.npmjs.com/package/@mnemo-dev/mcp shows new version
- [ ] GitHub Release has 3 binary assets attached
- [ ] `mnemo init` works on a fresh repo
- [ ] `mnemo init --client kiro` generates correct agent config

---

## Contacts & Access

| Service | Account/Access |
|---------|---------------|
| PyPI | Token in GitHub Secrets (`PYPI_API_TOKEN`) |
| npm | Org: `@mnemo-dev`, auth via `npm login` |
| GitHub | Org: `Mnemo-mcp` |
| VS Code Marketplace | Publisher: `Nikhil1057` |
| Homebrew tap | Repo: `Mnemo-mcp/homebrew-tap` |
