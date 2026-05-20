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
│   ├── settings.json        # Claude Code defaults on the host (symlinked to ~/.claude/settings.json)
│   ├── settings-moat.json   # Claude Code defaults inside Moat (linked by bootstrap_agent_homes.sh --moat; headless Playwright + --no-sandbox)
│   └── codex-moat-config.toml # Codex defaults inside Moat (copied to ~/.codex/config.toml)
├── hooks/
│   └── pre-push             # Blocks Claude Code from pushing to main/master (generic)
├── scripts/
│   ├── bootstrap_agent_homes.sh # Links skills/, settings.json, AGENTS.md into ~/.claude and ~/.codex (used by moat.yaml pre_run)
│   └── playwright-mcp.sh    # Launcher for @playwright/mcp inside Moat — resolves bundled Chromium, bridges HTTPS_PROXY auth, ignores TLS-intercept certs
├── templates/
│   ├── moat.yaml            # Template moat config for Claude Code projects (used by `mcl`)
│   └── moat-codex.yaml      # Template moat config for Codex projects (used by `mco`)
├── skills/                  # AI agent skills (Claude Code + Codex CLI) — see Skills table below
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
| `gh-review-pr` | Review a GitHub PR focusing on correctness, tests, and risk |
| `gh-fix-ci` | Find the first failing CI check and fix it |
| `gh-address-pr-comments` | Resolve actionable PR review comments one-by-one |
| `pr-screenshots` | Capture Playwright screenshots for each user journey and embed them in the PR description |
| `make-tests` | Add tests for the change you're working on |
| `tdd` | Test-driven development with red-green-refactor loop |
| `de-slop` | Remove AI artifacts and cleanup noise before a PR |
| `explore-repo` | Structured codebase exploration before planning or building |
| `vscode-review` | Open every changed file on the current branch in a new VS Code window — a `--diff` tab and a live-file tab per file. Use to review local Claude/Codex output before committing |
| `local-review` | Address inline `//r <thought>` review markers left in the working tree — apply the change and remove the marker, or rewrite as `//c <reply>` to push back. Pairs with `vscode-review` |
| `zoom-out` | Get a higher-level map of an unfamiliar area of code, using the language in CONTEXT.md |
| `improve-codebase-architecture` | Find deepening refactoring opportunities informed by CONTEXT.md and docs/adr/ |
| `spec-it` | Grill the user one question at a time to extract a complete implementation plan into context, update CONTEXT.md / ADRs as terms and decisions resolve, then ship the plan as a `spec/<slug>` PR off main with the plan as the description |
| `ubiquitous-language` | Drill-sergeant for the domain language. Reads/writes `language.md`, asks one DDD-loaded question at a time — surfacing missing behavior, false cognates, duplicate concepts, weak definitions — until the user explicitly stops |
| `work-forever` | Run in highly autonomous mode for long-running tasks |
| `subagent` | Delegate exploration to a non-interactive Codex exec run |
| `new-skill` | Create a new skill from conversation history |
| `youtube-extractor` | Extract transcripts, titles, and thumbnails from YouTube videos |
| `pdf-viewing` | OCR PDFs with page tracking and rasterize to images |
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
- **post_build hook:** Runs once at image-build time. Sets up isolated git config files, configures `http.proxyAuthMethod` for Moat's authenticated proxy, runs `npx playwright install chromium`, and warms the `@playwright/mcp` npx cache so the first MCP probe doesn't time out.
- **pre_run hook:** Runs on every container start. Clones this repo to `/tmp/setup-scripts`, runs `bootstrap_agent_homes.sh --moat` (which symlinks `skills/`, `AGENTS.md`, and the container settings file into `~/.claude` and `~/.codex`), copies `defaults/codex-moat-config.toml` to `~/.codex/config.toml`, and sets per-worktree `core.hooksPath` so the repo's hooks fire inside the container.
- **Env:** `IN_MOAT=1` flags the container so tooling (e.g., the `pr-screenshots` skill) can pick between headful and headless behavior.

Because the clone happens in `pre_run` (not `post_build`), every Moat session pulls the latest `main` of `setup_scripts` rather than whatever was current at image-build time — skill edits on the host show up in the next container start without rebuilding the image.

The `pre_run` hook also enables `extensions.worktreeConfig` before writing `core.hooksPath` with `git config --worktree`, so each Moat container's hook configuration is isolated and doesn't write to the shared git common directory across worktrees.

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
