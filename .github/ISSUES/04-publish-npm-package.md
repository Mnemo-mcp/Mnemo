---
title: "Publish @mnemo-mcp/mcp to npm"
labels: enhancement, deployment
---

## Description

NPX package at `packages/mcp/` is ready. Needs to be published.

## Pre-publish Checklist

- [x] Error handling for missing `mnemo` binary
- [x] Version synced to 0.3.0
- [x] License set to AGPL-3.0
- [x] engines field added (node >=14)
- [ ] Add README.md to the package explaining it's a shim
- [ ] Test: `npx @mnemo-mcp/mcp` shows helpful error when mnemo not installed
- [ ] Publish: `cd packages/mcp && npm publish --access public`
