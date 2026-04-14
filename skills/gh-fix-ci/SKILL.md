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
```bash
gh auth setup-git 2>/dev/null || true
git push
```

## Moat

All remote operations use `gh`. For pushing fixes, `gh auth setup-git`
ensures git uses the `github` grant's credential helper.