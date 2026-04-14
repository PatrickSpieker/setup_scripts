---
name: gh-address-pr-comments
description: Resolve actionable review comments for a PR, one-by-one.
---

# Address PR Comments

Resolve actionable review comments for a PR, one-by-one.

## Steps

1. Fetch PR data + comments
```bash
gh pr view {PR_NUMBER} --json title,body,state,author,headRefName,baseRefName,url,reviews
gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments
gh api repos/{OWNER}/{REPO}/issues/{PR_NUMBER}/comments
```

2. Checkout PR
```bash
gh pr checkout {PR}
```

3. Collect comments (review + issue comments)
```bash
gh pr view {PR_NUMBER} --json title -q .title
gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments
gh api repos/{OWNER}/{REPO}/issues/{PR_NUMBER}/comments
```

4. Present a numbered list of actionable items (prefer file+line refs). Ask user which to handle.

5. For each selected item:
- Show relevant code context
- Make the smallest correct change
- Add/update tests when needed

6. Summary
```bash
git status --short
git diff --stat
```

7. Commit + push fixes (use `/gh-commit` then push, or `/gh-ship`)
```bash
# SSH transport is auto-configured in Moat; credential helper covers non-Moat
gh auth setup-git 2>/dev/null || true
git push
```

## Moat

The `ssh:github.com` grant auto-configures SSH transport for `git push`.
`gh` subcommands (`pr view`, `api`, `pr checkout`) use the `github` grant's
API access.