## Goal

- Keep agent prompts and skills lean, reproducible, and context-aware.

## Repo

- This repo holds my dotfiles, shared agent prompts/skills, and install scripts for local tools.

Context for Moat can be found at: https://majorcontext.com/moat/llms.txt

## Moat

- When running inside Moat, `git push` and `git pull` use SSH transport (configured automatically by the `ssh:github.com` grant — no agent action needed). Use `gh` for GitHub API operations (creating PRs, viewing checks, fetching repo info). Do not attempt to switch remotes between SSH and HTTPS or configure git credentials manually.
Context for Claude Code can be found at: https://platform.claude.com/llms.txt
Context for Codex can be found at: https://developers.openai.com/codex/llms.txt
