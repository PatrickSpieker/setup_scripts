---
name: pr-screenshots
description: Capture Playwright screenshots for each user journey in the current PR and embed them in the PR description.
---

# PR Screenshots

Drive the browser with the Playwright MCP tools, save one PNG per distinct UI state under `docs/screenshots/<slug>/`, commit them, and embed them in the PR description.

## When to use

- You've finished (or nearly finished) a branch with visible UI changes and want to give the reviewer a walkthrough without requiring them to boot the dev server.
- User explicitly asks to "add screenshots to the PR" or "show the reviewer the flow."

Do NOT use for tiny / non-UI changes (backend refactors, dependency bumps).

## Prerequisites

- The repo is a web app runnable locally (dev server exposes a URL Playwright can hit).
- The Playwright MCP is configured — tools named `mcp__playwright__browser_*` are available in this session. This repo's `moat.yaml` wires it up; on the host it's configured via `defaults/settings.json`. You do NOT need to `npm install playwright` or `npx playwright install` — the MCP server provisions its own Chromium (headful on host, headless in Moat).
- `gh` is authenticated and `gh pr view` succeeds for the current branch.
- App auth: if the app requires login, you must have credentials available via env vars or a fixture. Otherwise scope this skill to unauthenticated flows.

## Steps

### 1. Figure out what user journeys to capture

```bash
git fetch origin
BASE=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null || git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
git diff --name-only "$BASE"...HEAD
gh pr view --json title,body 2>/dev/null
```

Treat each of these as one journey:
- **New or heavily-modified page/route** → one journey per page.
- **Major new component used in a flow** → a journey through the flow that uses it.
- **New user-facing API route** → capture the UI that consumes it.
- If the PR description already names flows, use those verbatim.

List them back to the user in one short paragraph before capturing. Bail if nothing visual changed.

### 2. Discover the dev server command and URL

```bash
jq -r '.scripts | to_entries[] | "\(.key): \(.value)"' package.json 2>/dev/null
```

Look for a `dev`, `start`, `serve`, or similar script. Note the port it prints (default Vite: 5173, Next.js: 3000, Create React App: 3000). If the port is not obvious from the script, ask the user.

Pick a `SLUG` from the PR/branch name (kebab-case, descriptive, e.g. `checkout-redesign`). Screenshots land in `docs/screenshots/<SLUG>/`.

### 3. Start the dev server

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
SLUG="<chosen-slug>"
BASE_URL="http://localhost:<port>"

# Start dev server in background if not already running
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q 200 || \
  ( cd "$PROJECT_ROOT" && $DEV_CMD > /tmp/dev-server.log 2>&1 & )

# Wait for readiness
until curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q 200; do sleep 1; done

mkdir -p "$PROJECT_ROOT/docs/screenshots/$SLUG"
```

If the dev server needs isolated data (separate DB, clean state), pass that through env vars when starting it — don't point it at the user's real data dir.

### 4. Drive the browser with the Playwright MCP

Work one journey at a time. The core loop is: navigate → (interact) → screenshot. Use relative paths for `filename` — the MCP writes them under the working directory (`/workspace` in Moat), so `docs/screenshots/<slug>/NN-name.png` lands in the repo where you want it.

**Set the viewport once per session:**

```
mcp__playwright__browser_resize(width=1400, height=860)
```

**Navigate and snap:**

```
mcp__playwright__browser_navigate(url="http://localhost:5173/")
mcp__playwright__browser_take_screenshot(
  type="png",
  filename="docs/screenshots/<slug>/01-landing.png"
)
```

**Interact, then snap the resulting state.** To click or type on a specific element, first call `mcp__playwright__browser_snapshot` to get an accessibility tree with `ref` IDs, then pass the `ref` to the action tool:

```
mcp__playwright__browser_snapshot()
# → pick the ref for the element you want
mcp__playwright__browser_click(element="Sign in button", ref="<ref-from-snapshot>")
mcp__playwright__browser_take_screenshot(
  type="png",
  filename="docs/screenshots/<slug>/02-signed-in.png"
)
```

**Full-page screenshots** for layouts taller than the viewport:

```
mcp__playwright__browser_take_screenshot(type="png", fullPage=true, filename="...")
```

**Dialogs** (`window.confirm`, `window.prompt`): the MCP exposes `mcp__playwright__browser_handle_dialog` — call it after the dialog appears (the action that triggered it returns with a dialog-pending state).

**Seed realistic data** before snapping — empty states look stale. Use `mcp__playwright__browser_evaluate` to pre-populate localStorage, call seed endpoints via `curl` from Bash, or drive the UI to create the data.

**Rules:**
- **One numbered PNG per distinct state**, not per interaction. Snap the resulting panel/modal, not the click animation.
- **Viewport**: 1400×860. Larger produces huge PNGs; smaller may crop chrome.
- **Naming**: `NN-kebab-case.png` with two-digit prefix for sort order. Start each journey at its own prefix range (01-, 10-, 20-) so insertions in one journey don't renumber others.
- **Focus rings**: if a freshly-activated control shows a focus outline you don't want in the shot, click an empty area or press Escape via `mcp__playwright__browser_press_key` to blur it before snapping.
- **Close the browser** when done: `mcp__playwright__browser_close()`. Not strictly required (MCP cleans up on session end) but good hygiene if you plan to re-run.

### 5. Spot-check

Read 2–3 of the generated PNGs with the Read tool. Verify they show the intended state (not mid-transition, not hidden behind a modal). If any look wrong, re-navigate and re-capture. If total size is > 2 MB, trim or crop (see Pitfalls).

### 6. Commit the screenshots

```bash
git add docs/screenshots/<slug>/
git commit -m "docs: add PR screenshots for <feature>"
git push
SHA=$(git rev-parse HEAD)
```

Capture `$SHA` — you need it to pin the `<img>` URLs.

### 7. Update the PR description

Resolve owner/repo and pull the current body:

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PR=$(gh pr view --json number -q .number)
gh pr view "$PR" --json body -q .body > /tmp/pr-body.md
```

