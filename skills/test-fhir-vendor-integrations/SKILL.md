---
name: test-fhir-vendor-integrations
description: Discover and manually test every FHIR/EHR patient-access vendor integration in a repository, capture reproducible UI, API, log, and configuration evidence, update the integration test manual, and ship the results in a draft pull request. Use when asked to test, audit, retest, or document all vendor sandbox or staging integrations, or to run the production login-page smoke test. Default to staging; use production only when explicitly requested.
---

# Test FHIR Vendor Integrations

Run the complete vendor-integration test workflow. Rediscover vendors from code on every run; do not rely on a fixed list.

Read [references/evidence-contract.md](references/evidence-contract.md) before testing.

## Fixed contract

- Default to staging.
- Use production only when the user explicitly requests it.
- Never create, update, or comment on Linear tickets.
- Test every discovered vendor. Do not silently omit integrations.
- Capture all five evidence types for every vendor.
- Update repository artifacts, commit, push, and open or update a draft PR.

## 1. Inspect the repository

1. Read repository instructions and inspect the worktree before changing anything.
2. Find the existing integration manual and evidence directories; preserve their paths and conventions.
3. Discover vendors from implementation sources such as:
   - vendor/profile registries and enums;
   - endpoint loaders and static endpoint definitions;
   - OAuth start/callback routing;
   - frontend picker mappings;
   - environment templates and deployment configuration;
   - integration tests.
4. Query the target environment's endpoint API and picker during an actual run.
5. Build the inventory from the union of:
   - vendors with an executable integration path in code; and
   - vendors exposed by the target environment's endpoint API or picker.
6. Include a runtime-exposed vendor even when the checked-out registry lacks a profile, and record that deployment/code drift. Do not include an enum-only or vocabulary-only name unless code or the target environment exposes a usable integration path.
7. Save the discovered inventory as JSON using the schema in the evidence contract.

Do not use an earlier report, hard-coded checklist, or a single registry as the inventory source of truth.

## 2. Build the test matrix

For each vendor, determine:

- canonical vendor ID and display name;
- environment and endpoint ID;
- FHIR base, authorization endpoint, and token endpoint;
- callback URI;
- client authentication method and PKCE behavior;
- requested scopes;
- credential-readiness requirements by environment-variable name only;
- the picker search term and expected endpoint row.

Never record secret values, authorization codes, access tokens, refresh tokens, passwords, or PHI.

## 3. Prepare the account and browser

### Staging

Use a test account. Complete OAuth and initial data sync when valid sandbox credentials exist. Otherwise continue to the furthest reachable step and preserve the failure evidence.

### Production

Create a fresh Antaeus testing account for the run. Do not reuse a personal account. Do not enter vendor credentials and do not access health data. Stop when the external vendor login page or an explicit remote authorization error is visible.

Record the account identifier needed for cleanup without recording its password. Delete the account after the run when a safe supported cleanup path exists; otherwise document the cleanup requirement.

## 4. Test every vendor

Run vendors in a stable order and use stable vendor-slug filenames.

For each vendor:

1. Open Add Data and search using both the vendor name and known endpoint name.
2. Capture the picker screenshot before selection.
3. Select the intended endpoint and trace the relevant API call and response.
4. Follow redirects to the environment-specific stopping point.
5. Capture the furthest-result screenshot.
6. Capture relevant server/browser logs with timestamps and request IDs.
7. Record sanitized configuration and endpoint details.
8. Classify the primary result using the evidence contract.
9. Write a concise diagnosis and the next concrete fix when the state is not `Works`.

If the UI emits no request, or logs are unavailable, create the corresponding evidence file and state that no artifact was generated and why. A documented absence counts as evidence; a missing file does not.

## 5. Update repository artifacts

Reuse established paths. If none exist, use:

- manual: `docs/integration-manual-tests.md`;
- evidence: `docs/integration-test-evidence/<environment>/<YYYY-MM-DD>/`;
- inventory: `<evidence>/vendor-inventory.json`;
- manifest: `<evidence>/run-manifest.json`.

The manual must contain:

- scope, environment, account policy, date, commit, and test limitations;
- one summary-table row per discovered vendor;
- columns for `Integration`, `Environment`, `State`, `Description`, and `Evidence`;
- per-vendor reproduction steps, observed result, API details, logs, configuration, diagnosis, and acceptance criteria;
- totals by state and an explicit list of anything not fully tested.

Link the five evidence artifacts from each vendor section. Keep screenshots and raw artifacts sanitized and reviewable in the PR.

## 6. Validate completeness

Run:

```bash
python3 <skill-directory>/scripts/validate_run_manifest.py \
  --inventory <inventory-json> \
  --manifest <run-manifest-json> \
  --repo-root <repository-root>
```

Fix every validator error. Then manually confirm the report table contains every inventory vendor exactly once and all links resolve.

Do not claim completion if a vendor is missing, an evidence category is absent, or the environment-specific stopping rule was violated.

## 7. Ship a draft PR

1. Review the diff and exclude unrelated user changes.
2. Commit the manual and sanitized evidence on a task branch.
3. Push the branch.
4. Open a draft PR, or update the existing draft PR for the same run.
5. Include the state totals, vendor table, major blockers, test limitations, and artifact paths in the PR body.

Do not create Linear tickets, even for `Error` or `Blocked` results.
