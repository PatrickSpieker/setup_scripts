# Antaeus test accounts

Apply only when the target is Antaeus. Discover the internal MCP tools and inspect current schemas before calls.

- `admin_list_test_accounts`: production-only allowlisted account discovery; does not return passwords.
- `admin_get_sandbox_credentials`: request the exact environment/provider. Firebase supports production and staging; ID.me supports staging only. Never print or persist returned credentials in the report/checkpoint.
- `admin_get_test_references`: non-secret provider setup guidance and synthetic patients.
- `admin_update_test_account`: production-only existing editable fields using the account's current version; useful for prerequisites/restoration. It cannot reset every kind of app data.

Verify account identity before mutation. Use known synthetic records and the correct provider environment. Inspect external service effects independently: test-account membership does not make real charges, recipients, clinical exchange, or other users' records safe to touch. Production external effects become `production restriction` branches.

Record non-secret original values and versions before changes. Restore only fields/data owned by this run when their current values still match this run's changes; otherwise leave them and explain the conflict. Do not delete an account as a generic reset mechanism. Respect idempotency/version requirements in each current tool schema. A queued operation is not completion; inspect its status. For uncertain UI mutations, inspect resulting UI/account state before any retry.

Setup APIs may arrange reachable test prerequisites. They are not evidence that a user followed a UI transition. Capture that transition through browser/simulator navigation.