Append a `## Walkthrough` section with one `<img>` per screenshot, grouped by journey.

**URL form** (works for both public and private repos — renders via the viewer's auth cookie; raw.githubusercontent.com silently 404s for private repos from unauthenticated clients):

```html
<img src="https://github.com/<owner>/<repo>/blob/<SHA>/docs/screenshots/<slug>/NN-name.png?raw=true" alt="..." width="900" />
```

**Why pin to `<SHA>`**: screenshots are locked to a specific commit. Future pushes to the branch won't silently change what the PR description shows.

Structure:

```markdown
## Walkthrough

### Journey 1 — <name>
<img src=".../01-landing.png?raw=true" alt="Landing" width="900" />
<brief caption>

<img src=".../02-next-step.png?raw=true" alt="..." width="900" />
<brief caption>

### Journey 2 — <name>
...
```

Apply with `gh pr edit <PR> --body-file /tmp/pr-body-updated.md`.

### 8. Verify

Read the returned PR URL back to the user. Don't curl the image URLs — raw endpoints return 404 without auth; the reviewer sees them in-browser via their GitHub session.

## Pitfalls

- **Stale screenshots after further commits.** When the branch changes after the screenshots commit, the images are out of date relative to the code. Either regenerate (new commit, update PR URLs to the new SHA) or accept the drift — don't mix.
- **Huge PNGs balloon the repo.** Keep total under ~2 MB per PR. Use `fullPage=true` sparingly. If a single PNG is > 300 KB, crop the viewport instead.
- **MCP output path.** `filename` is resolved relative to the MCP server's working directory — in Moat that's `/workspace`, so `docs/screenshots/<slug>/...` lands in the repo. If you ever see PNGs appearing under `.playwright-mcp/` instead, pass an absolute path via `$PROJECT_ROOT`.
- **`.playwright-mcp/` is gitignored.** The MCP writes accessibility-tree YAML snapshots there as a side effect of navigation. Don't try to commit those — only the PNGs you explicitly saved go in the repo.
- **Modal dialogs hang the session.** If an action opens a `window.confirm`/`window.prompt`, the triggering tool call returns with a pending dialog. Resolve it with `mcp__playwright__browser_handle_dialog` before issuing more actions, or the next call will block.
- **Stale `ref` values.** The `ref` IDs from `mcp__playwright__browser_snapshot` are only valid for that snapshot. After any navigation or DOM change, re-snapshot before the next click.
- **GitHub image cache.** GitHub caches image URLs heavily; overwriting a PNG at the same path and pushing may still show the old image for minutes. Pin to a new SHA to force refresh.
- **Proxy / certificate errors inside Moat.** Chromium is launched via `scripts/playwright-mcp.sh`, which bridges Moat's authenticated HTTPS proxy and trusts the Moat CA. If navigation fails with `ERR_PROXY_AUTH_UNSUPPORTED` or a cert error, the launcher didn't run — check that `moat.yaml`'s `claude.mcp.playwright.command` points at `/tmp/setup-scripts/scripts/playwright-mcp.sh` and that `post_build` provisioned Chromium.
