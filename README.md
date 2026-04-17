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
├── AGENTS.md                # Agent-facing instructions (symlinked to .claude/claude.md)
├── moat.yaml                # Moat runtime config (grants, hooks for skills + pre-push)
├── bashrc_main              # Bash config (aliases, git shortcuts, PATH, oh-my-bash, fzf)
├── bash_profile_main        # Bash profile (sources bashrc)
├── vimrc_main               # Neovim config (vim-plug, keymaps, plugins)
├── vscode_settings.json     # VS Code settings
├── obsidian_vimrc           # Obsidian vim keybindings
├── hooks/
│   ├── pre-commit           # Runs test_runner.sh lint (repo-specific)
│   └── pre-push             # Blocks Claude Code from pushing to main/master (generic)
├── templates/
│   └── moat.yaml            # Template moat config for new projects
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
│   └── slidev-presentation-kit/ # Create/edit Slidev presentations
└── swiftbar_plugins/
    └── ai_token_usage.1m.py # Menu bar token usage tracker (Claude + Codex, 1-min refresh)
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
| `design-doc` | Format implementation plans as structured design documents |
| `de-slop` | Remove AI artifacts and cleanup noise before a PR |
| `explore-repo` | Structured codebase exploration before planning or building |
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

## Dotfiles

| File | Installs to | Notes |
|------|-------------|-------|
| `bashrc_main` | `~/.bashrc` | Aliases, git shortcuts, PATH, fzf config, oh-my-bash (purity theme) |
| `bash_profile_main` | `~/.bash_profile` | Sources bashrc |
| `vimrc_main` | `~/.config/nvim/init.vim` | vim-plug managed; run `:PlugInstall` after setup |
| `vscode_settings.json` | `~/Library/Application Support/Code/User/settings.json` | |
| `obsidian_vimrc` | (manual) | Vim keybindings for Obsidian |

## Moat

`moat.yaml` configures the [Moat](https://majorcontext.com/moat/llms.txt) sandbox runtime:

- **Grants:** `claude`, `github`, `ssh:github.com`
- **post_build hook:** Clones this repo and symlinks `skills/` to `~/.claude/skills/`
- **pre_run hook:** Sets `core.hooksPath` to point at `hooks/` from the cloned repo

The `pre_run` hook uses per-worktree git config (`extensions.worktreeConfig` + `git config --worktree`) so that each Moat container's hook configuration is isolated and doesn't write to the shared git common directory.

`templates/moat.yaml` is a starter config for new projects. It uses the same `hooksPath` approach, which means all hooks in `hooks/` are active — including `pre-commit`. Repos that don't have a `test_runner.sh` will need to add one or the pre-commit hook will block commits.

## Hooks

| Hook | Purpose | Scope |
|------|---------|-------|
| `hooks/pre-push` | Prevents Claude Code (`$CLAUDECODE=1`) from pushing to `main` or `master` | Generic — safe for all repos |
| `hooks/pre-commit` | Runs `test_runner.sh lint` on staged changes | Repo-specific — requires `test_runner.sh` at repo root |

## SwiftBar Plugin

`swiftbar_plugins/ai_token_usage.1m.py` shows a token usage leaderboard for Claude Code and Codex in the macOS menu bar (1-minute refresh). Installed by `setup.sh` via symlink to `~/.swiftbar/plugins/`.

## Shell Highlights

- `nvim` aliased as `vim`; `vi` left alone for git rebase compatibility
- `rm` routed to `trash` when available
- `noclobber` enabled
- fzf backed by ripgrep (`rg --files --hidden`)
- Git aliases: `gs` (status), `gc` (commit -am), `gacp` (add + commit + push), `gpoh` (push origin HEAD)
- Moat + Claude: `mcl` (new worktree session), `mclpr <pr>` (resume PR branch), `mclb <branch>` (resume any remote branch). Pass `-r`/`--rebuild` to any of these (and `mco`) to force rebuild of the container image.
- Docker: `sd` (open Docker), `sac` (start container system)
