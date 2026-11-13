# Capture paths

## Web: existing Chrome + cropped FFmpeg

Use the connected Chrome browser's DOM-aware tools for interactions and state inspection. Use its existing profile/session; do not launch Playwright with a fresh profile. If the Chrome connection is absent, report that prerequisite rather than silently using the in-app browser. Reuse the requested tab or create a task tab in that existing session according to the browser tool's contract.

Measure the page-content rectangle in desktop logical coordinates from current UI bounds, and measure the display origin and pixel scale from its screenshot/capture dimensions. Do not assume the main display, a 2× scale, or a fixed browser toolbar height. Verify edges with a current screenshot. If the browser provides exact viewport/screen geometry, prefer that evidence. Window outer bounds alone are insufficient. A tab screenshot can establish the page's dimensions, but is not a continuous recording.

List video inputs (the trailing FFmpeg input error is normal for device listing):

```bash
python3 "$DEMO" devices
```

Select the observed `Capture screen N` entry for the display containing the entire page. Never select a camera. Convert measured logical bounds to display-relative capture pixels:

```bash
python3 "$DEMO" bounds --rect 120 160 1200 780 --origin 0 0 --scale 2 2
```

These numbers illustrate argument order only. Use real observed bounds. `bounds` converts x/y relative to the display origin and rounds width/height down to even pixels (at most one pixel), preserving the content's aspect ratio to encoding precision. Keep the page unobscured and the window stationary. Screen capture records whatever covers the chosen region; reject spoiled takes.

Start with the discovered video input and content-only crop:

```bash
python3 "$DEMO" record "$RUN" --device 3 --crop 240 320 2400 1560
```

Use an execution session that yields while the recorder runs. The helper emits `Recording ready` after frames arrive; mark and drive actions only then. It writes only the cropped page to raw video, has a 15-second no-frame startup deadline, and uses an explicit 30 fps output. `--duration N` is optional and only used when requested. Stop from another command:

```bash
python3 "$DEMO" stop "$RUN"
```

Wait for the recording execution session to finish, then inspect its manifest/log. Never force-kill a healthy capture: MP4 needs graceful finalization. If interrupted, the helper attempts graceful shutdown and bounds its fallback termination waits. If startup fails, retain `work/capture.log`; check screen permission for the launching application, restart it after a grant if necessary, and retry within the skill's retry limit.

## iOS: Device Hub with Xcode open

Inspect running apps and Device Hub's selected sidebar row/window title. Require Xcode to be open (launch it if closed using the available app launcher). Ask only when no target is selected or selection is ambiguous; do not select a different target merely because it is easier to automate. Record the observed device identity and orientation in the run manifest.

The verified macOS app bundle ID is `com.apple.dt.Devices`. Its selected-device view exposes the iOS app hierarchy, **Record Screen**, **Screenshot**, **Home**, and rotation controls. Use fresh UI observations to locate controls; do not hardcode accessibility indices. Open/drive the requested Antaeus app through this Device Hub view. If Xcode's `DeviceInteraction*` tools are needed, bind them to the exact selected device, obey returned tool guidance, and close sessions you create.

1. Prepare the app's starting state before recording.
2. Click Device Hub's **Record Screen** control. Inspect the resulting UI to confirm recording is active.
3. Immediately run `python3 "$DEMO" clock "$RUN"` to anchor action markers, then drive the flow with Device Hub and mark actions as in the main skill.
4. Stop recording through the observed Device Hub control. Save the video into this run's `work/` directory using the save UI if offered. Do not guess where it was saved; inspect the returned UI/path or observed destination. In the verified Device Hub version, stopping automatically saves `Screen Recording <device> <date>.mp4` on Desktop. Identify the new export by its exact device and capture time; do not pick an unrelated latest recording.
5. Import the saved video. Clock start follows the actual recording start, so add the measured lead-in via `--offset`; compare the first marked action with the raw video to establish it, rather than assuming zero.

```bash
python3 "$DEMO" import "$RUN" /absolute/saved-device-video.mov --offset 1.2
```

Import copies the original without modifying it. For a new native export created by this take (including an automatic Desktop save), use `import --move` to adopt it into `work/raw.mp4`, avoiding a stray duplicate outside the cleanup scope. Never use `--move` on a pre-existing user recording. If the native export was saved under this run's `work/`, register that exact file in the manifest's `owned` list for post-upload cleanup (relative `work/...` path). Never register a pre-existing external file. Check all markers after alignment; markers may instead be reconstructed from the finished video with `mark --at`.

Device Hub native video should contain only the device screen. Verify dimensions, orientation, and content. If native recording is unavailable for the selected device, use a live Device Hub mirror only when its screen bounds are observable and stable: crop it with FFmpeg using the web recording mechanics, preserving the device's aspect ratio. Do not replace video with a screenshot slideshow. If neither path works, report the limitation without changing the selected target.
