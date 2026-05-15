"""Tests for agent home bootstrapping used by Moat hooks."""

import os
import subprocess


def run_bootstrap(repo_dir, home, *extra_args):
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(repo_dir / "scripts/bootstrap_agent_homes.sh"), str(repo_dir), *extra_args],
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


def test_bootstrap_links_host_settings_by_default(repo_dir, tmp_path):
    home = tmp_path / "home"

    result = run_bootstrap(repo_dir, home)

    assert result.returncode == 0, result.stdout + result.stderr
    link = home / ".claude/settings.json"
    assert link.is_symlink()
    assert os.readlink(link) == str(repo_dir / "defaults/settings.json")


def test_bootstrap_links_moat_settings_when_moat_flag_set(repo_dir, tmp_path):
    home = tmp_path / "home"

    result = run_bootstrap(repo_dir, home, "--moat")

    assert result.returncode == 0, result.stdout + result.stderr
    link = home / ".claude/settings.json"
    assert link.is_symlink()
    assert os.readlink(link) == str(repo_dir / "defaults/settings-moat.json")


def test_bootstrap_links_each_claude_agent(repo_dir, tmp_path):
    home = tmp_path / "home"

    result = run_bootstrap(repo_dir, home)

    assert result.returncode == 0, result.stdout + result.stderr
    # The agents/ dir itself should be a real directory, not a symlink —
    # mirrors the skills/ pattern so the dir survives re-bootstraps that
    # may need to swap individual agent symlinks.
    agents_dir = home / ".claude/agents"
    assert agents_dir.is_dir()
    assert not agents_dir.is_symlink()
    # Every .md file in the repo's agents/ should appear as a symlink.
    for agent in (repo_dir / "agents").glob("*.md"):
        link = agents_dir / agent.name
        assert link.is_symlink(), f"{link} should be a symlink"
        assert os.readlink(link) == str(agent)


def test_bootstrap_replaces_existing_claude_agents_symlink(repo_dir, tmp_path):
    home = tmp_path / "home"
    old_target = tmp_path / "old-agents"
    old_target.mkdir()
    (home / ".claude").mkdir(parents=True)
    (home / ".claude/agents").symlink_to(old_target)

    result = run_bootstrap(repo_dir, home)

    assert result.returncode == 0, result.stdout + result.stderr
    agents_dir = home / ".claude/agents"
    assert agents_dir.is_dir()
    assert not agents_dir.is_symlink()


def test_bootstrap_links_agents_md_globally(repo_dir, tmp_path):
    """AGENTS.md must be linked as user-scope global instructions for both
    Claude Code (~/.claude/CLAUDE.md) and Codex (~/.codex/AGENTS.md) inside
    the Moat container. Moat doesn't run bashrc, so this is the only path
    that wires global agent rules in containers."""
    home = tmp_path / "home"

    result = run_bootstrap(repo_dir, home)

    assert result.returncode == 0, result.stdout + result.stderr
    claude_link = home / ".claude/CLAUDE.md"
    codex_link = home / ".codex/AGENTS.md"
    assert claude_link.is_symlink()
    assert codex_link.is_symlink()
    assert os.readlink(claude_link) == str(repo_dir / "AGENTS.md")
    assert os.readlink(codex_link) == str(repo_dir / "AGENTS.md")
