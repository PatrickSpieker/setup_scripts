"""
Structural linter for skills/.

Enforces mechanical invariants so skill conventions don't drift.
Error messages include remediation hints so agents (and humans)
know exactly how to fix failures.
"""

import re
from pathlib import Path

import yaml

REPO_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_DIR / "skills"
README_PATH = REPO_DIR / "README.md"


def _skill_dirs():
    """Return sorted list of skill directory names (excluding non-directories)."""
    return sorted(
        d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def _parse_frontmatter(skill_md_path):
    """Extract YAML frontmatter from a SKILL.md file."""
    text = skill_md_path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _readme_skill_names():
    """Extract skill names from the Skills table in README.md."""
    text = README_PATH.read_text()
    in_skills_section = False
    names = []
    for line in text.splitlines():
        if line.strip().startswith("## Skills"):
            in_skills_section = True
            continue
        if in_skills_section and line.startswith("## ") and "Skills" not in line:
            break
        if in_skills_section:
            match = re.match(r"\| `([^`]+)` \|", line)
            if match:
                names.append(match.group(1))
    return set(names)


# --- Tests ---


def test_every_skill_dir_has_skill_md():
    for name in _skill_dirs():
        skill_md = SKILLS_DIR / name / "SKILL.md"
        assert skill_md.exists(), (
            f"skills/{name}/ is missing SKILL.md. "
            f"Create one with at least name + description frontmatter. "
            f"See docs/skill-conventions.md."
        )


def test_skill_md_has_required_frontmatter():
    for name in _skill_dirs():
        skill_md = SKILLS_DIR / name / "SKILL.md"
        if not skill_md.exists():
            continue  # caught by test_every_skill_dir_has_skill_md
        fm = _parse_frontmatter(skill_md)
        for field in ("name", "description"):
            assert fm.get(field), (
                f"skills/{name}/SKILL.md is missing required frontmatter field '{field}'. "
                f"Required fields: name, description. See docs/skill-conventions.md."
            )


def test_skill_name_matches_directory():
    for name in _skill_dirs():
        skill_md = SKILLS_DIR / name / "SKILL.md"
        if not skill_md.exists():
            continue
        fm = _parse_frontmatter(skill_md)
        fm_name = fm.get("name", "")
        assert fm_name == name, (
            f"skills/{name}/SKILL.md has name '{fm_name}' but directory is '{name}'. "
            f"These must match. See docs/skill-conventions.md."
        )


def test_readme_skills_table_matches_disk():
    on_disk = set(_skill_dirs())
    in_readme = _readme_skill_names()

    missing_from_readme = on_disk - in_readme
    assert not missing_from_readme, (
        f"Skills on disk but missing from README.md table: {sorted(missing_from_readme)}. "
        f"Add a row to the Skills table in README.md for each."
    )

    missing_from_disk = in_readme - on_disk
    assert not missing_from_disk, (
        f"Skills in README.md table but missing from disk: {sorted(missing_from_disk)}. "
        f"Either create the skill directory or remove the README row."
    )


def test_no_stale_skills_readme():
    stale = SKILLS_DIR / "README.txt"
    assert not stale.exists(), (
        "skills/README.txt is stale. "
        "Skill documentation lives in each skill's SKILL.md "
        "and in docs/skill-conventions.md. Remove this file."
    )
