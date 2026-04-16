## Goal

- Keep agent prompts and skills lean, reproducible, and context-aware.

## Repo

- This repo holds my dotfiles, shared agent prompts/skills, and install scripts for local tools.

Context for Moat can be found at: https://majorcontext.com/moat/llms.txt

## Moat

- When running inside Moat, `git push` and `git pull` use SSH transport (configured automatically by the `ssh:github.com` grant — no agent action needed). Use `gh` for GitHub API operations (creating PRs, viewing checks, fetching repo info). Do not attempt to switch remotes between SSH and HTTPS or configure git credentials manually.
- **If `git push` fails with `Permission denied (publickey)`**: the SSH agent proxy has no keys. This is a host-side issue — the user's SSH agent didn't have GitHub keys loaded when Moat started. **Stop immediately** and tell the user to run `ssh-add` on their host machine and restart the Moat run. Do not attempt workarounds (switching to HTTPS, unsetting `insteadOf` rules, pushing via the GitHub API) — they will all fail because the system git config rewrites HTTPS→SSH and the network proxy blocks direct HTTPS to github.com.
Context for Claude Code can be found at: https://platform.claude.com/llms.txt
Context for Codex can be found at: https://developers.openai.com/codex/llms.txt
