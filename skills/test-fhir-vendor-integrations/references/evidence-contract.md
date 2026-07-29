# Evidence and reporting contract

## State taxonomy

Assign one primary state per vendor.

| State | Meaning |
|---|---|
| `Works` | The environment-specific target completed. Staging completed OAuth, patient read, and initial sync; production reached the real external vendor login page without entering vendor credentials. |
| `Partial` | The flow made meaningful progress but stopped after the minimum target began, such as an external login page followed by a callback or sync failure. |
| `Blocked` | Missing access, configuration, endpoint data, or another external prerequisite prevented a meaningful integration attempt. |
| `Error` | A configured and reachable integration behaved incorrectly or was rejected with an actionable application/vendor error. |
| `Not tested` | Testing was intentionally skipped. State the reason and still provide all five evidence records, using explicit “not generated” notes where necessary. |

Prefer `Blocked` for absent prerequisites and `Error` for observed defects. Do not use `Works` for a staging run that only reached the login page.

## Mandatory evidence

Create five sanitized, repository-relative files for every vendor:

1. **Picker screenshot**: show the search term and selected endpoint row. If no row exists, show the empty result.
2. **Result screenshot**: show the furthest visible state, including remote or local errors.
3. **API call**: record method, sanitized URL, status, request ID, sanitized request parameters, sanitized response, and timestamp. If no request occurred, record why.
4. **Logs**: record source, timestamp range, request/correlation IDs, and the minimal relevant excerpt. If unavailable, record the attempted lookup and why it failed.
5. **Configuration**: record endpoint IDs/URLs, environment, callback, client-auth method, PKCE, scopes, and credential variable names/readiness. Never record credential values.

Use PNG for screenshots and UTF-8 JSON or text for other evidence. Redact secrets, tokens, authorization codes, cookies, passwords, email verification links, and PHI.

## Inventory schema

```json
{
  "environment": "staging",
  "generated_at": "2026-07-29T12:00:00Z",
  "vendors": [
    {
      "id": "vendor-slug",
      "name": "Vendor Display Name"
    }
  ]
}
```

Use `production` only for an explicitly requested production run.

## Run manifest schema

```json
{
  "environment": "staging",
  "vendors": [
    {
      "id": "vendor-slug",
      "name": "Vendor Display Name",
      "state": "Error",
      "description": "Authorization server rejected the registered redirect URI.",
      "evidence": {
        "picker_screenshot": "docs/integration-test-evidence/staging/2026-07-29/vendor-picker.png",
        "result_screenshot": "docs/integration-test-evidence/staging/2026-07-29/vendor-result.png",
        "api_call": "docs/integration-test-evidence/staging/2026-07-29/vendor-api.json",
        "logs": "docs/integration-test-evidence/staging/2026-07-29/vendor-logs.txt",
        "configuration": "docs/integration-test-evidence/staging/2026-07-29/vendor-config.json"
      }
    }
  ]
}
```

The inventory and manifest vendor IDs must match exactly. Evidence paths must stay inside the repository and point to non-empty files.
