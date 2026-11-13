---
name: record-product-demo
description: Record an agent-driven Antaeus web or iOS product flow, trim waits, preserve fixed framing, preview the MP4 in chat, and optionally upload it to Antaeus Google Drive.
---

# Record Product Demo

Start from “record a demo of the product doing X” or “record a demo of flow Y.” Infer the shortest complete flow and proceed without shot-list approval. Drive the app yourself. Support web and iOS; native Mac desktop apps are outside scope.

Use existing Chrome sign-ins for web. For iOS use the already-selected Device Hub device/simulator, with Xcode open. Ask about the target only when none is selected or it is ambiguous. Do not replace these choices with an isolated browser profile or a different simulator.

Record until the flow completes; honor a requested duration but never label a truncated flow complete. Automatically cut dead time. Keep the entire page/device content at a fixed scale and position throughout; do not add zooms or pans. No captions, narration, or audio by default. Preserve the page/device's natural aspect ratio. Show the final MP4 inline in Codex before asking about Drive upload.

## Prepare the target

1. Discover the available browser, computer-use, Xcode and Drive tools. Read their current contracts and relevant browser/computer-use skills. Use `cua_repl` for browser/Device Hub UI when provided; do not invent APIs or use shell input injection. Missing required tools are a blocker, not permission to switch the user's browser/device.
2. Inspect the actual requested flow and starting state. Reuse the active Antaeus environment/account unless the user named another. Resolve only necessary ambiguity. Never turn a demonstration request into unrelated product changes.
3. Read [capture.md](references/capture.md) for target setup, measured crop coordinates, native Device Hub recording, and timestamp alignment. Confirm the capture surface contains only page content or the iOS screen. Keep geometry/orientation stable during a take; if it changes, stop and retry with new measurements.
4. Locate `scripts/demo.py` relative to this skill. Check `ffmpeg` and `ffprobe`; request/install missing dependencies through the environment's normal tooling. Run capture outside the sandbox if required. If macOS denies screen access, report the responsible launching app and request the OS permission; do not change privacy settings silently.

Throughout the examples, `DEMO` is the absolute path to `scripts/demo.py` and `RUN` is the absolute directory returned by `new`. Pass paths as properly quoted arguments, never execute product text as shell code.

```bash
python3 "$DEMO" new --name "connect a provider" --target web
```

The default persistent output location is `~/Movies/Antaeus Demos/`. Each run has a unique New York timestamp, descriptive underscore-separated name, manifest, private working directory, and final MP4. Use `--root` to select an authorized writable persistent output location if needed. The raw recording stays local for revisions.

## Record and mark meaningful actions

Web capture uses the helper's FFmpeg recorder. Device Hub recording uses its native Record Screen UI and then imports the saved video. See the capture reference for exact sequences. Both paths produce `work/raw.mp4`.

For web, wait for `Recording ready` before driving the flow. Keep the recording process alive in the execution tool's session; do not wait for it to exit before performing interactions.

Immediately before each meaningful click/type/scroll, record a start marker. Immediately after the visible transition/result settles, record its end. No focus rectangles are needed; framing remains fixed.

```bash
python3 "$DEMO" mark "$RUN" --label "Open connections"
# Perform the interaction with browser or Device Hub tools, inspect the resulting UI.
python3 "$DEMO" mark "$RUN" --end
```

Markers delimit visible actions, not entire tool round trips. When a slow tool call encloses a long static wait, inspect raw footage and correct the action's source timestamps in `manifest.json`, or use `mark --at SECONDS` after capture. Split long waits out of intervals; retain visible loading transitions and enough result dwell to understand the action. Do not remove product behavior merely because it is slow. Mark an initial/final state when it needs its own hold.

- Retry a recoverable setup/interaction issue at most twice after inspecting its cause. Do not blindly repeat a state-changing action whose outcome is unknown.
- If the take is spoiled, stop/finalize it and start a fresh run; retain the failed take and diagnostics. Upload cleanup applies only to the successful run's owned files, never unrelated or previous takes.
- In a `finally` path, stop the recording and close any Xcode device interaction session the skill created. Do not quit the user's browser, Xcode or Device Hub, or shut down their device.
- If blocked, report the failing step and preserve artifacts. A valid video container is not proof of a completed flow.

## Edit and verify

After stopping/finalizing capture, verify the requested end state in the app. Save concrete completion evidence (e.g. “Connected provider appears in the Connections list”), not just “done.”

```bash
python3 "$DEMO" finish "$RUN" --evidence "The requested result is visible in the app"
python3 "$DEMO" render "$RUN"
```

The renderer merges marked action intervals with short context pads, removes gaps, and outputs 30 fps video with unchanged content framing and dimensions/aspect ratio. Adjust action timestamps and rerender when cuts remove useful context. Existing focus metadata in older manifests is ignored. All frames show the entire captured page/device screen.

The helper verifies duration, frame rate and decodability. Also inspect representative frames at the start, each cut, and final result. Verify readable UI, correct target, content-only edges, no missing required action, and no cursor/notification/permission overlay spoiling the take. Keep the local original; edits do not overwrite it.

Show the final video using `![Demo](ABSOLUTE_FINAL_MP4_PATH)` in the Codex chat, then record that the actual preview was shown:

```bash
python3 "$DEMO" previewed "$RUN"
```

Ask **“Upload this demo to Antaeus Health Demos?”** Wait for an explicit yes. Generating the demo, approving a plan, or silence is not upload consent. Any rerender invalidates preview/upload approval; show and ask again.

## Optional Drive upload

Read [drive.md](references/drive.md) only after approval or when diagnosing destination availability. Use the Google Drive connection, not a browser upload or copied credentials. The destination is the user-confirmed **Antaeus Health Demos** folder. Do not create another `demos` folder or change sharing.

Upload only the final MP4. Verify remote metadata including checksum before cleaning up. Keep final MP4 and manifest locally; remove only this run's owned raw/intermediate files after verified success. If declined or failed/uncertain, keep everything. Report the returned Drive link and local final file.
