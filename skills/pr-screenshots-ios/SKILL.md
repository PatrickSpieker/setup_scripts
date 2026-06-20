---
name: pr-screenshots-ios
description: Capture and verify deterministic iOS Simulator screenshots for affected pull-request journeys through XcodeBuildMCP by defaulting to direct UI automation of the changed flows, then store them under a commit-pinned walkthrough or refresh the iOS walkthrough on an existing PR. Use directly when adding iOS PR screenshots or when gh-ship delegates a consumer-visible iOS change.
---

# iOS PR Screenshots

Capture deterministic screenshots for the current change on one representative iPhone simulator. Default to running the app and driving only the changed reviewer flows directly with XcodeBuildMCP UI actions. Reuse an existing focused XCUITest screenshot tour only when it already targets the same changed flow and is faster or more deterministic than direct UI automation. Store named PNGs under the PR screenshot directory and render a commit-pinned iOS block under `## Interface Changes` -> `### Walkthrough`.

Use XcodeBuildMCP for all Xcode, simulator, test, and UI-automation operations. Do not use the older Xcode MCP, raw `xcodebuild`, or raw `simctl`. The bundled extraction script may call `xcresulttool` and `sips` only to post-process the result bundle produced by XcodeBuildMCP; direct MCP capture may use `sips` only to normalize screenshots returned by XcodeBuildMCP.

Operate in one of two modes:

- **Capture mode:** called by `gh-ship` before the main commit. Run a direct MCP capture for the changed flows, or update an existing tour only when that is clearly more efficient, verify images, then return modified tour paths plus image metadata. Do not commit, push, or edit a PR.
- **Refresh mode:** called directly for an existing PR. Capture, commit, push, and replace the generated iOS walkthrough block while preserving Web and hand-written PR content.

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

Read the actual diff. Infer consumer-visible iOS journeys from changed views, navigation, presentation, copy, styling, interactions, and adaptive layout. Do not require repository path mappings. Tests, models, services, configuration, and internal refactors without a visual delta return `not required`.

Group the changed UI into reviewer journeys. Capture the resulting branch only, one image per materially changed stable state.

## 2. Establish XcodeBuildMCP context

XcodeBuildMCP is required. If it is unavailable or the necessary workflows cannot be exposed in the current session, return a blocker; `gh-ship` will ship a draft.

Follow the server's session contract:

1. Call `session_show_defaults` before any build, run, or test action.
2. If project/workspace context is missing or incorrect, call `discover_projs` from the repository root.
3. Prefer a workspace when it is the repository's established build entry point; otherwise use the project.
4. Call `list_schemes` and inspect build settings/repository instructions to select the app scheme. Do not guess when multiple plausible app schemes produce different products. Select a UI-test target only if you intentionally choose an existing screenshot tour for this capture.
5. Call `list_sims` and choose one available iPhone on the newest installed iOS runtime. Prefer a standard Pro-size phone when several exist. Use portrait orientation.
6. Set project/workspace, scheme, and simulator defaults with `session_set_defaults`, then report the selected context.

The required capabilities are project discovery, simulator management, app build/run, and UI automation (`build_run_sim`, `screenshot`, `snapshot_ui`, `tap`, `batch`, and any needed text/scroll/button actions). Simulator testing (`test_sim`) is optional and should be used only when an existing XCUITest tour is the chosen capture path. XcodeBuildMCP exposes tools by enabled workflow. If an expected tool is missing, inspect the enabled workflows. Do not silently switch to shell tools; report that XcodeBuildMCP must be configured/reloaded.

Use one simulator by default. Add another device or orientation only when the diff specifically changes adaptive UI, size-class behavior, iPad layout, or rotation.

## 3. Plan the targeted MCP capture

Plan the shortest direct MCP action sequence that reaches the changed UI states:

- Start from the actual diff and target only affected reviewer flows, not a broad product tour.
- Prefer direct interaction over editing test code. Do not create screenshot-tour tests solely for PR evidence.
- Use existing repository launch arguments, demo modes, preview fixtures, seed data, or safe staging setup when they make the direct flow deterministic.
- Use `snapshot_ui` before each action to find current `elementRef` targets.
- Use `tap` for one target, `batch` for multiple same-screen taps, and the available MCP text, scroll, gesture, or hardware-button tools when the journey needs them.
- Refresh `snapshot_ui` after navigation, scrolling, sheets, alerts, or layout changes before choosing the next target.
- Capture each stable state with `screenshot(returnFormat: "path")`, then copy or convert it into `docs/screenshots/$SLUG/ios/` using the same `NN-kebab-case.png` naming convention.
- Record the action sequence in the capture result so reviewers can understand how each image was reached, but do not add or modify test files solely for screenshots.

