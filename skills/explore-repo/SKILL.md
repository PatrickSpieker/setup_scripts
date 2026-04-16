---
name: explore-repo
description: Perform a structured codebase exploration to build deep understanding before planning or building.
---

# Explore Repo

Perform a live, structured exploration of a codebase to build deep understanding before planning or building.

## Philosophy

- Every exploration is **live discovery**. Do not rely on cached summaries or stale documentation. Read the actual code — it changes faster than docs can keep up.
- Think like a **staff engineer onboarding** to a new codebase: curious, thorough, methodical. Ask open-ended questions about architecture, trade-offs, and the "why" behind decisions — not just "what files exist."
- The goal is to **fill the context window with relevant, high-quality information** so that subsequent planning has everything it needs. You are not building anything yet.

## When to use

- New to a codebase and need to understand it before making changes
- Need to understand a specific subsystem before planning a feature
- Onboarding to a project and want to build context quickly
- Need to find existing patterns, conventions, or prior art before planning work
- User asks to "explore," "understand," "investigate," or "learn" a repo or part of one

## Steps

Report findings to the user at each phase before moving on. Be explicit about what you found and what questions remain open.

### Phase 1: Orientation — Project Structure and Stack

**Goal:** Understand the shape of the project at a high level.

1. Read the top-level directory structure (1-2 levels deep)
2. Read the root README if it exists — treat it as potentially stale; verify claims against actual code
3. Identify language, framework, and key dependencies from `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or equivalent
4. Read any agent instruction files (`AGENTS.md`, `claude.md`, `.cursorrules`) and follow relevant guidance
5. Identify test framework and structure (`test/`, `tests/`, `__tests__/`, `*_test.go`, `*.spec.ts`, etc.)
6. Identify CI/CD configuration (`.github/workflows/`, `Makefile`, `Dockerfile`)
7. Identify linter/formatter configuration (`.eslintrc`, `ruff.toml`, `prettier`, pre-commit hooks)

**Report:** Concise summary of tech stack, directory layout, and infrastructure. Flag anything surprising.

### Phase 2: Architecture — Systems, Boundaries, and Data Flow

**Goal:** Understand how the major systems relate to each other.

1. Identify main entry points (server startup, CLI entry, main function, route definitions)
2. Trace request/data flow from entry point through major layers (routes → handlers → services → data access)
3. Identify data layer: ORM, database client, data access patterns. Note if multiple patterns exist — a codebase often has 2-3, with only one preferred.
4. Identify key abstractions and interfaces: core types, interfaces, or base classes the rest of the code builds on
5. Look for service/module boundary patterns — how code is organized into domains or features
6. Check for external API integrations, message queues, caches, or other infrastructure dependencies

**Report:** Architecture summary. Generate an ASCII or Mermaid diagram of major components and relationships — diagrams are high-value here. Ask the user to verify.

### Phase 3: Patterns and Conventions

**Goal:** Understand how the team writes code so future work follows existing conventions.

1. Find 2-3 "golden examples" — files that represent preferred patterns for common tasks (well-structured service, clean test, good API handler). Prefer files that are well-tested and recently modified.
2. Identify database access pattern(s) in use and which appears preferred
3. Identify error handling pattern (custom error types? try/catch? Result types?)
4. Identify testing patterns: typical test structure, utilities, fixtures, factories, mocking strategy
5. Check for shared utilities, helpers, or common abstractions that new code should reuse
6. Note code style conventions beyond linter rules (naming, file organization, import ordering)

**Report:** Key patterns with file paths to examples. Call out cases where multiple patterns exist so the user can clarify which is preferred.

### Phase 4: Problem-Specific Deep Dive (if a task is known)

**Goal:** If the user has a specific task, build targeted understanding of the relevant subsystem.

1. Find the most relevant directory and files for the task
2. Look for **similar implementations** — has the codebase already solved a problem like this?
3. Identify specific types, interfaces, and functions that will need to be touched or extended
4. Research unfamiliar technologies or libraries found in the relevant area
5. Evaluate approaches: What is the **simple way**? The **robust way**? Trade-offs?
6. Identify files a subsequent plan should reference

**Report:** Targeted findings with file paths, prior art, and approach trade-offs.

## Output Format

At the end of exploration, produce a structured summary for use as planning input:

```markdown
## Exploration Summary

### Tech Stack
- Language: ...
- Framework: ...
- Key Dependencies: ...
- Test Framework: ...
- Database / Data Layer: ...
- CI/CD: ...

### Architecture Diagram
(ASCII or Mermaid diagram of major components)

### Key Patterns
- **Pattern Name**: Brief description → `path/to/example.ts`

### Conventions to Follow
- (Specific conventions observed in the code)

### Relevant Files for [Task]
- `path/to/file.ts` — why it's relevant

### Similar Prior Art
- (Similar implementations in the codebase)

### Open Questions
- (Anything that needs human input)
```

## Rules

1. **Never skip exploration to jump to building.** Skipping leads to code that fights existing patterns, reinvents utilities, or gets the architecture wrong.
2. **Every exploration is fresh.** Do not assume cached summaries are current. If the README says one thing and the code says another, the code wins.
3. **Do not change any files.** Read, do not write. You may run existing tests or build commands to test understanding, but do not edit source files.
4. **Flag uncertainty and ask questions.** If multiple patterns exist and you don't know which is preferred, say so. Unexpressed uncertainty is the enemy.
5. **Prefer pointing over caching.** Give file paths the agent can read later rather than pasting large code blocks. The summary is a map, not a copy of the territory.
6. **Use diagrams.** ASCII and Mermaid diagrams are high-value for communicating architecture. Generate them and ask the user to verify.
