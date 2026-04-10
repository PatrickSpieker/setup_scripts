import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_dir():
    return REPO_DIR


@pytest.fixture
def mock_bin(tmp_path):
    """Provides a temp bin directory and a helper to create mock commands."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "mock_calls.log"

    def create_mock(name: str, exit_code: int = 0, stdout: str = "", script: str = ""):
        """Create a mock executable that logs calls and returns canned output."""
        mock_path = bin_dir / name
        if script:
            body = script
        else:
            body = textwrap.dedent(f"""\
                #!/usr/bin/env bash
                echo "$0 $*" >> "{log_file}"
                {f'echo "{stdout}"' if stdout else ''}
                exit {exit_code}
            """)
        mock_path.write_text(body)
        mock_path.chmod(mock_path.stat().st_mode | stat.S_IEXEC)

    class MockBin:
        path = bin_dir
        log = log_file
        create = staticmethod(create_mock)

        def calls(self) -> str:
            return log_file.read_text() if log_file.exists() else ""

        def assert_called_with(self, pattern: str):
            calls = self.calls()
            assert pattern in calls, f"Expected {pattern!r} in mock calls:\n{calls}"

    return MockBin()


@pytest.fixture
def fake_home(tmp_path, repo_dir):
    """Create an isolated HOME with the structure bashrc_main expects."""
    home = tmp_path / "home"
    (home / "setup_scripts/skills/skill-a").mkdir(parents=True)
    (home / "setup_scripts/templates").mkdir(parents=True)
    # Copy the real template
    import shutil
    shutil.copy(repo_dir / "templates/moat.yaml", home / "setup_scripts/templates/moat.yaml")
    (home / ".codex/skills").mkdir(parents=True)
    (home / ".claude/skills").mkdir(parents=True)
    (home / "code").mkdir(parents=True)
    # No-op files that bashrc_main sources
    (home / ".cargo").mkdir(parents=True)
    (home / ".cargo/env").write_text("")
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/env").write_text("")
    return home


def run_bash_function(func_call: str, *, repo_dir: Path, mock_bin, fake_home: Path, cwd=None):
    """Source bashrc_main and run a function, with mocked externals."""
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{mock_bin.path}:/usr/bin:/bin:/usr/local/bin"

    cmd = f'source "{repo_dir}/bashrc_main" 2>/dev/null; {func_call}'
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd or str(fake_home),
    )
