---
title: "Deploy website to GitHub Pages"
labels: enhancement, deployment
---

## Description

Website is rewritten and builds successfully. Need to deploy it.

## Tasks

- [ ] Add `.github/workflows/pages.yml` (see deployment_plan.md)
- [ ] Update `website/next.config.mjs` with `output: 'export'` and `basePath: '/Mnemo'`
- [ ] Enable GitHub Pages in repo settings (Source: GitHub Actions)
- [ ] Verify at https://mnemo-mcp.github.io/Mnemo
