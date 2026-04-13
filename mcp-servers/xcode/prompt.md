# Parallel Xcode Agent Environment

You are running inside a Moat container on a git worktree branch. You have access to Xcode build/test/simulator tools via an MCP server called `xcode`. These tools execute on the host Mac, not inside your container.

## Critical: Always pass your branch name

Every `xcode` MCP tool requires a `branch` parameter. Get it once at the start of your session:

```bash
git branch --show-current
```

Pass this exact string to every tool call. The MCP server uses it to route commands to your specific worktree and simulator. If you pass the wrong branch, you'll build or test against another agent's files.

## Available tools

- **xcodebuild** — `action` (build/test/clean), `scheme`, `branch`, optional `configuration` (Debug/Release), optional `extra_args`. Timeout: 5 minutes.
- **simulator** — `action` (boot/shutdown/status), `branch`. Boot your simulator before building or testing.
- **install_and_launch** — `branch`, `app_path` (relative to worktree root, e.g. `DerivedData/Build/Products/Debug-iphonesimulator/YourApp.app`), optional `bundle_id`.
- **screenshot** — `branch`, optional `filename`. Saves to worktree root. Use to visually verify UI changes.

## Workflow

1. Get your branch name
2. Boot your simulator
3. Make code changes
4. Build with `xcodebuild`
5. If build succeeds, run tests or install and launch
6. Screenshot to verify if doing UI work

## Things to know

- **DerivedData is per-worktree** — build artifacts are at `./DerivedData` relative to your worktree, not the shared `~/Library` location.
- **You have a dedicated simulator** — no other agent shares it, so you won't see interference.
- **Build output is truncated** — you'll see the last ~4000 characters. If a build fails, the error is usually at the tail.
- **You cannot run xcodebuild or xcrun directly** — these tools only exist on the host. Always use the MCP tools.
- **Code signing** — pass `extra_args: 'CODE_SIGNING_ALLOWED=NO'` if you're just building for the simulator and hitting signing errors.
