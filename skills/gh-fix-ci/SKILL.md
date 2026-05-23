---
name: gh-fix-ci
description: Find the first failing CI check, fix it, and re-run the smallest verification command.
---

# Fix CI

Find the first failing check, fix it, and re-run the smallest verification command.

## Steps

1. Identify failures
```bash
gh pr checks {PR} 2>/dev/null || true
gh run list --limit 10 2>/dev/null || true
```

2. Open logs (or paste the failure output). Focus on the root error.

3. Fix
- Prefer minimal, correct changes
- Do not “fix” by skipping tests

4. Verify locally (the narrowest command that covers the failure), then summarize:
- what failed
- what changed
- how to re-run

5. Push the fix (use `/gh-ship` or push directly)

**Merged-branch guard:** before pushing, confirm the branch's PR is still open.
```bash
gh pr view --json state,number,url -q '"\(.state) #\(.number) \(.url)"' 2>/dev/null || echo "NONE"
```
- If state is `MERGED`/`CLOSED`, pushing here strands the fix. **Auto-recover, no prompt** — move the fix to a fresh branch off HEAD and open a new PR for it:
  ```bash
  cur=$(git branch --show-current)
  new="${cur}-followup"
  git rev-parse --verify "$new" 2>/dev/null && new="${new}-$(date +%H%M%S)"
  git checkout -b "$new"
  ```
  Push `$new` and `gh pr create` a new PR; report it to the user. (A merged PR also means there's no live CI run to re-green — surface that.)
- If `OPEN`/`NONE`, push normally:

```bash
# SSH transport is auto-configured in Moat; credential helper covers non-Moat
gh auth setup-git 2>/dev/null || true
git push
```

## Moat

The `ssh:github.com` grant auto-configures SSH transport for `git push`.
`gh` subcommands (`pr checks`, `run list`) use the `github` grant's API access.