# Checkpoint CLI

Requires Python 3.10+ on macOS/Linux; no packages. Resolve the script relative to this skill. Commands serialize writes with a file lock and atomically save `graph.json`, then regenerate `report.html`. A renderer failure leaves the checkpoint recoverable. Do not edit checkpoint JSON manually.

```bash
python3 <skill>/scripts/report.py --run <working-directory> init \
  --title 'App UI flows' --app 'App' --platform web \
  --role 'test user' --device '1280x800' --theme light --build '<commit or version>'
```

Optional init flags: `--mode staging`, `--workflow 'Sign up'`, `--max-states 50`, `--max-seconds 1800`. Omitted limits mean no cap. Seconds are wall time since initialization (including interruptions); a resume does not silently extend the requested budget. Production is the default. Use `inspect` to read progress, `resume` to reactivate it, and `render [--output /absolute/report.html]` to rebuild a report without altering the checkpoint. Keep an unfinished run's ID and directory stable.

For `state`, `action`, and `change`, write the following JSON record to a temporary input file and pass `--input <path>`. Input files must contain no secrets and may be removed after import. All fields below are strings. IDs contain letters, digits, hyphens, or underscores, at most 80 characters.

## State

```json
{"id":"s1","title":"Dashboard","key":"dashboard:member:empty","screenshot":"/absolute/capture.png","evidence":"Navigated through sign-in; dashboard heading visible","url":"https://app.example/dashboard","prerequisites":"Signed in as test member","observations":"No records yet"}
```

Required: `id`, `title`, `key`, `screenshot`, `evidence`. Screenshot bytes are copied into the run directory. PNG/JPEG/WebP only. `key` is an agent-chosen appearance-plus-behavior equivalence key; duplicate keys are rejected so equivalent records reuse the existing ID. Credentials/query strings/fragments must not be included in metadata; URL query, fragment, and userinfo are stripped on import. Check URL paths for secrets too. Inspect screenshots for visible secrets before import; a byte-format check does not certify privacy.

## Action

```json
{"id":"a1","from":"s1","label":"Click Create record","effect":"test-account","provenance":"ui: Create record button","prerequisites":"Test account owns the destination record"}
```

Required: all except `prerequisites`. `effect` is `read-only`, `test-account`, or `external`. Unknown effects are `external` until investigated; classify based on actual services/recipients, not the screen's label. Provenance may instead be `source: path:line`.

```bash
python3 <skill>/scripts/report.py --run <dir> begin a1
```

**Only `READY` authorizes proceeding with that recorded action.** `BLOCKED`/`STOPPED` saves a report but does not execute anything. The helper does not drive the UI. `begin` checkpoints `in_flight` before navigation. The state limit prevents starting new actions at the cap; a previously started action's outcome can still be captured when its time limit expires.

After UI navigation and importing the observed destination:

```bash
python3 <skill>/scripts/report.py --run <dir> resolve a1 --to s2 --evidence 'Created synthetic record; confirmation visible'
```

For a known action not explored:

```bash
python3 <skill>/scripts/report.py --run <dir> block a2 --reason 'outside requested workflow' --explanation 'Account settings are outside sign-up scope'
```

Other reasons: `production restriction`, `unreachable`, `exploration limit`. Blocking an in-flight action requires first inspecting whether it happened; explain uncertainty when it cannot be determined. Do not call it a confirmed failure. An in-flight action cannot be begun again; `resume` intentionally does not reset it. If inspection confirms an action never happened, block that attempt with the explanation and create a new action ID for an intentional retry.

## Restoration

```json
{"id":"c1","description":"Test profile display name","original":"Test Member","expected":"Flow Test","status":"pending","explanation":"Restore after profile flow"}
```

Required: `id`, `description`, `status`, `explanation`. `original`/`expected` are optional non-secret values used locally for comparison; they are excluded from HTML. Never store passwords, access codes, tokens, cookies, or sensitive restoration data here. Before restoring, compare current values/version with the recorded expected state. Use the same change ID to update status to `restored` or `left-behind`, explaining failures or concurrent edits. The helper records outcomes; the agent performs restoration through approved app tools.

## Finish

```bash
python3 <skill>/scripts/report.py --run <dir> finish --status exhausted --explanation 'Inspected all discovered controls in the current role and viewport'
```

`exhausted` requires at least one captured state and no pending/in-flight actions. Blocked branches remain visible. For limits, tool failures, or interruption, use `--status stopped` with an explanation; pending/in-flight branches render as `exploration limit`, with uncertain outcomes distinguished. Unknown undiscovered coverage is explicit. `change` commands still work after stopping so cleanup can be recorded. No automatic deletion of test accounts or screenshots occurs.
