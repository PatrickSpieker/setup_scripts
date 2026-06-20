---
name: pr-screenshots
description: Capture and verify web UI screenshots for affected pull-request journeys with Playwright, store them under a commit-pinned walkthrough, or refresh the web walkthrough on an existing PR. Use directly when adding web PR screenshots or when gh-ship delegates a consumer-visible web change.
---

# Web PR Screenshots

Capture one PNG per materially changed web UI state, using safe representative data, and render a commit-pinned Web block under `## Interface Changes` -> `### Walkthrough`.

Operate in one of two modes:

- **Capture mode:** called by `gh-ship` before the main commit. Write and verify images, then return their paths and journeys. Do not commit, push, or edit a PR.
- **Refresh mode:** called directly for an existing PR. Capture, commit, push, and replace the generated Web walkthrough block while preserving other platforms and hand-written PR content.

Read `AGENTS.md`, `CLAUDE.md`, and `CONTRIBUTING.md` when present.

## 1. Establish scope

Accept `BASE` and `SLUG` from `gh-ship` when provided. Otherwise derive them:

```bash
git fetch origin
BASE=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null || \
  gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
SLUG=$(git branch --show-current | sed 's@.*/@@; s/[^a-zA-Z0-9-]/-/g' | tr '[:upper:]' '[:lower:]')
git diff --name-status "origin/$BASE"...HEAD
git diff --name-status
```

Infer journeys from behavior in the full diff:

- New or heavily changed page/route: one journey per page.
- Changed component: capture the flow and state in which a reviewer sees it.
- API-backed UI: capture the consuming UI with realistic fixture data.
- Copy, validation, modal, loading, error, and success changes: capture each materially changed visible state.

If no consumer-visible web UI changed, return `not required`. Do not capture merely because the repository contains a web app.

## 2. Discover and start the app

Inspect package-manager files, workspace configuration, scripts, and contributor instructions. Prefer the repository's established dev or preview command. Do not install a second browser automation stack; use the configured Playwright MCP/browser tools.

Determine the local URL from configuration or server output. Start the app with isolated fixture/demo data. Never point screenshot setup at production data or the user's personal data directory.

If the app cannot start, authentication cannot be satisfied safely, Playwright is unavailable, or a required journey cannot be reached, return a precise blocker. In refresh mode, continue to the draft handling step rather than silently retaining stale evidence.

## 3. Prepare scoped output

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel)
OUT="$PROJECT_ROOT/docs/screenshots/$SLUG/web"
mkdir -p "$OUT"
find "$OUT" -maxdepth 1 -type f -name '*.png' -delete
```

Delete obsolete files only from this exact generated platform directory. Never clean another PR slug, the iOS directory, or manually managed screenshot paths.

## 4. Capture with Playwright

Set the default viewport once:

```text
browser_resize(width=1400, height=860)
```

Add mobile/tablet viewports only when the diff changes responsive or breakpoint-specific behavior.

For each journey:

1. Navigate to the starting route.
2. Seed or create representative non-sensitive data.
3. Use the accessibility snapshot to locate controls.
4. Interact until the materially changed state is stable.
5. Capture `docs/screenshots/<slug>/web/NN-kebab-case.png`.

Use two-digit ranges per journey (`01-`, `10-`, `20-`) so later insertions do not renumber unrelated journeys. Capture states, not click animations. Use full-page screenshots only when the changed layout requires it. Close the browser when done.

## 5. Verify every image

Open every generated PNG. Confirm that each image:

- shows the intended stable state;
- contains no credentials, personal information, production records, notifications, or unrelated browser content;
- has no blocking dialogs, keyboards, focus artifacts, or stale data;
- is legible at review size.

Prefer recapturing with safe fixtures over editing the image. If redaction is unavoidable, disclose it in the caption. If a safe representative image cannot be produced, return incomplete evidence with the blocker.

Keep the generated set reasonably small; remove redundant states and compress oversized images using the repository's existing tooling.

## 6. Return capture results

In capture mode, return:

- status: `complete`, `not required`, or `blocked`;
- paths grouped by journey;
- a short caption and alt text for every image;
- viewport(s) used;
- blocker when incomplete.

Do not stage or commit in capture mode. `gh-ship` owns the main commit.

## 7. Render the Web walkthrough

After the caller supplies the final commit SHA, render only the Web platform block:

```markdown
#### Web

##### <Journey>
<img src="https://github.com/<owner>/<repo>/blob/<SHA>/docs/screenshots/<slug>/web/01-state.png?raw=true" alt="..." width="900" />

<brief caption>
```

Place it under `## Interface Changes` -> `### Walkthrough`. Pin every URL to the commit SHA. Preserve the iOS block when refreshing Web independently.

For blocked evidence, render:

```markdown
#### Web

> [!WARNING]
> Evidence incomplete; this PR remains draft.
> - Missing: web walkthrough
> - Blocker: <specific blocker>
```

## 8. Standalone refresh mode

Require an open PR. If the PR is merged or closed, recover to a new branch rather than committing stranded screenshots.

After successful capture:

```bash
git add "docs/screenshots/$SLUG/web/"
git commit -m "docs: refresh PR screenshots"
git push
SHA=$(git rev-parse HEAD)
```

Replace the existing generated Web block from the complete current diff; do not append a second walkthrough. Preserve the iOS block and accurate hand-written content. Update the body through the REST endpoint:

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PR=$(gh pr view --json number -q .number)
gh api --method PATCH "repos/$OWNER_REPO/pulls/$PR" \
  -F body=@/tmp/pr-body-updated.md --jq .html_url
```

If capture is blocked, update the Web block with the warning and downgrade a ready PR with `gh pr ready --undo "$PR"`. Never promote an existing draft automatically.

Report the PR URL and screenshot count by journey.

## Antaeus web app

The `antaeus-web-app` repository uses Vite at `http://localhost:5173`. Authenticated routes require the staging Firebase client configuration below in a repository-root `.env`; these are public client identifiers, not server credentials:

```env
VITE_FIREBASE_API_KEY=AIzaSyCvv3DLb3Biw60q0sN1c2rLMLQJ9hh4fKk
VITE_FIREBASE_AUTH_DOMAIN=antaeus-staging-1.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=antaeus-staging-1
```

Create a fresh throwaway staging account for each capture run. Do not reuse production accounts. Clean up created posts, grants, and invites through the API afterward; note any Firebase user that the client cannot delete.

For Epic-linked fixtures, follow the repository-local QA skill rather than copying credentials into this global skill. Sharing-only flows do not require an Epic link.

## Common failures

- Re-snapshot after navigation or DOM changes; stale accessibility refs are invalid.
- Resolve browser dialogs before the next action.
- Verify where the Playwright server writes relative paths; use the absolute `$OUT` path when uncertain.
- Regenerate URLs with the latest screenshot commit SHA to bypass GitHub's image cache.
- If the browser cannot reach localhost or reports proxy/certificate failures inside Moat, verify that the repository's Playwright MCP uses the shared `scripts/playwright-mcp.sh` launcher. Report the launcher/configuration blocker; do not install an ad hoc browser.
