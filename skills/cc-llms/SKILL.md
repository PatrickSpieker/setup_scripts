---
name: cc-llms
description: Load context on the Claude Developer Platform (Anthropic API, SDKs, Claude Code) from a bundled llms.txt reference. Use when building on the Anthropic API, configuring Claude Code, or looking up API behavior (models, tool use, caching, citations, batch, files, memory, compaction).
---

# Claude Developer Platform (cc-llms)

Load the parts of the Anthropic developer docs that are relevant to the current task. The bundled reference is large (~120KB) — **do not read it end-to-end**. Navigate it.

## Reference

- `references/cc-llms.txt` — single-file export of docs from platform.claude.com. Single H1 at the top; the real structure is H2/H3 within "## English".

## When to use

- Writing or debugging code against the Anthropic API / `anthropic` SDK
- Configuring Claude Code (settings.json, hooks, MCP servers, skills, slash commands)
- Looking up model IDs, pricing tiers, rate limits, or context window sizes
- Implementing prompt caching, extended thinking, tool use, batch, files API, citations, memory, or compaction
- Clarifying authentication, admin API, or workspace behavior

## Workflow

1. **Frame the question.** What API surface, feature, or product page is actually needed? One of: API reference, SDK guide, Claude Code feature, model spec, admin/billing.
2. **Grep before reading.** Search `references/cc-llms.txt` for the specific term (e.g., `prompt caching`, `tool_use`, `MCP`, `settings.json`, `claude-opus-4`, `batch`). Jump to the first few hits.
3. **Expand around hits.** Read ±30 lines of context for each match to capture the relevant section. Follow H2/H3 boundaries.
4. **Prefer examples.** The docs include JSON/code blocks — pull those into your working context rather than summarizing prose.
5. **Cross-check model IDs and version-specific behavior.** The reference may lag; verify model IDs against the system prompt (current: Opus 4.7, Sonnet 4.6, Haiku 4.5) before citing them.
6. **Surface a short summary** of the abstractions you loaded so the user knows what you're working from.

## Common grep anchors

- Models & pricing: `claude-opus`, `claude-sonnet`, `claude-haiku`, `context window`, `pricing`
- Caching / thinking: `prompt caching`, `cache_control`, `extended thinking`, `thinking budget`
- Tool use: `tool_use`, `tool_choice`, `input_schema`, `computer use`
- Claude Code: `settings.json`, `hooks`, `slash commands`, `MCP`, `subagents`, `skills`
- API surface: `messages`, `files`, `batches`, `admin`, `workspaces`, `rate limits`
