"""Shellcheck linting and config file validation."""

import json
import re
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


def test_shellcheck_playwright_mcp():
    r = run_shellcheck(REPO_DIR / "scripts/playwright-mcp.sh")
    assert r.returncode == 0, r.stdout + r.stderr


def test_playwright_mcp_is_executable():
    """The MCP wrapper is invoked directly by Moat via `command:`, so it must
    have the execute bit set."""
    import os
    import stat
    mode = (REPO_DIR / "scripts/playwright-mcp.sh").stat().st_mode
    assert mode & stat.S_IXUSR, "scripts/playwright-mcp.sh is not executable"


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


def test_moat_yaml_declares_playwright_headless():
    """Playwright must be declared under claude.mcp in moat.yaml, with
    container-safe args (headless, no-sandbox, isolated), and launched via
    the shim that resolves the bundled chromium path."""
    moat = yaml.safe_load((REPO_DIR / "moat.yaml").read_text())
    pw = moat["claude"]["mcp"]["playwright"]
    assert pw["command"].endswith("/playwright-mcp.sh"), (
        "playwright MCP should launch via scripts/playwright-mcp.sh so "
        "--executable-path is injected; `npx @playwright/mcp` alone defaults "
        "to the Chrome channel which isn't installed in the container."
    )
    args = pw["args"]
    assert "--headless" in args
    assert "--no-sandbox" in args
    assert "--isolated" in args


def test_moat_yaml_installs_chromium_system_deps():
    """post_build_root must run `playwright install-deps chromium` so the
    bundled chromium finds libglib/libnss/etc. at runtime. post_build alone
    runs as moatuser (no root) and cannot install system packages."""
    for path in (REPO_DIR / "moat.yaml", REPO_DIR / "templates/moat.yaml"):
        moat = yaml.safe_load(path.read_text())
        hooks = moat.get("hooks", {})
        post_build = hooks.get("post_build", "")
        # Only enforce deps install where chromium is being installed.
        if "playwright@latest install chromium" not in post_build:
            continue
        post_build_root = hooks.get("post_build_root", "")
        assert "install-deps chromium" in post_build_root, (
            f"{path} installs chromium in post_build but is missing a "
            "post_build_root that runs `playwright install-deps chromium`. "
            "Without the system libs (libglib-2.0.so.0 etc.), the browser "
            "fails to launch with 'cannot open shared object file'."
        )


def test_host_settings_playwright_is_headful():
    """Host Playwright stays headful so the user can watch the browser."""
    host = load_json(REPO_DIR / "defaults/settings.json")
    assert "--headless" not in host["mcpServers"]["playwright"]["args"]


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


def test_invalid_json_rejected():
    with pytest.raises(json.JSONDecodeError):
        json.loads('{"missing": value}')
