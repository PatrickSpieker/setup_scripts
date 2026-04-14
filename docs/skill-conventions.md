# Skill Conventions

Canonical reference for authoring and maintaining skills in this repo.

## Directory Structure

Every skill lives at `skills/<skill-name>/` with at minimum a `SKILL.md`.

```
skills/<skill-name>/
  SKILL.md          # Required. Frontmatter + workflow.
  scripts/          # Optional. Executable tools the skill invokes.
  references/       # Optional. Reference material (docs, llms.txt files).
  resources/        # Optional. Bundled assets or sub-references.
```

## SKILL.md Format

```yaml
---
name: <skill-name>        # Required. Must match the directory name exactly.
description: <one-line>   # Required. Used in README table and CLI help.
---
```

After frontmatter: an H1 heading, then workflow sections (Steps, Checklist, Flow, etc.).

## Naming

- **kebab-case**, always.
- **Verb-first** for action skills: `gh-commit`, `make-tests`, `de-slop`.
- **Noun** for resource/tool skills: `subagent`, `pdf-viewing`.

## README Sync

When adding or removing a skill, update the Skills table in `README.md`.
The linter (`tests/test_skill_structure.py`) enforces parity between the
`skills/` directory and the README table on every commit.

## Linter

Structural checks run via `./test_runner.sh lint`. The linter enforces:

1. Every `skills/*/` directory contains a `SKILL.md`.
2. Each `SKILL.md` has `name` and `description` in YAML frontmatter.
3. The `name` field matches the parent directory name.
4. The README.md skills table matches `skills/` directories (both directions).
5. No stale `skills/README.txt` exists.

## Reference Skills

- **Minimal workflow:** `gh-commit` -- frontmatter + step-based flow.
- **With scripts:** `pdf-viewing` -- includes a `scripts/` directory.
- **With resources:** `subagent` -- includes a `resources/` directory.
