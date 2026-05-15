# setup_scripts

Personal dev environment setup: dotfiles, AI agent skills, and install scripts for macOS.

## Quick Start

```bash
# Full setup (Homebrew, bash, neovim, skills, SwiftBar, etc.)
./setup.sh

# Or just install Homebrew packages
brew bundle --file Brewfile
```

> **Note:** After cloning, mark the setup script as executable: `chmod 755 ./setup.sh`

## Repo Structure

```
setup_scripts/
├── setup.sh                 # Main install script (Homebrew, bash, vim, skills, SwiftBar)
├── Brewfile                 # Homebrew packages (git, gh, neovim, ripgrep, fzf, codex, etc.; claude-code uses native installer)
├── AGENTS.md                # Agent-facing instructions. Linked as user-scope global rules to ~/.claude/CLAUDE.md and ~/.codex/AGENTS.md on every shell start (bashrc_main) and inside Moat (bootstrap_agent_homes.sh). In-repo symlink: .claude/claude.md → ../AGENTS.md.
├── moat.yaml                # Moat runtime config (grants, hooks for skills + pre-push)
├── bashrc_main              # Bash config (aliases, git shortcuts, PATH, oh-my-bash, fzf)
├── bash_profile_main        # Bash profile (sources bashrc)
├── vimrc_main               # Neovim config (vim-plug, keymaps, plugins)
├── vscode_settings.json     # VS Code settings
├── obsidian_vimrc           # Obsidian vim keybindings
├── hammerspoon/             # Hammerspoon Lua config (symlinked to ~/.hammerspoon/)
│   └── init.lua             #   Minimal starter: hyper+R reloads, alert on load
├── defaults/
│   ├── settings.json        # Claude Code defaults (symlinked to ~/.claude/settings.json)
│   └── codex-moat-config.toml # Codex defaults inside Moat (copied to ~/.codex/config.toml)
├── hooks/
│   └── pre-push             # Blocks Claude Code from pushing to main/master (generic)
├── scripts/
│   └── bootstrap_agent_homes.sh # Links skills/, settings.json, AGENTS.md into ~/.claude and ~/.codex (used by moat.yaml pre_run)
├── templates/
│   ├── moat.yaml            # Template moat config for Claude Code projects (used by `mcl`)
│   └── moat-codex.yaml      # Template moat config for Codex projects (used by `mco`)
├── skills/                  # AI agent skills (Claude Code + Codex CLI)
│   ├── gh-commit/           #   Conventional commits
│   ├── gh-ship/             #   Commit + push + create PR
│   ├── gh-review-pr/        #   Thorough PR review
│   ├── gh-fix-ci/           #   Fix first failing CI check
│   ├── gh-address-pr-comments/ # Resolve PR review comments
│   ├── pr-screenshots/      #   Capture Playwright screenshots for PR walkthrough
│   ├── make-tests/          #   Generate tests for current changes
│   ├── design-doc/          #   Structured design documents
│   ├── de-slop/             #   Remove AI artifacts before PR
│   ├── explore-repo/        #   Structured codebase exploration
│   ├── work-forever/        #   Autonomous long-running mode
│   ├── subagent/            #   Delegate to Codex exec subagent
│   ├── new-skill/           #   Create a new skill
│   ├── new-cmd/             #   Create a new command
│   ├── delegate-cursor-background-task/ # Hand off work to Cursor agent
│   ├── youtube-extractor/   #   Extract YouTube transcripts + metadata
│   ├── pdf-viewing/         #   OCR and rasterize PDFs
│   ├── cc-llms/             #   Claude Developer Platform context (bundled llms.txt)
│   ├── codex-llms-full/     #   OpenAI Codex context (bundled llms.txt)
│   ├── linear-llms/         #   Linear context (bundled llms.txt index)
│   ├── moat-llms-full/      #   Moat context (bundled llms.txt)
│   └── render-llms-full/    #   Render context (bundled llms.txt)
└── swiftbar_plugins/
    ├── ai_token_usage.1m.py # Menu bar token usage tracker (Claude + Codex, 1-min refresh)
    └── moat_orphans.5m.py   # Menu bar warning for stale Moat containers (5-min refresh)
```

