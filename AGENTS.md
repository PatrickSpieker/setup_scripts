## Goal

- Keep agent prompts and skills lean, reproducible, and context-aware.

## Repo

- This repo holds my dotfiles, shared agent prompts/skills, and install scripts for local tools.

Context for Moat can be found at: https://majorcontext.com/moat/llms.txt

## Moat

- When running inside Moat, prefer `gh` for all GitHub operations (creating PRs, pushing branches, fetching repo info) rather than `git push` / `git clone` over HTTPS or SSH. The `github` grant makes `gh` the most reliable transport — system-level git `insteadOf` rules can silently rewrite URLs and cause failures.
## iOS Build Bridge

When working on an iOS/Xcode project inside a Moat container, there is no
direct access to Xcode or the iOS Simulator.  Instead, use the `ios-build`
command which bridges to the host's Xcode toolchain via the filesystem.

```
ios-build build              # xcodebuild build
ios-build test               # xcodebuild test
ios-build clean build        # xcodebuild clean build
ios-build simctl list        # xcrun simctl list
```

The command blocks until the host finishes the build and returns the output.
Build times depend on project size — expect 30-120s for a typical build.

Do NOT attempt to run `xcodebuild` or `xcrun` directly — they are not
available inside the container.

Context for Claude Code can be found at: https://platform.claude.com/llms.txt
Context for Codex can be found at: https://developers.openai.com/codex/llms.txt
