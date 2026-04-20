"""Tests for agent home bootstrapping used by Moat hooks."""

import os
import subprocess


def run_bootstrap(repo_dir, home):
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(repo_dir / "scripts/bootstrap_agent_homes.sh"), str(repo_dir)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_bootstrap_links_each_codex_skill(repo_dir, tmp_path):
    home = tmp_path / "home"

    result = run_bootstrap(repo_dir, home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / ".codex/skills/gh-ship").is_symlink()
    assert (home / ".codex/skills/gh-ship/SKILL.md").exists()
    assert not (home / ".codex/skills/skills").exists()


def test_bootstrap_replaces_existing_codex_skills_symlink(repo_dir, tmp_path):
    home = tmp_path / "home"
    old_target = tmp_path / "old-skills"
    old_target.mkdir()
    (home / ".codex").mkdir(parents=True)
    (home / ".codex/skills").symlink_to(old_target)

    result = run_bootstrap(repo_dir, home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / ".codex/skills").is_dir()
    assert not (home / ".codex/skills").is_symlink()
    assert (home / ".codex/skills/gh-ship/SKILL.md").exists()