## Skills

Skills are tool-agnostic workflows that work in both Claude Code (`/skill-name`) and Codex CLI (`$skill-name`).

| Skill | Description |
|-------|-------------|
| `gh-commit` | Create small, logical commits with conventional commit messages |
| `gh-ship` | Commit, push, and create PR in one step |
| `ship-plan` | Open a `feat/<slug>` PR off main with the current plan as the PR description (single empty marker commit, no file in repo). Plan-first review before any implementation; implementation commits land on the same branch later |
| `gh-review-pr` | Review a GitHub PR focusing on correctness, tests, and risk |
| `gh-fix-ci` | Find the first failing CI check and fix it |
| `gh-address-pr-comments` | Resolve actionable PR review comments one-by-one |
| `pr-screenshots` | Capture Playwright screenshots for each user journey and embed them in the PR description |
| `make-tests` | Add tests for the change you're working on |
| `tdd` | Test-driven development with red-green-refactor loop |
| `design-doc` | Format implementation plans as structured design documents |
| `de-slop` | Remove AI artifacts and cleanup noise before a PR |
| `explore-repo` | Structured codebase exploration before planning or building |
| `zoom-out` | Get a higher-level map of an unfamiliar area of code, using the language in CONTEXT.md |
| `improve-codebase-architecture` | Find deepening refactoring opportunities informed by CONTEXT.md and docs/adr/ |
| `grill-with-docs` | Stress-test a plan against the project's domain model and ADRs; update docs inline |
| `work-forever` | Run in highly autonomous mode for long-running tasks |
| `subagent` | Delegate exploration to a non-interactive Codex exec run |
| `new-skill` | Create a new skill from conversation history |
| `new-cmd` | Create a new command from conversation history |
| `to-prd` | Turn the current conversation context into a PRD and submit it as a GitHub issue |
| `delegate-cursor-background-task` | Create a GitHub/Linear ticket for Cursor's background agent |
| `youtube-extractor` | Extract transcripts, titles, and thumbnails from YouTube videos |
| `pdf-viewing` | OCR PDFs with page tracking and rasterize to images |
| `pdf-to-epub-md` | Batch-convert PDFs in the current dir to EPUB-bound markdown via marker, then dispatch one `epub-md-formatter` agent per book to clean each output |
| `cc-llms` | Load context on the Claude Developer Platform from a bundled llms.txt reference |
| `codex-llms-full` | Load context on OpenAI Codex (CLI, IDE, cloud, SDK) from a bundled llms.txt reference |
| `linear-llms` | Load context on Linear (issues, GraphQL API, SDK) from a bundled llms.txt index |
| `moat-llms-full` | Load context on Moat (container runtime for AI agents) from a bundled llms.txt reference |
| `render-llms-full` | Load context on Render (cloud platform) from a bundled llms.txt reference |
| `render-debug` | Debug failed Render deployments by analyzing logs, metrics, and database state |
| `render-monitor` | Monitor Render services in real-time — health, metrics, logs, deployment verification |
| `firebase-basics` | Firebase CLI setup and project management (install check, login, active project, web SDK) |
| `firebase-auth-basics` | Set up and use Firebase Authentication (provisioning, sign-in flows, security rules) |

### How skills are installed

- **Claude Code:** `setup.sh` symlinks `skills/` to `~/.claude/skills/`
- **Codex CLI:** `sync-skills` in `bashrc_main` symlinks each skill to `~/.codex/skills/` on every shell startup

## Agents

Subagents are Claude-only and live in `agents/<name>.md`. `setup.sh` symlinks `agents/` to `~/.claude/agents/`; inside Moat, `bootstrap_agent_homes.sh` links each `*.md` individually so the directory itself stays a real dir.

