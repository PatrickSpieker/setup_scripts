---
name: linear-llms
description: Load context on Linear (issues, projects, cycles, GraphQL API, TypeScript SDK, agents) from a bundled llms.txt reference. Use when working with the Linear API/SDK, writing Linear MCP queries, modeling issues/projects/cycles, or integrating automations.
---

# Linear (linear-llms)

Linear's llms.txt is an **index of links**, not the full content. Use it to find the right doc page, then fetch that page for details.

## Reference

- `references/linear-llms.txt` — ~9KB index. Each bullet is `[Page Name](https://linear.app/docs/<slug>.md)`. Appending `.md` to any Linear docs URL returns the markdown source.

## When to use

- Querying the Linear GraphQL API or using the TypeScript SDK
- Using the Linear MCP server from Claude Code / Codex (already configured in this repo's `defaults/codex-moat-config.toml` and `.claude/settings.json`)
- Modeling Linear concepts in code (Issues, Projects, Cycles, Initiatives, Teams, Views, Labels, Workflow States)
- Setting up integrations, webhooks, or agents
- Automating with OAuth, API keys, or agent authentication

## Workflow

1. **Identify the concept.** Map the task to a Linear section: Getting started, Issues, Projects, Initiatives, Cycles, Views, Integrations, GraphQL API, TypeScript SDK, Agents, Authentication.
2. **Find the page in the index.** Grep `references/linear-llms.txt` for the keyword — you'll get a URL.
3. **Fetch the page.** Use WebFetch on the `.md` URL from the index to get the actual content. The index itself holds no detail beyond titles.
4. **For API/SDK work**, prioritize these entry points from the index:
   - `### GraphQL API` — schema, queries, mutations
   - `### TypeScript SDK` — client usage
   - `### Authentication` — API keys, OAuth, personal vs. agent auth
   - `### Agents` — agent accounts and webhook patterns
5. **Summarize the abstractions** you loaded (entity names, required fields, auth model) before generating code.

## Index sections (for orientation)

Getting started · Account · Your sidebar · Teams · Issues · Issue properties · Projects · Initiatives · Cycles · Views · Find and filter · AI · Integrations · Analytics · Administration · GraphQL Schema · GraphQL API · Authentication · Agents · TypeScript SDK · Guides

## Note

If the Linear MCP server is available in the session, prefer MCP tool calls over GraphQL for read/write operations — faster and already authenticated.
