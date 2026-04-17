---
name: pr-screenshots
description: Capture Playwright screenshots for each user journey in the current PR and embed them in the PR description.
---

# PR Screenshots

Capture Playwright screenshots for each relevant user journey affected by the current branch's changes, commit them under `docs/screenshots/<slug>/`, and embed them in the PR description.

## When to use

- You've finished (or nearly finished) a branch with visible UI changes and want to give the reviewer a walkthrough without requiring them to boot the dev server.
- User explicitly asks to "add screenshots to the PR" or "show the reviewer the flow."

Do NOT use for tiny / non-UI changes (backend refactors, dependency bumps).

## Prerequisites

- The repo is a web app runnable locally (dev server exposes a URL Playwright can hit).
- `@playwright/test` or `playwright` is installed (check `package.json`). If not, install it (`pnpm add -D playwright` or equivalent) and ensure a browser is provisioned (`npx playwright install chromium`).
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

List them back to the user in one short paragraph before generating. Bail if nothing visual changed.

### 2. Discover the dev server command and URL

```bash
jq -r '.scripts | to_entries[] | "\(.key): \(.value)"' package.json 2>/dev/null
```

Look for a `dev`, `start`, `serve`, or similar script. Note the port it prints (default Vite: 5173, Next.js: 3000, Create React App: 3000). If the port is not obvious from the script, ask the user.

Set two variables used below:
- `DEV_CMD` — e.g. `pnpm dev`, `npm run dev`, `yarn dev`
- `BASE_URL` — e.g. `http://localhost:5173`

### 3. Draft a screenshot script

Write to `/tmp/pr-screenshots-<timestamp>.mjs` (throwaway, not in repo — only the PNGs get committed).

Pick a slug from the PR/branch name (kebab-case, descriptive, e.g. `checkout-redesign`). The output dir is `docs/screenshots/<slug>/` under the repo root.

Script skeleton:

```javascript
// Resolve playwright through the project's node_modules regardless of
// package manager (npm/yarn/pnpm). PROJECT_ROOT is set by the caller.
import { createRequire } from "node:module";
const require = createRequire(`${process.env.PROJECT_ROOT}/package.json`);
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://localhost:5173";
const OUT = `${process.env.PROJECT_ROOT}/docs/screenshots/${process.env.SLUG}`;

async function shot(page, name, { fullPage = false, settle = 150 } = {}) {
  if (settle) await page.waitForTimeout(settle);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage });
  console.log(`  saved ${name}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 860 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => console.error("PAGE ERROR:", e.message));

  // Seed any realistic data the flow needs here (API calls, fixture loading,
  // auth, etc.). Empty states look stale — populate enough for the journey
  // to read as real.

  // JOURNEY 1 ------------------------------------------------
  await page.goto(BASE);
  await shot(page, "01-landing");
  // Each meaningful state becomes one numbered PNG: 02-..., 03-...

  // JOURNEY 2 ------------------------------------------------
  // Start this journey at a higher prefix (10-, 20-) so insertions in one
  // journey don't renumber others.

  await browser.close();
  console.log("DONE");
}

main().catch((e) => { console.error(e); process.exit(1); });
```

**Rules for the script:**
- **One numbered PNG per distinct state**, not per interaction. If clicking a button opens a panel, snapshot the open panel — not the click animation frame.
- **Seed realistic data.** Empty states look stale. Use API calls, fixtures, or UI actions to populate the app before snapping.
- **Viewport**: 1400×860. Default pixel ratio. Larger viewports produce huge PNGs; smaller may crop chrome.
- **Use `fullPage: true`** only for layouts that don't fit the viewport.
- **Animations mid-flight**: the `settle` delay in `shot()` (default 150ms) catches most CSS transitions. Bump it for slower fades.
- **Naming**: `NN-kebab-case.png` with two-digit prefix for sort order. Start each journey at its own prefix range (01-, 10-, 20-).
- **Headless dialogs**: if a flow triggers `window.confirm` / `window.prompt`, register the handler BEFORE the triggering click:
  ```javascript
  page.once("dialog", (d) => d.accept("value"));
  await page.getByRole("button", { name: "Delete" }).click();
  ```

### 4. Ensure dev server is up, then run

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
PROJECT_ROOT="$PROJECT_ROOT" BASE_URL="$BASE_URL" SLUG="$SLUG" \
  node /tmp/pr-screenshots-<ts>.mjs
```

If the dev server needs isolated data (separate DB, clean state), pass that through env vars when starting it — don't point it at the user's real data dir.

### 5. Spot-check

Read 2–3 of the generated PNGs with the Read tool. Verify they show the intended state (not mid-transition, not hidden behind a modal). If any look wrong, adjust the script and re-run. If total size is > 2 MB, trim or crop (see Pitfalls).

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
- **Huge PNGs balloon the repo.** Keep total under ~2 MB per PR. Use `fullPage: true` sparingly. If a single PNG is > 300 KB, crop the viewport instead.
- **Modal dialogs swallow clicks.** `page.once("dialog", …)` must be registered BEFORE the click that triggers the dialog. Registering after → hangs forever.
- **Auto-focus rings look noisy.** If a freshly-activated control shows a focus outline you don't want in the shot, `await page.locator("body").click()` (or press `Escape`) to blur it before snapping.
- **GitHub image cache.** GitHub caches image URLs heavily; overwriting a PNG at the same path and pushing may still show the old image for minutes. Pin to a new SHA to force refresh.
- **Playwright resolution fails from `/tmp/`.** If `createRequire` can't find `playwright`, confirm `PROJECT_ROOT` is set and that `<PROJECT_ROOT>/node_modules/playwright` exists. For pnpm repos where only `.pnpm/` is populated, run `pnpm install` to ensure the top-level symlink exists.