| Agent | Description |
|-------|-------------|
| `epub-md-formatter` | Reformat marker-extracted markdown into EPUB-bound markdown ready for Calibre/Pandoc. Dispatched per-book by the `pdf-to-epub-md` skill. |

## Dotfiles

| File | Installs to | Notes |
|------|-------------|-------|
| `bashrc_main` | `~/.bashrc` | Aliases, git shortcuts, PATH, fzf config, oh-my-bash (purity theme) |
| `bash_profile_main` | `~/.bash_profile` | Sources bashrc |
| `vimrc_main` | `~/.config/nvim/init.vim` | vim-plug managed; run `:PlugInstall` after setup |
| `vscode_settings.json` | `~/Library/Application Support/Code/User/settings.json` | |
| `hammerspoon/` | `~/.hammerspoon/` | Lua automation config; hyper (cmd+alt+ctrl) + R reloads |
| `obsidian_vimrc` | (manual) | Vim keybindings for Obsidian |

## Moat

`moat.yaml` configures the [Moat](https://majorcontext.com/moat/llms.txt) sandbox runtime:

- **Grants:** `claude`, `github`, `ssh:github.com`
- **post_build hook:** Clones this repo, symlinks `skills/` to `~/.claude/skills/`, and runs `npx playwright install chromium` so the Playwright MCP server has a browser in the container image.
- **pre_run hook:** Sets `core.hooksPath` to point at `hooks/` from the cloned repo and passes `--moat` to `bootstrap_agent_homes.sh` so the container-scoped settings file is linked.
- **Env:** `IN_MOAT=1` flags the container so tooling (e.g., the `pr-screenshots` skill) can pick between headful and headless behavior.

The `pre_run` hook uses per-worktree git config (`extensions.worktreeConfig` + `git config --worktree`) so that each Moat container's hook configuration is isolated and doesn't write to the shared git common directory.

### Playwright: host-headful, container-headless

The Claude settings file is split so the Playwright MCP server behaves differently in each context:

- **Host** (`defaults/settings.json`, symlinked to `~/.claude/settings.json` on the laptop): Playwright runs **headful** via `npx @playwright/mcp@latest --isolated`, so you can watch the browser.
- **Container** (`defaults/settings-moat.json`, linked by `bootstrap_agent_homes.sh --moat`): Playwright runs **headless** with `--no-sandbox`, since the container has no display.

There is no CDP, WebSocket, or port forwarding between host and container — each runs its own browser, fully isolated.

`templates/moat.yaml` is a starter config for Claude Code projects (used by `mcl`); `templates/moat-codex.yaml` is the equivalent for Codex projects (used by `mco`). Both use the same `hooksPath` approach, which means all hooks in `hooks/` are active. The hooks here are generic (only `pre-push` currently), so they're safe to drop into any repo.

## Hooks

| Hook | Purpose | Scope |
|------|---------|-------|
| `hooks/pre-push` | Prevents Claude Code (`$CLAUDECODE=1`) from pushing to `main` or `master` | Generic — safe for all repos |

## SwiftBar Plugins

- `swiftbar_plugins/ai_token_usage.1m.py` — token usage leaderboard for Claude Code and Codex (1-minute refresh).
- `swiftbar_plugins/moat_orphans.5m.py` — warning indicator for stale Moat containers (5-minute refresh).

Both are installed by `setup.sh` via a single symlink of `swiftbar_plugins/` to `~/.swiftbar/plugins/`.

## Shell Highlights

- `nvim` aliased as `vim`; `vi` left alone for git rebase compatibility
- `rm` routed to `trash` when available
- `noclobber` enabled
- fzf backed by ripgrep (`rg --files --hidden`)
- Git aliases: `gs` (status), `gc` (commit -am), `gacp` (add + commit + push), `gpoh` (push origin HEAD)
- Moat + Claude: `mcl` (new worktree session), `mclpr <pr>` (resume PR branch), `mclb <branch>` (resume any remote branch). Pass `-r`/`--rebuild` to any of these (and `mco`) to force rebuild of the container image.
- Docker: `sd` (open Docker), `sac` (start container system)
