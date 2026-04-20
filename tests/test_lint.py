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


# ===== Config validation =====

def load_json(path):
    """Load JSON, stripping trailing commas for JSONC support."""
    text = path.read_text()
    cleaned = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(cleaned)


def test_settings_json_valid():
    load_json(REPO_DIR / "defaults/settings.json")


def test_vscode_settings_jsonc_valid():
    load_json(REPO_DIR / "vscode_settings.json")


def test_moat_yaml_valid():
    yaml.safe_load((REPO_DIR / "moat.yaml").read_text())


def test_templates_moat_yaml_valid():
    yaml.safe_load((REPO_DIR / "templates/moat.yaml").read_text())


def test_templates_moat_codex_yaml_valid():
    yaml.safe_load((REPO_DIR / "templates/moat-codex.yaml").read_text())


def test_codex_moat_config_toml_valid():
    tomllib.loads((REPO_DIR / "defaults/codex-moat-config.toml").read_text())


def test_invalid_json_rejected():
    with pytest.raises(json.JSONDecodeError):
        json.loads('{"missing": value}')
