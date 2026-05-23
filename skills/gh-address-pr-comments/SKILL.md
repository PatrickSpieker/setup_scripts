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
- **Check `state` first.** If it's `MERGED` (or `CLOSED`), the comments are historical and any fix you push to this branch is stranded. Surface that to the user; if they still want the changes made, the push in step 7 auto-recovers onto a fresh branch + new PR.

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

If the PR was `MERGED`/`CLOSED` (step 1), don't push to this branch — **auto-recover, no prompt**: move the fixes to a fresh branch off HEAD and open a new PR.
```bash
default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
git fetch origin "$default_branch:$default_branch" 2>/dev/null || git fetch origin "$default_branch"  # ff default; avoids a stale-base branch
cur=$(git branch --show-current)
new="${cur}-followup"
git rev-parse --verify "$new" 2>/dev/null && new="${new}-$(date +%H%M%S)"
git checkout -b "$new"
# Independent of the merged PR (not a follow-up)? base on the fresh default instead:
# git stash -u && git checkout -b "$new" "origin/$default_branch" && git stash pop
```
Otherwise push to the open PR's branch:
```bash
# SSH transport is auto-configured in Moat; credential helper covers non-Moat
gh auth setup-git 2>/dev/null || true
git push
```

## Moat

The `ssh:github.com` grant auto-configures SSH transport for `git push`.
`gh` subcommands (`pr view`, `api`, `pr checkout`) use the `github` grant's
API access.