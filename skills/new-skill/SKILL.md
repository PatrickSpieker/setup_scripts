---
name: new-skill
description: Create a skill from conversation history or user description.
---

# New Skill

Create a skill from conversation history or user description.

## Skill locations

There are two places a skill can live:

- **Global**: `~/.claude/skills/` (symlinked to `~/setup_scripts/skills/`, this repo).
  Available in every project. Create here when the skill is general-purpose.
- **Per-repo**: `<project>/.claude/skills/`. Checked into a specific project.
  Create here when the skill is project-specific.

If both locations have a skill with the same name, the global one wins.

## Steps

1. **Detect context**
   - If history exists: auto-capture workflow into skill
   - If no history: parse user's description
   - Use thread context clues to infer name, description, and triggers

2. **Determine destination**: global (default) or per-repo
   - If the skill is project-specific, use `.claude/skills/` in the current project
   - Otherwise, use `~/setup_scripts/skills/` (the global symlink target)

3. Propose the skill name, description, triggers, and whether scripts are needed
   - Proceed unless user rejects or corrects

4. Check existing skills for patterns
```bash
ls ~/.claude/skills/        # global
ls .claude/skills/ 2>/dev/null  # per-repo
```

5. Create skill in the chosen location:
```
skills/{skill-name}/
  SKILL.md
  resources/         # references, samples, templates (only if needed)
  scripts/           # only if tools requested
    run.py|ts|sh
```

6. Write SKILL.md following existing conventions:
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

7. Report created files

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
- Global skills go in `~/setup_scripts/skills/`; per-repo skills go in `<project>/.claude/skills/`
- Ask at most one question, only if ambiguity blocks execution
- Only create scripts if requested
- Match existing skill patterns in the repo (check frontmatter, section style)
