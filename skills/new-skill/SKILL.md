---
name: new-skill
description: Create a skill from conversation history or user description.
---

# New Skill

Create a skill from conversation history or user description.

## Setup

Skills live in `~/setup_scripts/skills/` (this repo). The entire `skills/` directory is
symlinked into each tool's config at install time:

- `~/.claude/skills` → `skills/`
- `~/.codex/skills` → `skills/`

So creating a skill here makes it available to all tools automatically — no per-host install needed.

## Steps

1. **Detect context**
   - If history exists: auto-capture workflow into skill
   - If no history: parse user's description
   - Use thread context clues to infer name, description, and triggers

2. Propose the skill name, description, triggers, and whether scripts are needed
   - Proceed unless user rejects or corrects

3. Check existing skills for patterns
```bash
ls skills/
```

4. Create skill in `skills/{skill-name}/`:
```
skills/{skill-name}/
  SKILL.md
  resources/         # references, samples, templates (only if needed)
  scripts/           # only if tools requested
    run.py|ts|sh
```

5. Write SKILL.md following existing conventions:
```markdown
---
name: skill-name
description: one-line description
---

# Skill Name

One-line description matching the frontmatter.

## Steps
1. ...
2. ...
```

Add `## When to use` only if triggers aren't obvious from the description.
Add `## Tools created` only if scripts/ are included.

6. Report created files

## Flags

`--interview`: Ask detailed questions (purpose, triggers, inputs, outputs, edge cases)

## Script Templates

**Python (uv):**
```python
def main() -> int:
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**TypeScript (bun):**
```typescript
console.log("ok");
```

**Shell:**
```bash
#!/usr/bin/env bash
set -euo pipefail
echo "ok"
```

## Rules

- Default to capturing conversation if history exists
- All skills go in `skills/` in this repo — never install directly into `~/.claude/skills/` etc.
- Ask at most one question, only if ambiguity blocks execution
- Only create scripts if requested
- Match existing skill patterns in the repo (check frontmatter, section style)
