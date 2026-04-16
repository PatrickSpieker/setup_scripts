---
name: gh-ship
description: Commit, push, and create PR in one step.
---

# Ship

Commit, push, and create PR in one step.

## Steps

1. Safety check
```bash
git branch --show-current
```
- If on `main`/`master`: stop and create a branch: `git checkout -b feat/short-desc`

2. Inspect changes
```bash
git status --porcelain
git diff --stat
```
- If no changes, stop

3. Stage + commit
```bash
git add path/to/file1 path/to/file2
git commit -m "type(scope): short description"
```
- Never `git add .`
- One commit unless changes are clearly separate concerns

4. Push

**Pre-flight** (Moat only): verify SSH is working before attempting push.
```bash
ssh -T git@github.com 2>&1
```
- If you see `Hi <user>!` → SSH works, proceed with push.
- If you see `Permission denied (publickey)` → SSH agent has no keys.
  **Stop and tell the user:**
  > `git push` failed — the `ssh:github.com` grant's SSH agent has no keys loaded.
  > This usually means your host SSH agent didn't have GitHub keys when Moat started.
  > Fix: on your host machine, run `ssh-add` (load your key), then restart the Moat run.

  **Do not** attempt to switch remotes to HTTPS, unset insteadOf rules, reconfigure
  credentials, or push via the GitHub API. These workarounds will not work because
  the system-level git config rewrites HTTPS→SSH and the network proxy blocks direct
  HTTPS to github.com.

**Push:**
```bash
gh auth setup-git 2>/dev/null || true
git push -u origin $(git branch --show-current)
```

5. Create or update PR
```bash
gh pr view --json number,body 2>/dev/null
```
- If no PR: `gh pr create --title "type(scope): desc" --body "## Summary\n- changes"`
- If PR exists:
  1. Read the existing PR description from the `body` field above
  2. Update the description to account for the changes just pushed (add new bullet points, revise summary, etc.) while preserving any content that is still accurate
  3. `gh pr edit --body "updated body"` to apply the updated description
  4. Report the PR URL

Read if present: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`.

## Moat

The `ssh:github.com` grant proxies your host machine's SSH agent into the
container — private keys never enter the container. A system-level git config
(`/tmp/.gitsystem-isolated`) rewrites all HTTPS GitHub URLs to SSH, so all git
transport goes through SSH.

**If SSH auth fails**: the SSH agent proxy has no keys. This means the host's
SSH agent wasn't running or didn't have GitHub keys loaded when Moat started.
There is no HTTPS fallback — the URL rewrite and network proxy make it
impossible. The only fix is to load keys on the host and restart the Moat run.
Do not attempt workarounds (switching remotes, unsetting config, API push).

The `gh auth setup-git` fallback covers non-Moat environments where HTTPS with
a credential helper is the standard path. All `gh` subcommands (`pr create`,
`pr view`, etc.) use the `github` grant's API access.