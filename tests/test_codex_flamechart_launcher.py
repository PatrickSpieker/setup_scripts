"""Exercise first-use setup, retries, and shell argument forwarding offline."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "flamechart_launcher", REPO / "skills/codex-flamechart/scripts/run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CODEX_FLAMECHART_PYTHON", raising=False)
    monkeypatch.setattr(sys, "argv", ["run.py", "codex://threads/example", "--open"])
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1:3] == ["-m", "venv"]:
            python = Path(command[3]) / "bin/python"
            python.parent.mkdir(parents=True)
            python.touch()

    monkeypatch.setattr(module.subprocess, "run", run)
    monkeypatch.setattr(module.os, "execv", lambda *args: calls.append(args))
    return module, calls, tmp_path / ".local/share/codex-flamechart/venv"


def test_first_use_cached_use_and_lock_refresh(launcher):
    module, calls, environment = launcher
    module.main()
    assert calls[0][1:3] == ["-m", "venv"]
    assert calls[1][1:4] == ["-m", "pip", "install"]
    assert calls[2][1][-2:] == ["codex://threads/example", "--open"]
    calls.clear()
    module.main()
    assert len(calls) == 1  # Cached execution makes no installer calls.
    (environment / ".requirements.sha256").write_text("outdated")
    calls.clear()
    module.main()
    assert calls[0][1:4] == ["-m", "pip", "install"]


def test_failed_install_is_retried(launcher, monkeypatch):
    module, calls, environment = launcher
    original = module.subprocess.run

    def fail_install(command, **kwargs):
        if "pip" in command:
            raise subprocess.CalledProcessError(1, command)
        original(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", fail_install)
    assert module.main() == 1
    assert not (environment / ".requirements.sha256").exists()
    monkeypatch.setattr(module.subprocess, "run", original)
    calls.clear()
    module.main()
    assert calls[0][1:4] == ["-m", "pip", "install"]


def test_custom_python_and_help_skip_setup(launcher, monkeypatch, tmp_path):
    module, calls, _ = launcher
    python = tmp_path / "custom python"
    python.touch()
    monkeypatch.setenv("CODEX_FLAMECHART_PYTHON", str(python))
    module.main()
    assert len(calls) == 1
    assert calls[0][0] == str(python)
    calls.clear()
    monkeypatch.setattr(sys, "argv", ["run.py", "--help", "--open"])
    module.main()
    assert len(calls) == 1
    assert calls[0][0] == sys.executable


def test_shell_command_from_another_directory(tmp_path):
    source = (REPO / "bashrc_main").read_text()
    function = source.split("codex-flamechart() {", 1)[1].split("\n}", 1)[0]
    result = subprocess.run(
        [
            "bash",
            "-c",
            'python3() { printf "%s\\n" "$@"; }; '
            + "codex-flamechart() {"
            + function
            + '\n}; codex-flamechart "codex://threads/example" --output "report with spaces.html"',
        ],
        cwd=tmp_path,
        env={"HOME": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        str(tmp_path / "setup_scripts/skills/codex-flamechart/scripts/run.py"),
        "codex://threads/example",
        "--output",
        "report with spaces.html",
        "--open",
    ]
