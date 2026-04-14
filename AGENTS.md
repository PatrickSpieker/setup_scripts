## Goal

- Keep agent prompts and skills lean, reproducible, and context-aware.

## Repo

- This repo holds my dotfiles, shared agent prompts/skills, and install scripts for local tools.

Context for Moat can be found at: https://majorcontext.com/moat/llms.txt

## Moat

- When running inside Moat, `git push` does not work (proxy blocks HTTPS git traffic, SSH is unavailable). Use `gh` for all GitHub operations: `gh pr create` for PRs, `gh api` for repo info, and `/tmp/setup-scripts/scripts/gh-push` to push commits. The `gh-push` script uploads commits via the GitHub REST API and preserves commit history. The `pre_run` hook automatically creates the branch ref on the remote before the agent starts.
Context for Claude Code can be found at: https://platform.claude.com/llms.txt
Context for Codex can be found at: https://developers.openai.com/codex/llms.txt
