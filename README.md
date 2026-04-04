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
├── Brewfile                 # Homebrew packages (git, gh, neovim, ripgrep, fzf, claude-code, codex, etc.)
├── moat.yaml                # Moat sandbox config (grants, hooks for skills + pre-push)
├── AGENTS.md                # Agent-facing instructions for this repo
├── bashrc_main              # Bash config (aliases, git shortcuts, PATH, oh-my-bash, fzf)
├── bash_profile_main        # Bash profile (sources bashrc)
├── vimrc_main               # Neovim config (vim-plug, keymaps, plugins)
├── vscode_settings.json     # VS Code settings
├── obsidian_vimrc           # Obsidian vim keybindings
├── skills/                  # AI agent skills (Claude Code + Codex CLI)
│   ├── gh-commit/           #   Conventional commits
│   ├── gh-ship/             #   Commit + push + create PR
│   ├── gh-review-pr/        #   Thorough PR review
│   ├── gh-fix-ci/           #   Fix first failing CI check
│   ├── gh-address-pr-comments/ # Resolve PR review comments
│   ├── make-tests/          #   Generate tests for current changes
│   ├── design-doc/          #   Structured design documents
│   ├── de-slop/             #   Remove AI artifacts before PR
│   ├── work-forever/        #   Autonomous long-running mode
│   ├── subagent/            #   Delegate to Codex exec subagent
│   ├── new-skill/           #   Create a new skill
│   ├── new-cmd/             #   Create a new command
│   ├── delegate-cursor-background-task/ # Hand off work to Cursor agent
│   ├── youtube-extractor/   #   Extract YouTube transcripts + metadata
│   ├── pdf-viewing/         #   OCR and rasterize PDFs
│   └── slidev-presentation-kit/ # Create/edit Slidev presentations
├── hooks/
│   └── pre-push             # Git pre-push hook (installed by moat.yaml pre_run)
├── templates/
│   └── moat.yaml            # moat.yaml starter template (copied by moat-init)
└── swiftbar_plugins/
    └── ai_token_usage.1m.py # Menu bar token usage tracker (Claude + Codex)
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
| `make-tests` | Add tests for the change you're working on |
| `design-doc` | Format implementation plans as structured design documents |
| `de-slop` | Remove AI artifacts and cleanup noise before a PR |
| `work-forever` | Run in highly autonomous mode for long-running tasks |
| `subagent` | Delegate exploration to a non-interactive Codex exec run |
| `new-skill` | Create a new skill from conversation history |
| `new-cmd` | Create a new command from conversation history |
| `delegate-cursor-background-task` | Create a GitHub/Linear ticket for Cursor's background agent |
| `youtube-extractor` | Extract transcripts, titles, and thumbnails from YouTube videos |
| `pdf-viewing` | OCR PDFs with page tracking and rasterize to images |
| `slidev-presentation-kit` | Create or edit Slidev presentations |

### How skills are installed

- **Claude Code:** `setup.sh` symlinks `skills/` to `~/.claude/skills/`
- **Codex CLI:** `sync-skills` in `bashrc_main` symlinks each skill to `~/.codex/skills/` on every shell startup

## Moat Integration

[Moat](https://majorcontext.com/moat/llms.txt) runs Claude Code in an isolated sandbox. This repo provides both a ready-to-use config and helpers for bootstrapping new repos.

**`moat.yaml`** (root) — used when Moat runs *inside* this repo:
- Grants: `claude`, `github`, `ssh:github.com`
- `post_build` hook clones this repo and symlinks skills into `~/.claude/skills`
- `pre_run` hook installs the `pre-push` git hook, using `git rev-parse --git-dir` for worktree compatibility

**Shell functions** (in `bashrc_main`):

| Function | Purpose |
|----------|---------|
| `mcl [branch]` | Launch Moat + Claude Code in a git worktree. Defaults to `moat/YYYYMMDD-HHMMSS` branch. Runs `moat claude --worktree "$branch" -- --model=opus`. |
| `moat-init` | Copy `templates/moat.yaml` into the current directory so any repo can use Moat. |

**`templates/moat.yaml`** — a starter config for other repos, identical to the root config. Run `moat-init` in a repo, customize grants/hooks, then `mcl` to launch.

## Dotfiles

| File | Installs to | Notes |
|------|-------------|-------|
| `bashrc_main` | `~/.bashrc` | Aliases, git shortcuts, PATH, fzf config, oh-my-bash (purity theme) |
| `bash_profile_main` | `~/.bash_profile` | Sources bashrc |
| `vimrc_main` | `~/.config/nvim/init.vim` | vim-plug managed; run `:PlugInstall` after setup |
| `vscode_settings.json` | `~/Library/Application Support/Code/User/settings.json` | |
| `obsidian_vimrc` | (manual) | Vim keybindings for Obsidian |

## SwiftBar Plugin

`swiftbar_plugins/ai_token_usage.1m.py` shows a token usage leaderboard for Claude Code and Codex in the macOS menu bar. Installed by `setup.sh` via symlink to `~/.swiftbar/plugins/`.

## Shell Highlights

- `nvim` aliased as `vim`; `vi` left alone for git rebase compatibility
- `rm` routed to `trash` when available
- `noclobber` enabled
- fzf backed by ripgrep (`rg --files --hidden`)
- Git aliases: `gs` (status), `gc` (commit -am), `gacp` (add + commit + push), `gpoh` (push origin HEAD)
- `mcl [branch]` launches Claude Code via Moat in an isolated worktree (default branch: `moat/YYYYMMDD-HHMMSS`)
- `moat-init` copies a moat.yaml template into the current directory for quick Moat setup
