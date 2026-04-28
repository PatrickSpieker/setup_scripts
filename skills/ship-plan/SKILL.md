---
name: ship-plan
description: Commit the latest plan-mode plan file to docs/plans/<slug>.md on a fresh branch and open a PR for review. Plan only, no code. Use when the user wants to review a long Claude-produced plan in GitHub before any implementation.
---

# Ship Plan

Commit the most recent plan-mode plan file to `docs/plans/<slug>.md` on a new branch and open a PR whose only diff is that one file. Reviewers leave inline comments on the file. No implementation in this PR.

## When to use

- Claude has just produced a long plan (typically via plan mode → file in `~/.claude/plans/`) and the user wants to review it on GitHub before building.
- Triggers: "ship this plan", "open a PR for the plan", "let's review this plan in GitHub", "/ship-plan".

## Hard rules

- **Plan-only diff.** The PR must contain exactly one file: `docs/plans/<slug>.md`. Refuse to proceed if anything else is staged or modified.
- **No `git add .` / `git add -A`.** Only `git add docs/plans/<slug>.md`.
- **Never branch from main/master and push to main/master.** Always create a fresh `plan/<slug>` branch.
- **Don't invent a plan.** If no plan file exists, stop and tell the user to produce one first.

## Steps

### 1. Locate the plan file

```bash
ls -t ~/.claude/plans/*.md 2>/dev/null | head -5
```

- Pick the most recently modified.
- Show the user the path and its first H1; ask them to confirm or pass a different path.
- If `~/.claude/plans/` is empty: stop. Tell the user to produce a plan first (plan mode, `/design-doc`, or written by hand).

### 2. Derive metadata

```bash
plan_src=<path-the-user-confirmed>
title=$(grep -m1 '^# ' "$plan_src" | sed 's/^# //')
# Slug: lowercase, non-alnum → '-', collapse runs, trim, cap at 50 chars.
slug=$(echo "$title" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9]/-/g; s/-\+/-/g; s/^-//; s/-$//' \
  | cut -c1-50 | sed 's/-$//')
branch="plan/$slug"
dest="docs/plans/$slug.md"
```

If the plan has no H1, ask the user for a title.

### 3. Pre-flight

```bash
git rev-parse --is-inside-work-tree >/dev/null || { echo "Not in a git repo"; exit 1; }
current=$(git branch --show-current)
git status --porcelain
```

- If working tree is dirty (any line of `git status --porcelain`): stop and report. The skill's invariant is "only the plan file in this PR."
- If the branch already exists (`git rev-parse --verify "$branch" 2>/dev/null`): ask user whether to switch to it (revising the existing plan PR) or pick a different slug.
- If `docs/plans/$slug.md` already exists on disk on the target branch: ask whether to overwrite (revision) or pick a different slug.

**Moat SSH preflight** (mirrors `/gh-ship`):

```bash
ssh -T git@github.com 2>&1
```

- `Hi <user>!` → SSH works, proceed.
- `Permission denied (publickey)` → stop, tell the user:
  > `git push` will fail — the `ssh:github.com` grant's SSH agent has no keys loaded.
  > On your host machine, run `ssh-add` (load your key), then restart the Moat run.

  Do **not** attempt to switch remotes to HTTPS, unset insteadOf rules, or push via the GitHub API. The system git config rewrites HTTPS→SSH and the network proxy blocks direct HTTPS to github.com.

### 4. Create the branch

```bash
git checkout -b "$branch"
```

(If `current` is already `$branch` because the user explicitly chose to revise an existing plan PR, skip this step.)

### 5. Stage and commit (only the plan file)

```bash
mkdir -p docs/plans
cp "$plan_src" "$dest"
git add "$dest"

# Verify nothing else is staged.
staged=$(git diff --cached --name-only)
[ "$staged" = "$dest" ] || { echo "ERROR: more than the plan is staged: $staged"; exit 1; }

git commit -m "plan: $title"
```

### 6. Push

```bash
gh auth setup-git 2>/dev/null || true
git push -u origin "$branch"
```

### 7. Open the PR

```bash
default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)

gh pr create \
  --base "$default_branch" \
  --title "plan: $title" \
  --body-file - <<EOF
## Summary

<1–3 lines lifted from the plan's Context section, or synthesized if absent>

## How to review

This PR contains **only the plan** at \`$dest\`. No implementation.
Leave inline comments on the file in the **Files Changed** tab.

## What happens next

After review, run \`/gh-address-pr-comments <PR#>\` in a fresh Claude session
to pull comments back, revise the plan, and push another commit. Once the
plan is approved, implementation happens in a separate PR.
EOF
```

Print the PR URL.

## Edge cases

- **Plan file has no H1:** ask the user for a title; don't guess.
- **Slug collides with existing `docs/plans/<slug>.md`:** ask whether to overwrite (revision) or pick a new slug.
- **`docs/plans/` doesn't exist:** `mkdir -p` creates it; the plan file itself populates the directory (no `.gitkeep` needed).
- **Repo has no `origin`:** stop and report — `gh pr create` would fail anyway.
- **Multiple plan files in `~/.claude/plans/`:** list them by mtime, default to most recent, let the user pick by index or path.
- **User invokes from a feature branch with a dirty tree:** refuse. The invariant is one-file diff.

## Moat

The `ssh:github.com` grant proxies the host's SSH agent into the container — private keys never enter the container. The system git config rewrites HTTPS GitHub URLs to SSH, so all git transport goes through SSH. `gh` subcommands use the `github` grant's API access. See `/gh-ship` for the full SSH-failure protocol.

Read if present: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`.
