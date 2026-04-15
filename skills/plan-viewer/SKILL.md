---
name: plan-viewer
description: Localhost web viewer for Claude Code plan files with notes, repo filtering, and live updates.
---

# Plan Viewer

## Overview
A lightweight localhost web app for reviewing Claude Code plan files. Three-panel layout: plan picker/search sidebar, rendered markdown content, and per-plan notes. Plans update live as they're modified on disk.

## Quick Start
1. Create a local venv and install deps:
   ```bash
   uv venv
   uv add --dev watchfiles typer
   ```
2. Start the server:
   ```bash
   uv run python scripts/plan_server.py
   ```
3. Opens `http://localhost:8787` in your browser.

## Tasks

### Start the viewer
- Command: `uv run python scripts/plan_server.py`
- Options: `--port 9000`, `--no-open`, `--plans-dir /path/to/plans`
- Default: port 8787, opens browser, watches `~/.claude/plans/`

### Rebuild the plan-repo index
- Endpoint: `GET /api/reindex`
- Rescans session JSONL files to update which repo each plan belongs to
