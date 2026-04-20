---
name: moat-llms-full
description: Load context on Moat (container runtime for AI agents — Claude Code, Codex) from a bundled llms.txt reference. Use when authoring moat.yaml, debugging runs, configuring grants/hooks/runtimes, or understanding credential injection and the TLS proxy.
---

# Moat — Full Docs (moat-llms-full)

Load the Moat abstractions relevant to the current task. Reference is ~341KB, organized into four ## sections. **Do not read linearly** — jump to the section that matches the task.

## Reference

- `references/moat-llms-full.txt` — single-file export from majorcontext.com/moat. Top-level structure:
  - `## Getting Started` — install, first run, quickstart
  - `## Concepts` — runs, grants, credential injection, proxy, runtimes, worktrees
  - `## Guides` — task-oriented how-tos
  - `## Reference` — moat.yaml schema, CLI commands, flags

## When to use

- Editing `moat.yaml` (this repo, `templates/moat.yaml`, `templates/moat-codex.yaml`, or project configs)
- Debugging a Moat run (credential errors, SSH key issues, grant failures, network proxy behavior)
- Understanding grants (`claude`, `openai`, `github`, `ssh:github.com`) and how credentials are injected
- Configuring `pre_run` / `post_build` hooks, worktree mode, custom runtimes
- Interpreting `moat list`, `moat wt`, `moat logs`, `moat run` output
- Working on the `mcl` / `mco` / `mclpr` / `mclb` bash functions in `bashrc_main`

## Workflow

1. **Classify.** Is this a config question (→ Reference), a concept question (→ Concepts), or a workflow question (→ Guides)?
2. **Grep by term.** Search `references/moat-llms-full.txt` for the exact concept (e.g., `grants:`, `pre_run`, `runtime:`, `ssh:github.com`, `--worktree`, `TLS proxy`, `audit log`).
3. **Read within section.** Follow the matching `## ... ### ...` tree; each section is self-contained.
4. **Cross-check live configs.** `moat.yaml`, `templates/moat.yaml`, `templates/moat-codex.yaml`, and `scripts/bootstrap_agent_homes.sh` in this repo are working examples — reconcile any divergence before editing.
5. **Respect this repo's memory.** `feedback_moat_patterns.md` flags: don't add unnecessary fields; Moat handles mounts and output capture. Keep configs lean.
6. **Summarize what you loaded** before editing.

## Common grep anchors

- Config schema: `runtime:`, `dependencies:`, `grants:`, `env:`, `hooks:`, `post_build`, `pre_run`, `mounts`
- Grants: `claude`, `openai`, `github`, `ssh:github.com`, `anthropic`
- CLI: `moat claude`, `moat codex`, `moat list`, `moat wt`, `moat run`, `moat logs`, `--worktree`, `--rebuild`, `--full-auto`
- Internals: `TLS-intercepting proxy`, `credential injection`, `audit log`, `HTTP traces`
- Runtimes: `runtime: apple`, `runtime: docker`

## Related

- Repo-specific memory: see `reference_moat_hooks.md`, `feedback_moat_patterns.md`, `feedback_moat_plugins.md` in the auto-memory for constraints not captured in the docs.
