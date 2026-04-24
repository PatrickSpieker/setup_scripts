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


def test_moat_yaml_declares_playwright_via_shim():
    """Playwright MCP must launch via scripts/playwright-mcp.sh — the shim
    handles chromium path resolution, the local auth-injecting proxy that
    fronts Moat's authenticated HTTPS_PROXY, and the --config file with all
    container-safe launchOptions (headless, isolated, --no-sandbox,
    --ignore-certificate-errors). moat.yaml's args should be empty so the
    shim's config is the single source of truth."""
    moat = yaml.safe_load((REPO_DIR / "moat.yaml").read_text())
    pw = moat["claude"]["mcp"]["playwright"]
    assert pw["command"].endswith("/playwright-mcp.sh"), (
        "playwright MCP must launch via scripts/playwright-mcp.sh "
        "(see docstring in the script for why)"
    )
    assert pw.get("args", []) == [], (
        "moat.yaml playwright args should be empty — the shim builds an MCP "
        "--config JSON with everything needed; CLI args here only confuse."
    )


def test_template_moat_yaml_mirrors_root_playwright_wiring():
    """templates/moat.yaml gets copied into client repos by `mcl` and is the
    snapshot that other projects use. It must declare the same Playwright
    wiring as the root moat.yaml (shim path, empty args, post_build_root for
    install-deps, npx-warm in post_build) so containers spawned in other
    repos get a working Playwright MCP too. Drift here silently breaks
    clients that already have a snapshot."""
    template = yaml.safe_load((REPO_DIR / "templates/moat.yaml").read_text())
    pw = template["claude"]["mcp"]["playwright"]
    assert pw["command"].endswith("/playwright-mcp.sh")
    assert pw.get("args", []) == []
    hooks = template["hooks"]
    assert "install-deps chromium" in hooks["post_build_root"], (
        "templates/moat.yaml post_build_root must run `playwright install-deps "
        "chromium` (system libs need root)."
    )
    assert "@playwright/mcp@latest --help" in hooks["post_build"], (
        "templates/moat.yaml post_build must warm the @playwright/mcp npx "
        "cache so the first MCP probe doesn't time out."
    )


def test_template_moat_codex_yaml_has_playwright_wiring():
    """templates/moat-codex.yaml is the snapshot `mco` copies into Codex
    client repos. It must declare Playwright under codex.mcp (per Moat docs
    — Codex sandbox-local MCPs use codex.mcp, written to .mcp.json), and
    install system libs / chromium / warm the MCP cache the same way the
    Claude templates do."""
    template = yaml.safe_load((REPO_DIR / "templates/moat-codex.yaml").read_text())
    pw = template["codex"]["mcp"]["playwright"]
    assert pw["command"].endswith("/playwright-mcp.sh"), (
        "Codex Playwright MCP must launch via the shared shim — the shim "
        "handles chromium-path resolution and the auth-injecting proxy."
    )
    assert pw.get("args", []) == []
    hooks = template["hooks"]
    assert "install-deps chromium" in hooks["post_build_root"]
    assert "playwright@latest install chromium" in hooks["post_build"], (
        "post_build must download the bundled Chromium browser binary "
        "(separate from system libs in post_build_root)."
    )
    assert "@playwright/mcp@latest --help" in hooks["post_build"], (
        "post_build must warm the @playwright/mcp npx cache."
    )


def test_playwright_shim_includes_proxy_bridging():
    """The shim must spawn a local CONNECT proxy so Chromium can use Moat's
    authenticated HTTPS_PROXY (Chromium's --proxy-server doesn't accept
    inline basic auth). Catch regressions where someone simplifies the shim."""
    shim = (REPO_DIR / "scripts/playwright-mcp.sh").read_text()
    assert 'Proxy-Authorization' in shim, "shim must inject Proxy-Authorization to upstream"
    assert '127.0.0.1' in shim, "shim must point Chromium at a localhost proxy"
    assert '--ignore-certificate-errors' in shim, (
        "Moat's TLS-intercepting CA isn't in chromium's trust store; "
        "shim must pass --ignore-certificate-errors"
    )
    assert '--no-sandbox' in shim, "container has no sandbox; --no-sandbox required"


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
