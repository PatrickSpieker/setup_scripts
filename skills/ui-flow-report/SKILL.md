---
name: ui-flow-report
description: Explore a web or native mobile app through real UI navigation and create a self-contained HTML screenshot graph of its states and interactions, with resumable capture and explicit unexplored branches.
---

# UI Flow Report

Create one top-to-bottom screenshot graph of all discoverable interactions. Branch horizontally, merge equivalent destinations, and loop return actions back to existing states. No workflow tabs. Use `scripts/report.py` to checkpoint and render; do not hand-build the HTML.

## Establish scope

Record app, platform, environment, current user role, device/viewport, theme, and optional workflow/time/state limits. **Production is the default; only an explicit staging request selects staging.** Do not infer staging from a hostname or debug build. Cover the current role/configuration unless asked for others.

Production may mutate verified test-account data. Mark effects outside that account—real charges, messages to real recipients, or other users' data—as `production restriction`. Classify unknown effects as external until inspected. Staging permits all interactions within the test environment; a staging UI connected to a real external service does not make that service a test environment. Test-account access does not authorize sending real messages.

Use available code to discover actions and conditional states, but every screenshot must come from actual navigation. Never fabricate a destination image. For Antaeus account discovery/setup, read [references/antaeus.md](references/antaeus.md). For browser or native navigation, read [references/drivers.md](references/drivers.md).

## Capture and explore

Read [references/checkpoints.md](references/checkpoints.md) for CLI commands and record shapes. Use a task-specific working directory (default `artifacts/ui-flow-report/<app>-<run>/`) with `graph.json`, `screenshots/`, and generated `report.html`. Keep credentials out of this directory. A checkpoint contains non-secret test values only; keep sensitive restoration values in an approved secret store or session memory.

1. Initialize the run or inspect its existing checkpoint. On resume, verify the same app, account, configuration, and build; re-navigate and compare the last state. Do not append incompatible evidence to a stale run. Reconcile every `in_flight` action by inspecting current UI/data before resolving it; never blindly retry.
2. Capture the current meaningful visible state. Include menus, modals, validation, and loading states when observed. Avoid every keystroke/hover unless it changes meaningful behavior. Record title, prerequisites, observations, navigation evidence, and an appearance-plus-behavior equivalence key. Reuse an existing state for equivalent repeated records. Visually identical states with different available actions/outcomes need different keys.
3. Inspect all visible controls, scrollable content, gestures, and code-discovered branches. Persist pending actions before following them. Label actions precisely (including non-secret input category where relevant). Source-only unreachable destinations remain unexplored, without invented screenshots. Record provenance (`ui` or `source` plus a non-secret locator).
4. For an action, save any practical restoration record, then call `begin` **before** performing it. Navigate with the selected UI driver, capture the destination, then `resolve` the action to its state ID. A control with no meaningful visual change is a self-loop if it is a meaningful interaction. Record conditional outcomes as distinct action records with their prerequisites.
5. Continue until the pending frontier is empty and inspection finds no new states; no arbitrary default cap. Deduplicate by appearance AND behavior, not screenshot bytes, URLs, or record IDs alone. A requested workflow limits exploration: mark known exits `outside requested workflow`, rather than silently dropping them. On limits or interruption, known pending branches render as `exploration limit`; uncertainty about undiscovered branches stays visible.
6. Restore owned test-account changes when practical, comparing current values/versions before restoring. Do not overwrite unrelated changes. Mark each change restored or left behind with an explanation. UI transitions must be captured through UI actions; setup/restoration APIs may arrange prerequisites but cannot stand in for observed transitions.
7. Finish with `exhausted` only after inspecting the whole discovered frontier; otherwise `stopped` and explain the interruption or blocker. The helper renders after every saved mutation, so a portable partial report is normally already available. An abrupt kill may require `render` on resume. An interrupted run is not complete just because its last screenshot exists.

## Deliver

Open the generated HTML and verify layout and screenshots. Check representative branches/loops, labels, search, fit/pan/zoom, details, and enlargement. Verify all images are genuine, legible, and free of credentials. Fix captures or omit them with an explicit explanation; do not silently edit UI evidence. Return the HTML link, coverage limits, unexplored reasons, and any test-data changes left behind. Only the HTML is needed for sharing; preserve the working directory for resumption.
