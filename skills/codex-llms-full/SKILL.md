---
name: codex-llms-full
description: Load context on OpenAI Codex (CLI, IDE extension, cloud, SDK) from a bundled llms.txt reference. Use when configuring or scripting Codex, tuning approvals/sandboxing, authoring codex.toml, writing prompts for `codex exec`, or integrating the Codex SDK.
---

# Codex — Full Docs (codex-llms-full)

Load the Codex abstractions relevant to the current task. The reference is ~707KB with 482 H1 pages — **do not read linearly**. Navigate it.

## Reference

- `references/codex-llms-full.txt` — single-file export from developers.openai.com/codex. Each `# ` at column 0 is a new doc page.

## When to use

- Writing or debugging `codex exec` / `codex e` invocations (flags, models, sandboxing)
- Authoring `~/.codex/config.toml` or workspace `codex.toml` (approval policy, sandbox mode, MCP servers, profiles, trust levels)
- Understanding approvals, sandbox modes (`read-only`, `workspace-write`, `danger-full-access`), network policy
- Integrating the Codex SDK or App Server
- Using Codex cloud, IDE extension, or computer use
- Interpreting `codex` errors, session/resume semantics, worktree behavior

## Workflow

1. **Classify the task.** Which surface: CLI, IDE, cloud, SDK, config, sandboxing/approvals, app server?
2. **Grep by keyword.** Search `references/codex-llms-full.txt` for the exact feature/flag (e.g., `approval_policy`, `sandbox_mode`, `--full-auto`, `codex exec resume`, `trust_level`, `mcp_servers`).
3. **Locate the page.** Match against the H1 list — pages like `# Codex CLI`, `# Codex App Server`, `# Authentication`, `# Worktrees`, `# Agent approvals & security`, `# Local environments`.
4. **Extract abstractions.** Pull config keys, default values, flag semantics, and example TOML/JSON blocks into context. Skip marketing prose.
5. **Cross-check against the repo.** `defaults/codex-moat-config.toml` in this repo is a live example; reconcile any divergence with docs before editing.
6. **Summarize what you loaded** before acting.

## Common grep anchors

- Config/TOML: `approval_policy`, `sandbox_mode`, `model =`, `model_reasoning_effort`, `[projects.`, `trust_level`, `[mcp_servers.`, `profiles`
- CLI flags: `--full-auto`, `--yolo`, `--skip-git-repo-check`, `--cd`, `-i`, `--image`, `--model`, `--search`
- Sandboxing: `workspace-write`, `read-only`, `danger-full-access`, `network access`, `sandbox_private_desktop`
- Exec workflow: `codex exec`, `codex exec resume`, `session id`, `--json`
- Surfaces: `# Codex CLI`, `# Codex App Server`, `# Codex app commands`, `# Worktrees`, `# In-app browser`, `# Computer Use`, `# Authentication`
