---
title: "Package name mismatch: pyproject says mnemo-dev, docs say mnemo"
labels: bug, P1, docs
---

## Description

`pyproject.toml` has `name = "mnemo-dev"` but README says `pip install mnemo`. Users following the README will get a "package not found" error.

## Options

1. Rename package to `mnemo` on PyPI (breaking change for existing users)
2. Update README to say `pip install mnemo-dev`
3. Register `mnemo` as an alias/redirect on PyPI

## Decision Needed

Pick one before v0.4.0 release.
