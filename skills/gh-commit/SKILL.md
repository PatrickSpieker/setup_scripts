---
name: gh-commit
description: Create small, logical commits with conventional commit messages.
---

# Commit

Create small, logical commits with conventional commit messages.

## Steps

1. Safety
```bash
git branch --show-current
gh pr view --json state,number,url -q '"\(.state) #\(.number) \(.url)"' 2>/dev/null || echo "NONE"
```
- If on `main`/`master`: stop and create a branch: `git checkout -b feat/short-desc`
- **If the current branch's PR is already `MERGED` (or `CLOSED`):** committing here piles work onto a dead branch that a later push can't land. **Auto-recover, no prompt** — create a fresh branch off the current HEAD and commit there instead:
  ```bash
  default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
  git fetch origin "$default_branch:$default_branch" 2>/dev/null || git fetch origin "$default_branch"  # ff default; avoids a stale-base branch
  cur=$(git branch --show-current)
  new="${cur}-followup"   # or a fresh descriptive slug for the new work
  git rev-parse --verify "$new" 2>/dev/null && new="${new}-$(date +%H%M%S)"
  git checkout -b "$new"
  # Independent of the merged PR (not a follow-up)? base on the fresh default instead:
  # git stash -u && git checkout -b "$new" "origin/$default_branch" && git stash pop
  ```
  Tell the user you moved to `$new` and why.

2. Inspect changes
```bash
git status --porcelain
git diff --stat
```

3. Batch changes (typical: `feat|fix`, then `test`, then `docs`, then `refactor/chore`)
- Keep commits atomic
- Do not mix unrelated concerns
- Never `git add .`

4. Stage + commit each batch
```bash
git add path/to/file1 path/to/file2
git commit -m "type(scope): short description"
```

5. Summary
```bash
git log --oneline -10
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
git diff --stat origin/${DEFAULT_BRANCH}...HEAD
```

Read if present: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `.gitmessage`.

## Moat

When running inside Moat, use `gh` for all remote operations. Local git
commands (`status`, `diff`, `add`, `commit`, `log`, `branch`) are fine.