Search for an existing screenshot-tour XCUITest only after planning the direct path. Reuse or update it instead of direct MCP automation only when all of these are true:

- it already covers the changed flow or can be trivially narrowed to the changed flow;
- it provides deterministic setup that direct MCP capture cannot easily reproduce;
- updating it is less work than driving the changed flow directly;
- one focused `test_sim` call will produce only the screenshots needed for this PR.

When a tour is the chosen path, read the UI-test target's helpers, fixtures, launch configuration, page objects, and naming conventions, then update its journeys to match the complete current diff and remove stale captures. Reuse established test-app launch helpers, page objects, accessibility identifiers, and fixture builders.

The direct MCP journey or chosen tour must launch isolated fixture/demo data. Prefer launch arguments/environment and in-process fixtures over network setup, but when the changed journey genuinely requires authenticated staging state, create a fresh throwaway staging account and representative non-sensitive records through the repository's established safe setup path. Do not bail merely because no reusable account exists. Never use personal accounts, credentials, production records, notification content, or uncontrolled remote state.

When using XCUITest, use a helper equivalent to:

```swift
private func snap(_ app: XCUIApplication, name: String) {
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
}
```

Requirements:

- Name every attachment or direct screenshot `NN-kebab-case` with a two-digit prefix.
- Reserve number ranges per journey (`01-`, `10-`, `20-`).
- Capture after the expected view/state has an explicit readiness assertion.
- Force a deterministic appearance when appearance is not part of the change.
- Dismiss the keyboard and transient system UI before capture.
- Prefer `continueAfterFailure = false`; a failed tour must not yield apparently complete evidence.

For direct MCP capture, the same requirements apply to output file names and visible states. Treat `snapshot_ui` observations and visible UI state as the readiness assertion before each `screenshot`.

## 4. Capture through XcodeBuildMCP

Use the direct MCP action sequence from section 3 by default:

1. Run the app with `build_run_sim`.
2. Drive each step through `snapshot_ui` plus `tap`, `batch`, and other available UI automation tools.
3. Use `screenshot(returnFormat: "path")` only after the expected state is visible and stable.
4. If a step fails, inspect the latest `snapshot_ui` and screenshot, adjust the action sequence, and retry once the cause is understood.
5. If the journey still cannot be captured reliably, return incomplete evidence with the exact failing step.

When an existing tour is explicitly chosen, run only the screenshot tour with `test_sim`, using the active session defaults and the tool's current test-filter field. Do not run an entire test matrix merely to capture screenshots.

On tour failure:

1. Read the test/build diagnostics returned by XcodeBuildMCP.
2. Use `snapshot_ui` and `screenshot` when needed to diagnose the visible state.
3. Fix deterministic tour/setup failures and retry once they are understood.
4. If the journey requires authenticated staging state, create or repair a fresh throwaway staging account through the repository's established safe setup path before declaring authentication blocked.
5. If the journey still cannot be captured reliably, return incomplete evidence with the exact failing step. Do not extract screenshots from a failed tour as if they were complete.

Record the `.xcresult` path returned or reported by `test_sim` only for tour captures. If the tool does not return one directly, locate the result bundle produced by that specific run without selecting an older ambiguous bundle.

## 5. Extract into scoped output

For direct MCP captures, create `OUT="$PROJECT_ROOT/docs/screenshots/$SLUG/ios"`, remove obsolete PNGs only from that exact directory, and copy each `screenshot(returnFormat: "path")` result into `OUT` with its planned `NN-kebab-case.png` name. Use the same max-dimension target as the extractor when conversion is needed. Reject missing files, duplicate names, empty captures, and obviously stale screenshots.

For tour captures, resolve this skill's bundled script and run:

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel)
OUT="$PROJECT_ROOT/docs/screenshots/$SLUG/ios"
<skill-dir>/scripts/extract-attachments.py \
  <result-bundle.xcresult> "$OUT" --clean --max-dim 1000
