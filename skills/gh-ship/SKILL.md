---
name: gh-ship
description: Commit, push, and create or update a pull request with consumer-visible interface changes, API contract diffs, required web or iOS walkthrough screenshots, and verification evidence. Use when shipping local changes to GitHub or updating an existing PR.
---

# Ship

Commit, push, and create or update a PR. Treat reviewer evidence as part of the change: infer changed surfaces from the diff, delegate required screenshots, describe API contract deltas, and use draft status when required evidence is incomplete.

## Hard rules

- Never push to `main` or `master`. If currently there, create a feature branch yourself before continuing; when the repo has no convention, use `codex/short-desc`.
- Never push onto a branch whose PR is merged or closed. Recover onto a fresh branch as described below.
- Never use `git add .` or `git add -A`. Stage explicit paths only.
- Never include unrelated working-tree changes.
- If there are no branch or working-tree diffs from the PR base, stop.
- Required screenshots and API descriptions gate **ready** status, not shipping. Incomplete evidence produces a draft PR with an explicit warning.
- Never automatically promote an existing draft PR to ready. Automatically downgrade a ready PR when required evidence becomes incomplete.

Read `AGENTS.md`, `CLAUDE.md`, and `CONTRIBUTING.md` when present.

## 1. Establish the branch and base

```bash
git branch --show-current
gh pr view --json state,number,url,baseRefName,body,isDraft 2>/dev/null || echo "NONE"
```

If on the default branch, create a feature branch before continuing. Choose a short kebab-case name from the requested work or current diff, prefer the repository's established branch prefix when obvious, and otherwise use `codex/<short-desc>`:

```bash
default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
cur=$(git branch --show-current)
if [ "$cur" = "$default_branch" ] || [ "$cur" = "main" ] || [ "$cur" = "master" ]; then
  new="codex/<short-desc>"
  git rev-parse --verify "$new" 2>/dev/null && new="${new}-$(date +%H%M%S)"
  git checkout -b "$new"
fi
```

If the current branch's PR is `MERGED` or `CLOSED`, do not add commits to it. Fetch the default branch, then create a fresh branch:

```bash
default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
git fetch origin "$default_branch:$default_branch" 2>/dev/null || git fetch origin "$default_branch"
cur=$(git branch --show-current)
new="${cur}-followup"
git rev-parse --verify "$new" 2>/dev/null && new="${new}-$(date +%H%M%S)"
git checkout -b "$new"
```

For independent work, stash only the intended paths, branch from `origin/$default_branch`, and restore them. Do not move unrelated changes.

Resolve the comparison base from the open PR when one exists, otherwise from the repository default:

```bash
BASE=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null || \
  gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
git fetch origin "$BASE"
```

## 2. Inspect and classify the complete change

Inspect both committed branch work and pending changes:

```bash
git status --porcelain
git diff --name-status "origin/$BASE"...HEAD
git diff --name-status
git diff "origin/$BASE"...HEAD
git diff
```

Classify behavior from the diff, not merely from repository contents or file extensions.

### UI surfaces

Require screenshots only for consumer-visible UI changes:

- **Web:** pages, routes, components, copy, styling, interactions, or responsive behavior rendered in a browser.
- **iOS:** SwiftUI/UIKit views, navigation, copy, styling, interactions, or adaptive layout rendered by an iOS app.
- **Both:** capture both when both surfaces changed.
- **Neither:** tests, docs, configuration, models, and internal refactors without a visible delta do not require screenshots.

Infer affected user journeys from the changed behavior. Do not ask repositories to declare path mappings or launch commands before attempting discovery.

### API surfaces

Treat a change as an API contract change when it alters an external or service-to-service boundary, including HTTP routes, RPC methods, GraphQL operations/schema, protobuf or message formats, exported SDK methods, request/response DTOs, authentication, status codes, or documented errors.

For every changed contract, determine:

- classification: `additive`, `behavioral`, `breaking`, or `removed`;
- native contract identifier, such as `PATCH /v1/orders/{id}` or `OrderService.Cancel`;
- **Before** contract;
- **After** contract;
- changed request, response, auth, status, error, or behavior semantics;
- evidence source: schema/spec, contract test, or implementation files.

Use schemas and contract tests first. When none exist, infer from routes, handlers, DTOs, and consumers, and label the evidence `inferred from implementation`. If the diff appears to alter a contract but the before/after contract cannot be reconstructed confidently, mark API evidence incomplete.

## 3. Capture required walkthroughs before committing

Choose a kebab-case PR slug from the branch or feature. Generated files live under:

```text
docs/screenshots/<pr-slug>/web/
docs/screenshots/<pr-slug>/ios/
```

For each changed UI surface, load and follow the corresponding skill in **capture mode**:

- Web: `/pr-screenshots` or `$pr-screenshots`.
- iOS: `/pr-screenshots-ios` or `$pr-screenshots-ios`.

Pass the resolved base, slug, changed journeys, and pending diff context. Capture the resulting branch only, never a before image. Use one representative environment by default:

- Web: desktop `1400x860`; add mobile/tablet only for responsive changes.
- iOS: newest available portrait iPhone simulator; add devices/orientations only for adaptive changes.

The delegated skill must remove obsolete PNGs only inside its platform directory, use isolated fixture/demo data or a fresh throwaway staging account, inspect every generated image, and return the captured paths grouped by journey or a precise blocker. If authentication or persisted server state is needed for a representative capture, create the staging account and test records yourself when the repository exposes a safe staging path; do not treat account creation as a reason to bail. Do not stage unsafe screenshots containing credentials, personal data, production records, or notifications. If representative evidence still cannot be produced safely, treat it as incomplete.

