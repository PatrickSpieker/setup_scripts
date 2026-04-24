---
name: pr-screenshots
description: Capture Playwright screenshots for each user journey in the current PR and embed them in the PR description.
---

# PR Screenshots

Capture screenshots for each relevant user journey affected by the current branch's changes, commit them under `docs/screenshots/<slug>/`, and embed them in the PR description. Screenshots are taken with the **Playwright MCP server** (`mcp__playwright__browser_*` tools) — no throwaway Node scripts.

## When to use

- You've finished (or nearly finished) a branch with visible UI changes and want to give the reviewer a walkthrough without making them boot the dev server.
- User explicitly asks to "add screenshots to the PR" or "show the reviewer the flow."

Do NOT use for tiny / non-UI changes (backend refactors, dependency bumps).

## Prerequisites

- **Playwright MCP is wired up.** On the host this lives under `mcpServers.playwright` in `~/.claude/settings.json` (headful, `--isolated`). Inside a Moat container it's declared under `claude.mcp.playwright` in `moat.yaml` and launched via `scripts/playwright-mcp.sh --headless --isolated --no-sandbox`. The `--isolated` flag means each run gets a throwaway profile.
- **Repo has a web app runnable locally** (dev server exposes a URL). No UI → skip this skill.
- `gh` is authenticated and `gh pr view` succeeds for the current branch.
- **Auth**: if the app requires login and you don't have credentials available (env vars, fixtures, or a saved storage state), scope this run to unauthenticated flows.
- **Moat only**: `post_build_root: npx -y playwright@latest install-deps chromium` must have run so the browser's system libs are present. If `browser_navigate` returns `libglib-2.0.so.0: cannot open shared object file`, that hook is missing — fix `moat.yaml` and `moat claude --rebuild`.

## Steps

### 1. Figure out which journeys to capture

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

List them back to the user in one short paragraph before generating. Bail if nothing visual changed.

### 2. Boot the dev server

Find the dev command:

```bash
jq -r '.scripts | to_entries[] | "\(.key): \(.value)"' package.json 2>/dev/null
```

Look for `dev`, `start`, `serve`, etc. Note the port it prints (Vite: 5173, Next.js: 3000, CRA: 3000). If unclear, ask.

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
BASE_URL="http://localhost:<port>"

# Start dev server in background if not already up
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q 200 || \
  ( cd "$PROJECT_ROOT" && $DEV_CMD > /tmp/dev-server.log 2>&1 & )