```

`--clean` removes obsolete PNGs only from this exact iOS platform directory. The script rejects missing bundles, invalid attachment names, duplicate names, empty captures, and post-processing failures.

Never clean another PR slug, the Web directory, or manually managed paths.

## 6. Verify every image

Open every generated PNG. Confirm that each image:

- shows the intended stable state and journey;
- contains no credentials, personal information, production records, notifications, or unrelated simulator content;
- has no keyboard, system sheet, loading overlay, or stale fixture state unless that state is the subject of the change;
- is legible and correctly oriented.

Use XcodeBuildMCP `snapshot_ui` and `screenshot` for diagnosis when an image is suspicious. Prefer fixing fixtures, throwaway staging setup, timing, or the direct action sequence and rerunning the capture over editing the image. If redaction is unavoidable, disclose it in the caption. If a safe representative image cannot be produced after using available fixture or staging-account setup, return incomplete evidence.

Keep a typical iOS screenshot set below roughly 3 MB. Remove redundant images before lowering quality; the extractor and direct normalization already limit the longest dimension.

Stop the launched app with XcodeBuildMCP when finished. Do not erase or shut down a simulator that may be shared with the user.

## 7. Return capture results

In capture mode, return:

- status: `complete`, `not required`, or `blocked`;
- modified screenshot-tour file paths only when a tour was intentionally reused; otherwise `none`;
- image paths grouped by journey;
- a short caption and alt text for every image;
- selected project/workspace, scheme, optional test target, simulator, runtime, and whether capture used direct MCP actions or `test_sim`;
- direct MCP action sequence, or reason an existing tour was more efficient;
- blocker when incomplete.

Do not stage or commit in capture mode. `gh-ship` owns the main commit.

## 8. Render the iOS walkthrough

After the caller supplies the final commit SHA, render only the iOS platform block:

```markdown
#### iOS

##### <Journey>
<img src="https://github.com/<owner>/<repo>/blob/<SHA>/docs/screenshots/<slug>/ios/01-state.png?raw=true" alt="..." width="320" />

<brief caption>
```

Place it under `## Interface Changes` -> `### Walkthrough`. Pin every URL to the commit SHA. Preserve the Web block when refreshing iOS independently.

For blocked evidence, render:

```markdown
#### iOS

> [!WARNING]
> Evidence incomplete; this PR remains draft.
> - Missing: iOS walkthrough
> - Blocker: <specific blocker>
```

## 9. Standalone refresh mode

Require an open PR. If the PR is merged or closed, recover to a new branch rather than committing stranded screenshots.

After successful capture, stage the generated iOS directory and only the tour files changed for this refresh. Omit the tour path for the default direct MCP capture path:

```bash
git add "docs/screenshots/$SLUG/ios/" [path/to/ScreenshotTourTests.swift]
git commit -m "docs: refresh PR screenshots"
git push
SHA=$(git rev-parse HEAD)
```

Replace the existing generated iOS block from the complete current diff; do not append a second walkthrough. Preserve Web and accurate hand-written content. Update through REST:

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PR=$(gh pr view --json number -q .number)
gh api --method PATCH "repos/$OWNER_REPO/pulls/$PR" \
  -F body=@/tmp/pr-body-updated.md --jq .html_url
```

If capture is blocked, update the iOS block with the warning and downgrade a ready PR with `gh pr ready --undo "$PR"`. Never promote an existing draft automatically.

Report the PR URL, selected simulator context, and screenshot count by journey.

## Common failures

- Call `session_show_defaults` first; stale defaults can build the wrong scheme or simulator.
- XcodeBuildMCP tools are workflow-scoped. Missing UI/test tools require configuration and session reload, not a raw shell fallback.
- Do not hard-code a device model or iOS version; choose from `list_sims`.
- Default to direct MCP UI actions targeted to the changed flow; do not search for or maintain a broad tour before trying the efficient direct path.
- When a tour is intentionally reused, ensure the tour file belongs to the UI-test target before diagnosing a missing test.
- Do not create a tour just for screenshots; drive the app with MCP UI actions and save direct screenshots.
- Keep attachment and direct screenshot names to `NN-kebab-case`; the extractor and walkthrough intentionally reject other names.
- Pin URLs to the screenshot commit SHA so later pushes do not silently change review evidence.
