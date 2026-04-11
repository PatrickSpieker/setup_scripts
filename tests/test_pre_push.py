"""Tests for the pre-push git hook."""

import os
import subprocess

from conftest import REPO_DIR

HOOK = str(REPO_DIR / "hooks/pre-push")


def run_hook(stdin: str, claudecode: bool = False):
    env = os.environ.copy()
    if claudecode:
        env["CLAUDECODE"] = "1"
    else:
        env.pop("CLAUDECODE", None)
    return subprocess.run(
        ["bash", HOOK],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def test_allows_push_when_claudecode_unset():
    r = run_hook("refs/heads/foo abc123 refs/heads/main def456")
    assert r.returncode == 0


def test_blocks_claude_push_to_main():
    r = run_hook("refs/heads/foo abc123 refs/heads/main def456", claudecode=True)
    assert r.returncode == 1
    assert "blocked" in r.stdout.lower() or "blocked" in r.stderr.lower()


def test_blocks_claude_push_to_master():
    r = run_hook("refs/heads/foo abc123 refs/heads/master def456", claudecode=True)
    assert r.returncode == 1
    assert "blocked" in r.stdout.lower() or "blocked" in r.stderr.lower()


def test_allows_claude_push_to_feature_branch():
    r = run_hook("refs/heads/foo abc123 refs/heads/feature/bar def456", claudecode=True)
    assert r.returncode == 0


def test_allows_claude_push_when_no_main_refs():
    r = run_hook("refs/heads/foo abc123 refs/heads/dev def456", claudecode=True)
    assert r.returncode == 0
