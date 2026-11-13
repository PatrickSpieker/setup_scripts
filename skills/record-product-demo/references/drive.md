# Antaeus Drive upload

User-confirmed destination:

- Folder: **Antaeus Health Demos**
- ID: `115PfFulm_kVSzZ3MZ00w42rQAR04sIBz`
- URL: https://drive.google.com/drive/folders/115PfFulm_kVSzZ3MZ00w42rQAR04sIBz
- Account: an authenticated `@antaeus.health` account (discovery confirmed `patrick@antaeus.health`).

Discover the current Drive tools and use the Google Drive skill. The Python helper never accesses credentials or performs network uploads; it generates connector arguments and validates connector readbacks. Save provider objects from `structuredContent`/returned JSON, not the MCP envelope, in local JSON files. Those receipts may live in `work/`; register them in `owned` if this run created them.

1. After showing the actual local preview and receiving the user's explicit answer:

```bash
python3 "$DEMO" decision "$RUN" approve
# Or: python3 "$DEMO" decision "$RUN" decline
```

2. Read the Drive profile and exact folder metadata. Request `id,name,mimeType,trashed,capabilities(canAddChildren)` for the folder. Do not substitute a same-named folder. If the folder was removed, renamed, or access changed, ask for the replacement destination; do not create folders automatically. Update the configured destination only with user direction.

3. Save these normalized readbacks as `profile.json` and `folder.json`, then generate upload arguments:

```bash
python3 "$DEMO" upload-request "$RUN" --profile /absolute/profile.json --folder /absolute/folder.json
```

Call the connected Google Drive `upload_file` tool with the emitted arguments: `file_uri` (absolute final MP4 path), `file_name`, `mime_type: "video/mp4"`, and `parent_folder_id`. The name was generated once with America/New_York time when the run was created. Never change sharing permissions.

4. Read metadata for the actual returned file ID with `id,name,mimeType,parents,size,md5Checksum,webViewLink,trashed`. The connector may normalize fields to `title`, `mime_type`, `parent_ids`, and `url`; the helper accepts both forms. It may omit capabilities/checksums even when requested. Explicit `canAddChildren: false` blocks upload; unknown capability is resolved by the approved upload itself. Verify bytes and folder before cleanup:

```bash
python3 "$DEMO" verify-upload "$RUN" /absolute/remote-file-metadata.json
python3 "$DEMO" cleanup "$RUN"
```

If metadata omits MD5, fetch the uploaded file's raw bytes with the Drive connector and materialize its returned authenticated file reference. Pass that separate local readback path:

```bash
python3 "$DEMO" verify-upload "$RUN" /absolute/remote-file-metadata.json --downloaded /absolute/remote-readback.mp4
```

The helper compares SHA-256 against the approved final video. Never pass a copy of the local source as remote readback. If the connector cannot provide bytes or required identity/parent/size/link fields, retain all artifacts and report verification blocked. Register a run-owned download under `work/` for cleanup; never delete a shared connector cache path.

Return the observed `webViewLink` or normalized `url`; never fabricate a success URL. If Drive processing is pending, distinguish verified stored bytes from playback readiness. Open/check the returned video when possible; do not claim remote playback was verified merely because upload succeeded.

## Failed or uncertain upload

On timeout/error, record `upload-uncertain` and keep all artifacts. Search the exact parent folder for the exact filename using Drive's provider filter; paginate to completion. Check candidate metadata against local size and MD5. One matching candidate can be verified normally; multiple candidates need reconciliation, not another upload. Do not delete remote duplicates automatically.

If a fresh, complete search confirms the file is absent, repeat the approved upload using the saved `upload_request` in the manifest, without generating a new timestamp/name. Allow at most two retries after diagnosing the failure. On unresolved absence/ambiguity or missing metadata or both checksum and downloadable bytes, report upload as unverified and retain everything. Do not reset the helper state to bypass approval or verification.

Rerendering changes the final bytes and invalidates consent. Prior uncertain upload requests remain in `previous_uploads` for reconciliation; do not treat those old requests as approval for revised bytes. Preview the revised video and obtain new upload approval before a new upload. Raw recordings and temporary edits are deleted only by `cleanup` after successful verification; final MP4 and manifest are retained.
