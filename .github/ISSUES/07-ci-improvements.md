---
title: "CI improvements: pip caching, coverage, test before publish"
labels: enhancement, P3, ci
---

## Description

Current CI works but has gaps.

## Tasks

- [ ] Add pip dependency caching to ci.yml (faster builds)
- [ ] Add coverage reporting (pytest-cov + upload to codecov or similar)
- [ ] Add test step to release.yml before PyPI publish
- [ ] Add npm publish workflow for packages/mcp on tag push