Do not abort when capture is blocked. Record the missing platform and blocker for the PR warning, then continue shipping as draft.

## 4. Stage and commit

Review the final status after capture. Stage only the intended source, tests, screenshot-tour files, and generated screenshots by explicit path:

```bash
git status --short
git add path/to/file1 path/to/file2 docs/screenshots/<pr-slug>/<platform>/
git commit -m "type(scope): short description"
```

Include initial screenshots and any screenshot-tour test in the same logical commit as the UI change. Use one commit unless the work contains clearly separate concerns. A later standalone screenshot refresh uses its own `docs: refresh PR screenshots` commit.

## 5. Push

Inside Moat, preflight SSH:

```bash
ssh -T git@github.com 2>&1
```

- `Hi <user>!` means proceed.
- `Permission denied (publickey)` means stop immediately and tell the user to run `ssh-add` on the host and restart the Moat run. Do not switch remotes, alter `insteadOf`, configure HTTPS credentials, or push through the API.

```bash
gh auth setup-git 2>/dev/null || true
git push -u origin "$(git branch --show-current)"
SHA=$(git rev-parse HEAD)
```

## 6. Compose the PR body

For a non-trivial change, use this hierarchy:

````markdown
## Interface Changes
<strictly consumer-visible behavior; no implementation detail>

### API Contract Changes
<include only when an API changed>

#### `PATCH /v1/orders/{id}` - breaking

**Before**
```http
PATCH /v1/orders/{id}
{ "status": "cancelled" }
-> 200 Order
```

**After**
```http
PATCH /v1/orders/{id}
{ "reason": string }
-> 202 Cancellation
```

Changed behavior: authentication unchanged; `409 conflict` added; processing is asynchronous.

Evidence: `openapi.yaml` and `tests/contracts/test_orders.py`.

### Walkthrough
<include only when web or iOS UI changed>

#### Web
##### <Journey>
<commit-pinned images and short captions>

#### iOS
##### <Journey>
<commit-pinned images and short captions>

## Implementation Changes
<non-obvious implementation choices; omit prose when the diff speaks for itself>

## Test Plan
<automated and manual verification>
````

`### API Contract Changes` and `### Walkthrough` are generated authoritatively from the complete current base-to-branch diff on every run. Replace stale generated content rather than appending fragments. Preserve hand-written Interface, Implementation, and Test content that remains accurate.

Use native notation and fenced-language identifiers appropriate to each API. List every contract change, not only breaking ones.

Build screenshot URLs from the final commit SHA so they work in public and private repositories:

```html
<img src="https://github.com/<owner>/<repo>/blob/<SHA>/docs/screenshots/<slug>/<platform>/NN-name.png?raw=true" alt="..." width="900" />
```

Use `width="320"` for portrait iOS screenshots. Keep screenshots grouped by platform and journey.

When evidence is incomplete, keep the relevant subsection and add:

```markdown
> [!WARNING]
> Evidence incomplete; this PR remains draft.
> - Missing: iOS walkthrough
> - Blocker: XcodeBuildMCP is unavailable in this environment
```

For a pure internal refactor, retain `## Interface Changes` and write `none - internal refactor`. Trivial changes may stay concise, but must not omit applicable contract or walkthrough evidence.

When tests were added or changed, include exact copyable commands. Give separate executable steps separate `bash` blocks.

When the PR changes a state machine, include Mermaid `flowchart LR` diagrams for both before and after. Follow `AGENTS.md`; do not use `stateDiagram-v2`.

## 7. Create or update the PR

Evidence is incomplete when any required platform walkthrough is blocked or any apparent API contract remains uncertain.

For a new PR:

```bash
# Complete evidence: create ready (the default).
gh pr create --title "type(scope): desc" --body-file /tmp/pr-body.md

# Incomplete evidence: create draft.
gh pr create --draft --title "type(scope): desc" --body-file /tmp/pr-body.md
```

For an existing open PR, update the description through REST:

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PR=$(gh pr view --json number -q .number)
gh api --method PATCH "repos/$OWNER_REPO/pulls/$PR" \
  -F body=@/tmp/pr-body.md --jq .html_url
```

If evidence is incomplete and the existing PR is ready, downgrade it:

```bash
gh pr ready --undo "$PR"
```

Never mark an existing draft ready automatically, even when all evidence is now complete; it may be draft for an unrelated reason.

Prefer the REST endpoint above for title/body/base edits. Use `gh pr edit` only for helpers such as labels, reviewers, assignees, milestones, or projects.

Report the PR URL, readiness state, captured screenshot counts by platform/journey, API contract count, and any unresolved evidence.

## Edge cases

- **Working tree has unrelated changes:** leave them unstaged and unmentioned in the commit.
- **No `origin`:** stop; push and PR creation require it.
- **Capture succeeds for one platform and fails for another:** embed the successful evidence, warn for the missing platform, and ship draft.
- **Existing screenshots are stale:** regenerate the applicable platform directory and update URLs to the new SHA.
- **Screenshot refresh after review:** invoke the platform screenshot skill independently; it owns a separate refresh commit and updates only its generated platform block.

## Moat

The `ssh:github.com` grant proxies the host SSH agent. A system Git config rewrites GitHub HTTPS URLs to SSH, so there is no HTTPS fallback. `gh` commands use the GitHub API grant.
