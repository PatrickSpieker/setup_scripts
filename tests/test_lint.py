"""Shellcheck linting and config file validation."""

import json
import re
import shutil
import subprocess
import tomllib

import pytest
import yaml

from conftest import REPO_DIR

SHELLCHECK = "shellcheck"


# ===== Shellcheck =====

def run_shellcheck(path, exclude=None):
    cmd = [SHELLCHECK, str(path)]
    if exclude:
        cmd.extend(["--exclude", ",".join(exclude)])
    return subprocess.run(cmd, capture_output=True, text=True)


def test_shellcheck_pre_push():
    r = run_shellcheck(REPO_DIR / "hooks/pre-push")
    assert r.returncode == 0, r.stdout + r.stderr


def test_shellcheck_bashrc_main():
    # SC2034: oh-my-bash vars consumed by sourced framework
    # SC1091: external sources not available in test
    # SC2155: gem PATH line — intentional one-liner
    r = run_shellcheck(REPO_DIR / "bashrc_main", exclude=["SC2034", "SC1091", "SC2155"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_shellcheck_setup():
    # SC1090: non-constant source (~/.bash_profile)
    r = run_shellcheck(REPO_DIR / "setup.sh", exclude=["SC1090"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_shellcheck_bootstrap_agent_homes():
    r = run_shellcheck(REPO_DIR / "scripts/bootstrap_agent_homes.sh")
    assert r.returncode == 0, r.stdout + r.stderr


def test_hammerspoon_init_lua_valid():
    luac = shutil.which("luac")
    if not luac:
        pytest.skip("luac not installed (brew install lua)")
    r = subprocess.run(
        [luac, "-p", str(REPO_DIR / "hammerspoon/init.lua")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# ===== Config validation =====

def load_json(path):
    """Load JSON, stripping trailing commas for JSONC support."""
    text = path.read_text()
    cleaned = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(cleaned)


def test_settings_json_valid():
    load_json(REPO_DIR / "defaults/settings.json")


def test_settings_moat_json_valid():
    load_json(REPO_DIR / "defaults/settings-moat.json")


def test_settings_moat_has_no_mcp_servers():
    """Container-scoped settings must not declare mcpServers.

    Moat generates its own ~/.claude.json with MCP entries from moat.yaml's
    top-level `mcp:` and agent-scoped `claude.mcp:`. Declaring mcpServers in
    ~/.claude/settings.json is ignored and only creates confusion.
    """
    moat = load_json(REPO_DIR / "defaults/settings-moat.json")
    assert "mcpServers" not in moat


def test_settings_json_has_no_mcp_servers():
    """User-scope Claude Code MCPs live in ~/.claude.json (top-level
    `mcpServers`), written by `claude mcp add --scope user`. The
    `mcpServers` block in ~/.claude/settings.json is silently ignored by
    current Claude Code, so declaring it here is dead config that misleads
    readers into thinking host MCPs are wired up."""
    host = load_json(REPO_DIR / "defaults/settings.json")
    assert "mcpServers" not in host, (
        "Remove `mcpServers` from defaults/settings.json — it is not read by "
        "Claude Code. Register user-scope MCPs via `claude mcp add --scope "
        "user` (encoded in setup.sh) instead."
    )


def test_vscode_settings_jsonc_valid():
    load_json(REPO_DIR / "vscode_settings.json")


def test_moat_yaml_valid():
    yaml.safe_load((REPO_DIR / "moat.yaml").read_text())


def test_templates_moat_yaml_valid():
    yaml.safe_load((REPO_DIR / "templates/moat.yaml").read_text())


def test_templates_moat_codex_yaml_valid():
    yaml.safe_load((REPO_DIR / "templates/moat-codex.yaml").read_text())


def test_codex_moat_config_toml_valid():
    config = tomllib.loads((REPO_DIR / "defaults/codex-moat-config.toml").read_text())
    assert config["model"] == "gpt-5.4"
    assert config["approval_policy"] == "never"
    assert config["sandbox_mode"] == "danger-full-access"
    assert config["projects"]["/workspace"]["trust_level"] == "trusted"


@pytest.mark.parametrize("path", [
    "setup.sh", "moat.yaml", "templates/moat.yaml", "templates/moat-codex.yaml",
    "defaults/codex-config.toml", "defaults/codex-moat-config.toml",
])
def test_bootstrap_does_not_restore_removed_browser_stack(path):
    assert "playwright" not in (REPO_DIR / path).read_text().lower()


def test_web_screenshots_use_chrome_computer_use():
    skill = (REPO_DIR / "skills/pr-screenshots/SKILL.md").read_text()
    assert "Chrome computer use" in skill
    assert "playwright" not in skill.lower()
