---
name: xcode-agent
description: Build, test, and run iOS apps using the xcode-bridge MCP tools. Every tool call must include your branch name.
---

# Xcode Agent

Build, test, and debug iOS apps on a dedicated simulator via MCP tools.

## Setup

At the start of every session, run:
```bash
git branch --show-current
```
Store the result. You **must** pass it as `branch` to every MCP tool call.

## Available Tools

| Tool | Purpose |
|------|---------|
| `list_schemes` | Discover available schemes and targets |
| `resolve_dependencies` | Resolve Swift Package Manager packages |
| `xcodebuild` | Build, test, or clean (pass action: build/test/clean) |
| `install_and_launch` | Install .app on simulator and launch it |
| `screenshot` | Capture simulator screen (returns PNG image) |
| `build_log` | Read the most recent build log |
| `crash_log` | Read recent crash logs |
| `device_log` | Read simulator system log (filter by subsystem/process) |

## Workflow

1. `list_schemes` to discover the project structure
2. `resolve_dependencies` if the project uses Swift packages
3. `xcodebuild` with `action: "build"` and the scheme name
4. If build fails: read errors from the response, fix code, rebuild
5. `install_and_launch` to deploy to your simulator
6. `screenshot` to verify the UI looks correct
7. `xcodebuild` with `action: "test"` to run the test suite
8. If tests fail: fix code, rebuild, retest
9. If crashes: use `crash_log` and `device_log` to diagnose

## Rules

- **Always pass `branch`** to every tool call. The server uses it to route to your worktree and simulator.
- Build errors are returned inline in the tool response. Read them carefully before making changes.
- Screenshots are returned as images. Describe what you see to verify correctness.
- The simulator boots automatically on first use. You don't need to manage it.
