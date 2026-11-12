# UI drivers

Choose the available driver for the target. Read its installed skill and current tool schema before acting; tool names and capabilities change. Capture the app itself, not screenshots supplied by the user.

## Web

Prefer the user's requested browser; otherwise an available browser automation surface. Discover current browser tools (e.g. Playwright or computer-use browser tools) and follow the matching installed browser skill. Inspect the live accessibility/DOM snapshot before actions, refresh after navigation or layout changes, and capture screenshots through that same session. Use semantic targets before coordinates. Keep authentication in the active session; never export cookie jars, bearer tokens, or passwords into evidence.

Observe transient states when possible; do not wait away a loading or validation state that belongs in the graph. Do not invent an uncaptured transient state. Capture the viewport and scroll through content to discover offscreen actions. URL alone is not a state identifier. Default viewport/theme remain fixed during a run.

## iOS

Read available `ios-debugger-agent` and `pr-screenshots-ios` skills for current XcodeBuildMCP mechanics. Use their direct UI capture approach, not their PR publishing or changed-diff-only scope. Read session defaults before build/run/test; discover the intended project/workspace and scheme, list runtimes/simulators, and pin an exact simulator UDID. Follow the installed runtime-selection policy. Never silently change device/runtime during a run.

Build/run the target app when necessary, verify the launched frame, then inspect current UI before taps/text/scroll/gestures. For an already installed app, project/scheme discovery is unnecessary. If actions report success but the screen stays unchanged, open the simulator frontend through MCP and re-inspect before retrying; tool success alone is not transition evidence. Prefer accessibility references, refresh them after layout changes, and capture through XcodeBuildMCP screenshot tools. Do not create an XCUITest tour solely for this report. If automation workflows are missing, report the limitation and retain partial evidence; do not fake native captures or silently substitute raw shell control.

Meaningful keyboards, permission sheets, errors, and loading states are part of this task even though a PR screenshot tour might normally dismiss them. The `ios-simulator-browser` mirror is optional: if used, pin it to the same UDID and clean up only that run's helper. Do not shut down or erase a shared simulator.

## Other native platforms

Android requires an available emulator driver that can inspect, interact, and capture. Discover one if installed and apply the same evidence/checkpoint contract. If none exists, explicitly report Android unsupported in this session. Never claim iOS tools verify Android.