# Wait for readiness
until curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q 200; do sleep 1; done
```

If the dev server needs isolated state (separate DB, fixtures), pass that through env vars when starting it — don't point at the user's real data dir.

### 3. Pick a slug and create the output dir

Kebab-case, descriptive (e.g. `checkout-redesign`). Screenshots land in `docs/screenshots/<slug>/`.

```bash
SLUG="<chosen-slug>"
mkdir -p "$PROJECT_ROOT/docs/screenshots/$SLUG"
```

### 4. Capture screenshots via the MCP

The MCP browser is a persistent session. Call the tools in sequence. The key tools:

- `mcp__playwright__browser_resize` — set the viewport. **Do this first** (1400×860 recommended).
- `mcp__playwright__browser_navigate` — go to a URL.
- `mcp__playwright__browser_wait_for` — wait for text to appear/disappear, or a fixed delay.
- `mcp__playwright__browser_snapshot` — accessibility tree (returns `ref` handles for clicks/fills).
- `mcp__playwright__browser_click` / `_type` / `_fill_form` / `_select_option` / `_press_key` / `_hover` — drive the flow.
- `mcp__playwright__browser_evaluate` — run arbitrary JS in the page (seed data, read state).
- `mcp__playwright__browser_take_screenshot` — capture.
- `mcp__playwright__browser_close` — tear down when done.

**Where screenshots land.** `browser_take_screenshot` writes into the MCP's output directory (`.playwright-mcp/` at repo root, gitignored). The `filename` parameter is relative to that dir. After each screenshot, **move the PNG into `docs/screenshots/<slug>/`** with `mv` before the next call — keeping them in the gitignored dir means they'd never be committed.

Example sequence for one journey:

```
1. browser_resize(width=1400, height=860)
2. browser_navigate(url="http://localhost:5173/")
3. browser_wait_for(text="Welcome")         # or time=0.2 to let animations settle
4. browser_take_screenshot(filename="01-landing.png", type="png")
5. bash: mv .playwright-mcp/01-landing.png docs/screenshots/<slug>/
6. browser_snapshot()                       # get refs for the next click
7. browser_click(element="Sign in button", ref="<ref-from-snapshot>")
8. browser_wait_for(text="Password")
9. browser_take_screenshot(filename="02-login.png", type="png")
10. bash: mv .playwright-mcp/02-login.png docs/screenshots/<slug>/
...
11. browser_close()
```

**Rules:**

- **One numbered PNG per distinct state**, not per interaction. If a click opens a panel, snapshot the open panel — not the click animation frame.
- **Seed realistic data** via `browser_evaluate` or by driving the UI before snapping. Empty states look stale.
- **Viewport 1400×860**, default pixel ratio. Bigger → huge PNGs; smaller → may crop chrome.
- **`fullPage: true`** only for layouts that don't fit the viewport. A single fullPage PNG can easily be >500 KB.
- **Animations**: use `browser_wait_for(time=0.2)` to settle CSS transitions; bump for slower fades.
- **Naming**: `NN-kebab-case.png` with two-digit prefix for sort order. Start each journey at its own prefix range (01-, 10-, 20-) so inserting a step in journey 1 doesn't renumber journey 2.
- **Dialogs** (`window.confirm` / `prompt`): before the triggering click, pre-register the handler:
  ```
  mcp__playwright__browser_handle_dialog(accept=true, promptText="<value-if-needed>")
  ```
  (The MCP auto-consumes the *next* dialog — register it, then click.)

### 5. Spot-check

Read 2–3 of the moved PNGs with the Read tool. Verify they show the intended state (not mid-transition, not hidden behind a modal). If any look wrong, adjust and re-run. If total size is > 2 MB, trim or crop.

### 6. Commit the screenshots

```bash
git add docs/screenshots/<slug>/
git commit -m "docs: add PR screenshots for <feature>"
git push
SHA=$(git rev-parse HEAD)
```

Capture `$SHA` — you need it to pin the `<img>` URLs so future pushes don't silently change what the PR description shows.

### 7. Update the PR description

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PR=$(gh pr view --json number -q .number)
gh pr view "$PR" --json body -q .body > /tmp/pr-body.md
```

Append a `## Walkthrough` section with one `<img>` per screenshot, grouped by journey.

**URL form** (works for both public and private repos — renders via the viewer's auth cookie; `raw.githubusercontent.com` silently 404s for private repos from unauthenticated clients):

```html
<img src="https://github.com/<owner>/<repo>/blob/<SHA>/docs/screenshots/<slug>/NN-name.png?raw=true" alt="..." width="900" />
```

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

Read the returned PR URL back to the user. Don't `curl` the image URLs — raw endpoints return 404 without auth; the reviewer sees them in-browser via their GitHub session.

## Pitfalls

- **MCP output dir**. `browser_take_screenshot` writes into `.playwright-mcp/` (gitignored). If you forget to move the PNGs to `docs/screenshots/<slug>/`, the commit will be empty. Move after every screenshot, not at the end.
- **Chromium deps in Moat**. If `browser_navigate` fails with `libglib-2.0.so.0: cannot open shared object file`, the image is missing Playwright's system libs. Fix: add `post_build_root: npx -y playwright@latest install-deps chromium` in `moat.yaml`, then `moat claude --rebuild`.
- **Stale screenshots after further commits.** When the branch changes after the screenshots commit, the images are out of date relative to the code. Regenerate (new commit, update PR URLs to the new SHA) or accept drift — don't mix.
- **Huge PNGs balloon the repo.** Keep total under ~2 MB per PR. Use `fullPage: true` sparingly. If a single PNG is > 300 KB, crop the viewport instead.
- **Modal dialogs swallow clicks.** `browser_handle_dialog` must be registered BEFORE the click that triggers the dialog.
- **Auto-focus rings look noisy.** If a freshly-activated control shows a focus outline you don't want in the shot, click `body` or press `Escape` to blur it before snapping.
- **GitHub image cache.** GitHub caches image URLs heavily; overwriting a PNG at the same path and pushing may still show the old image for minutes. Pinning to a new SHA forces refresh.
- **MCP session is persistent.** The browser stays open between tool calls. If a previous skill run left the page somewhere odd, `browser_navigate` to a fresh URL or `browser_close` before starting.
