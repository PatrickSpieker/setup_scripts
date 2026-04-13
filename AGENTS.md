## Goal

- Keep agent prompts and skills lean, reproducible, and context-aware.

## Repo

- This repo holds my dotfiles, shared agent prompts/skills, and install scripts for local tools.

Context for Moat can be found at: https://majorcontext.com/moat/llms.txt

## Moat

- When running inside Moat, prefer `gh` for all GitHub operations (creating PRs, pushing branches, fetching repo info) rather than `git push` / `git clone` over HTTPS or SSH. The `github` grant makes `gh` the most reliable transport — system-level git `insteadOf` rules can silently rewrite URLs and cause failures.
Context for Claude Code can be found at: https://platform.claude.com/llms.txt
Context for Codex can be found at: https://developers.openai.com/codex/llms.txt
