---
name: ship-plan
description: Open a fresh PR off main whose description IS the current implementation plan, with an empty marker commit. Plan-first review on GitHub before any code lands. Use after exiting plan mode or when the user wants to review a plan in a PR before building.
---

# Ship Plan

Open a regular PR on a new `feat/<slug>` branch where the **PR description is the plan**. Single empty commit (`plan: <slug>`); no `docs/plans/` file. Implementation commits land on the same branch later.

## When to use

- Just exited plan mode and the user wants the plan reviewed in a PR before any code.
- The user says "ship this plan", "open a PR for the plan", "/ship-plan".

## Hard rules

- **Empty marker commit only.** Branch starts with `git commit --allow-empty -m "plan: <slug>"`. No staged files. Refuse if working tree is dirty — uncommitted changes would leak onto the plan branch.
- **Branch off main, never push to main.** New `feat/<slug>` branch from a freshly-fetched `origin/main` (or the repo's default branch).
- **Confirm before push.** Print the plan, slug, title, branch, base, then ask the user to confirm. Don't push silently.
- **Don't invent a plan.** If neither a recent plan-mode file nor a conversation plan exists, stop and tell the user to produce one first.

## Steps

### 1. Find the plan

Two sources, in priority order:

1. **Most recent `~/.claude/plans/*.md`** (plan mode writes here). Use if mtime is within the last hour OR the user just exited plan mode this session.
2. **Conversation context.** If no recent file exists but the user has clearly produced a plan in chat (multi-section markdown with steps/files/etc.), use that.

Pick whichever applies. If both exist, prefer the file (the user explicitly entered plan mode). If neither: stop, ask the user to produce a plan.

### 2. Derive slug + title

```bash
title=$(grep -m1 '^# ' "$plan_src" | sed 's/^# //')      # if from file
# Slug: lowercase, non-alnum → '-', collapse, trim, cap at 50 chars.
slug=$(echo "$title" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9]/-/g; s/-\+/-/g; s/^-//; s/-$//' \
  | cut -c1-50 | sed 's/-$//')
branch="feat/$slug"
```

If the plan has no H1, synthesize a short title from the first paragraph and ask the user to confirm in step 4.

### 3. Pre-flight

```bash
git rev-parse --is-inside-work-tree >/dev/null || { echo "Not in a git repo"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "Working tree dirty — commit, stash, or discard first."; exit 1; }
git fetch origin >/dev/null
default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
git rev-parse --verify "$branch" 2>/dev/null && { echo "Branch $branch exists already; pick a different slug."; exit 1; }
```

**Moat SSH preflight** (mirrors `/gh-ship`):

```bash
ssh -T git@github.com 2>&1
```

- `Hi <user>!` → SSH works, proceed.
- `Permission denied (publickey)` → stop, tell the user:
  > `git push` will fail — the `ssh:github.com` grant's SSH agent has no keys loaded.
  > On your host machine, run `ssh-add` (load your key), then restart the Moat run.

  Do **not** switch remotes to HTTPS, unset insteadOf rules, or push via the GitHub API. The system git config rewrites HTTPS→SSH and the network proxy blocks direct HTTPS to github.com.

### 4. Confirm with the user

Print:
- The PR title that will be used.
- The slug + branch (`feat/<slug>`).
- The base branch (default branch from step 3).
- The full plan body, exactly as it will appear in the PR description.

Ask the user to confirm or tell you what to change (slug, title, content). Do not proceed until they say yes.

### 5. Create branch + marker commit

```bash
git checkout -b "$branch" "origin/$default_branch"
git commit --allow-empty -m "plan: $slug"
```

### 6. Push

```bash
gh auth setup-git 2>/dev/null || true
git push -u origin "$branch"
```

### 7. Open the PR

```bash
gh pr create \
  --base "$default_branch" \
  --title "$title" \
  --body-file - <<'EOF'
<the full plan from step 1, verbatim>
EOF
```

Print the PR URL. Tell the user that implementation commits should land on the same branch (`feat/<slug>`); the PR description stays as the plan and can be revised via `gh pr edit --body-file`.

## Edge cases

- **Plan has no H1:** synthesize a short title from the first paragraph; surface it explicitly in step 4 so the user can override.
- **Slug collision (`feat/<slug>` exists locally or remotely):** stop and ask the user for a new slug. Don't silently append `-2`.
- **Working tree dirty:** refuse. The plan branch must start clean — uncommitted edits don't belong on a "review the plan" PR.
- **Multiple plan files in `~/.claude/plans/`:** list the 5 most recent by mtime, default to the newest, let the user pick by index or path.
- **No `origin` remote:** stop — `gh pr create` would fail anyway.
- **Repo's default branch isn't `main`:** the script reads it from `gh repo view`; works for `master` or anything else.

## What happens after merge

Implementation lands on the same branch as additional commits. The PR description (the plan) stays as the historical record of intent for that PR; if the plan changes during implementation, edit the PR description with `gh pr edit --body-file` so reviewers see the current plan.

## Moat

The `ssh:github.com` grant proxies the host's SSH agent into the container — private keys never enter the container. The system git config rewrites HTTPS GitHub URLs to SSH, so all git transport goes through SSH. `gh` subcommands use the `github` grant's API access. See `/gh-ship` for the full SSH-failure protocol.

Read if present: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`.
