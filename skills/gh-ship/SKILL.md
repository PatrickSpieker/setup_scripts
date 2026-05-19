---
name: gh-ship
description: Commit, push, and create PR in one step.
---

# Ship

Commit, push, and create PR in one step.

## Hard rules

- **Never push to main/master.** Always ship from a feature branch. If on main/master at start, stop and ask the user to branch.
- **Never `git add .` or `git add -A`.** Stage specific paths only — guards against committing secrets or unrelated work.
- **One commit unless changes are clearly separate concerns.** Same discipline as `/gh-commit`.
- **If there are no diffs, stop.** Don't invent work to ship.

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
- If no PR: compose the body per **PR body** below, then:
  ```bash
  gh pr create --title "type(scope): desc" --body-file - <<'EOF'
  <body>
  EOF
  ```
- If PR exists:
  1. Read the existing PR description from the `body` field above
  2. Update it to account for the new commits — same **PR body** mental model — preserving anything still accurate
  3. `gh pr edit --body-file -` to apply
  4. Report the PR URL

Read if present: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`.

## PR body

Answer three things:

- **Interface Changes** — strictly the consumer side: the change as a consumer sees it. For a service that's the API surface (new route, changed response shape); for an end-user app it's the UI / behaviour delta; for a CLI it's the new flag or output. Nothing about implementation. **May be empty for pure internal refactors** — keep the section header for structural consistency and write `none — internal refactor` (or equivalent) as the body.
- **Implementation Changes** — non-obvious implementation choices, design notes, alternatives considered and discarded, optional follow-ups. Skip when the diff speaks for itself.
- **Test Plan** — tests added (unit, integration), manual smoke checks, what a reviewer should look at to confirm the change is correct. **When the PR adds or updates automated tests, include a fenced `bash` code block with the exact command(s) to run them** so a reviewer (or CI) can copy-paste. **If the test plan needs multiple executable steps, give each its own fenced block** — one copy-button click per step, no manual splitting required. Skip blocks entirely when there's nothing automated to run (e.g., docs-only changes, manual-smoke-only).

Use these as content prompts, not a mandatory template. A one-line PR ("typo fix in README") doesn't need three sections. A non-trivial change does:

````markdown
## Interface Changes
<consumer-visible change — no implementation detail; for pure refactors: `none — internal refactor`>

## Implementation Changes
<non-obvious implementation note — omit the section if the diff speaks for itself>

## Test Plan
<one-line summary: what tests were added / what was smoke-checked>

```bash
# step 1 — lint
./test_runner.sh lint
```

```bash
# step 2 — tests
./test_runner.sh test
```
````

## Edge cases

- **Working tree has unrelated changes:** stage only the paths you intend to ship.
- **PR already exists for the branch:** update its description with the new commits' context (step 5); don't open a duplicate.
- **No `origin` remote:** stop — `git push` and `gh pr create` both require it.

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