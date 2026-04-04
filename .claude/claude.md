## Goal

- Keep agent prompts and skills lean, reproducible, and context-aware.

## Repo

- This repo holds my dotfiles, shared agent prompts/skills, and install scripts for local tools.

## Key Patterns

- `moat.yaml` at repo root configures the Moat sandbox (grants, build/run hooks). `templates/moat.yaml` is a starter copy for other repos.
- `mcl [branch]` (in `bashrc_main`) launches Claude Code via Moat in a worktree. `moat-init` copies the template config into cwd.
- `hooks/pre-push` is installed dynamically by the moat.yaml `pre_run` hook into each worktree's git directory.

Context for Moat can be found at: https://majorcontext.com/moat/llms.txt
Context for Claude Code can be found at: https://platform.claude.com/llms.txt
Context for Codex can be found at: https://developers.openai.com/codex/llms.txt
