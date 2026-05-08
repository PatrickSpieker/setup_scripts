---
name: vscode-review
description: Open every changed file on the current branch in a new VS Code window — a diff tab (old vs working tree, editable on the right) and a plain live-file tab per file. Use when reviewing local changes from Claude Code or Codex before committing or pushing.
---

# VS Code Review

Open all branch-changed files in a new VS Code window so you can scroll, compare against `main`, and edit in place — no PR needed.

## What it opens

Per changed file, two tabs in the same new window:

- **Diff tab** — `code --diff <main-version> <working-file>`. Old version on the left (read-only), working tree on the right (editable; writes go to disk).
- **Live tab** — the working file as a plain editor. Drag this into a split if you want a wider edit canvas next to the diff.

VS Code's CLI can't pre-arrange editor groups, so layout is one tab per view. Drag a tab into a split once and the layout sticks for that session.

## Run

```bash
~/.claude/skills/vscode-review/scripts/open-review.sh
```

The script picks scope automatically — no flags.

## Scope

- **On a feature branch** (default): `git diff --name-only $(git merge-base main HEAD)` — committed-on-branch + uncommitted, vs the merge-base with `main` (or `master` if `main` doesn't exist). Untracked files (`git ls-files --others --exclude-standard`) are also included as new files.
- **On `main`/`master`**: falls back to uncommitted vs `HEAD` (also includes untracked).

Other behavior:
- **Binary files**: detected via `git diff --numstat`, skipped, listed in summary.
- **Deleted files**: not opened (nothing to edit), listed in summary.
- **New files**: diffed against an empty file.
- **Window**: always new (`code -n` for the first diff).
- **Snapshot of base versions**: written to `/tmp/vscode-review-<branch>-<short-base-sha>/`. Not auto-deleted on close so the diff tabs keep working; cleared by the OS on reboot.

## Requirements

- `code` CLI on PATH (VS Code → Cmd+Shift+P → "Shell Command: Install 'code' command in PATH").
- Inside a git repo with a `main` or `master` branch reachable from `HEAD`.
