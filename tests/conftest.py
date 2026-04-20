"""
Shared test fixtures for bashrc_main tests.

Key design decision: we use REAL git repos (not mock git scripts) so tests
exercise actual git behavior. Only non-git externals (moat, gh, gem, bind)
are mocked. This avoids fragile bash-in-python mock scripts that have to
anticipate every git subcommand the function might call.
"""

import os
import shutil
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
    """Provides a temp bin directory and a helper to create mock executables.

    Used to mock non-git commands (moat, gh, gem, bind) that we can't or
    don't want to run for real in tests. Git is NOT mocked — we use real
    git repos instead.

    The mock_bin directory is prepended to PATH, so any executable created
    here takes precedence over system commands with the same name.

    Usage:
        mock_bin.create("moat")                    # no-op, exits 0
        mock_bin.create("gem", stdout="/fake/dir") # prints a string
        mock_bin.create("gh", script="...")         # custom bash script

    Assertions:
        mock_bin.assert_called_with("moat claude --worktree my-branch -- --model=opus")
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "mock_calls.log"

    def create_mock(name: str, exit_code: int = 0, stdout: str = "", script: str = ""):
        """Create a mock executable that logs its invocation to mock_calls.log."""
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
        # staticmethod prevents Python from binding create_mock as a method
        # (which would pass `self` as the first arg, breaking the signature).
        create = staticmethod(create_mock)

        def calls(self) -> str:
            return log_file.read_text() if log_file.exists() else ""

        def assert_called_with(self, pattern: str):
            calls = self.calls()
            assert pattern in calls, f"Expected {pattern!r} in mock calls:\n{calls}"

    return MockBin()


@pytest.fixture
def fake_home(tmp_path, repo_dir):
    """Create an isolated HOME with the structure bashrc_main expects.

    bashrc_main sources several files and references paths relative to HOME:
      - ~/setup_scripts/templates/moat.yaml  (template for moat-init)
      - ~/setup_scripts/skills/              (symlinked by sync-skills)
      - ~/.cargo/env                         (sourced at load time)
      - ~/.local/bin/env                     (sourced at load time)
      - ~/.codex/skills/                     (target for skill symlinks)

    We also write a minimal .gitconfig so real git commands work:
      - user.name/email: required for `git commit`
      - init.defaultBranch: pinned to "main" so tests are deterministic
        regardless of the system's git version or global config
    """
    home = tmp_path / "home"

    # Directories bashrc_main expects under HOME
    (home / "setup_scripts/skills/skill-a").mkdir(parents=True)
    (home / "setup_scripts/templates").mkdir(parents=True)
    shutil.copy(repo_dir / "templates/moat.yaml", home / "setup_scripts/templates/moat.yaml")
    shutil.copy(repo_dir / "templates/moat-codex.yaml", home / "setup_scripts/templates/moat-codex.yaml")
    (home / ".codex/skills").mkdir(parents=True)
    (home / ".claude/skills").mkdir(parents=True)
    (home / "code").mkdir(parents=True)

    # Dummy SSH key so _mcl_ensure_ssh_key finds it
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh/id_ed25519_moat").write_text("dummy-key-for-tests\n")

    # No-op files that bashrc_main sources on load
    (home / ".cargo").mkdir(parents=True)
    (home / ".cargo/env").write_text("")
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/env").write_text("")

    # Minimal git config so real git commands work in tests.
    # Without this, `git commit` fails (no user identity) and
    # `git init` may use "master" vs "main" depending on system defaults.
    (home / ".gitconfig").write_text(
        "[user]\n"
        "    name = Test User\n"
        "    email = test@example.com\n"
        "[init]\n"
        "    defaultBranch = main\n"
    )

    return home


def _run_git(cmd: str, cwd: Path, home: Path):
    """Run a git command in a subprocess with the fake HOME.

    Helper for fixture setup — keeps git isolated from the real user's
    config by pointing HOME at fake_home.
    """
    env = os.environ.copy()
    env["HOME"] = str(home)
    subprocess.run(
        ["bash", "-c", cmd],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        check=True,
    )


@pytest.fixture
def git_repo(tmp_path, fake_home):
    """Create a real git repo with one commit and no remote.

    This is the simplest repo setup. Use it for tests that don't need to
    fetch/pull from a remote (e.g., testing mcl in a local-only repo where
    the freshness check is skipped).

    The repo contains:
      - A single file (README.md) with one commit on "main"
      - A moat.yaml so mcl doesn't try to auto-create one

    Returns the path to the repo's working directory.
    """
    workdir = tmp_path / "project"
    workdir.mkdir()

    # Initialize repo and create an initial commit.
    # The commit gives us a HEAD ref, which mcl needs for worktree mode.
    _run_git("git init", workdir, fake_home)
    (workdir / "README.md").write_text("test repo\n")
    (workdir / "moat.yaml").write_text("runtime: apple\n")
    _run_git("git add -A && git commit -m 'initial commit'", workdir, fake_home)

    return workdir


@pytest.fixture
def git_repo_with_remote(tmp_path, fake_home):
    """Create a real git repo with a local bare repo acting as "origin".

    This sets up the full remote workflow so git fetch/pull/push work
    without any network access. The bare repo is just another directory
    on disk that git treats as a remote.

    Layout:
      tmp_path/
        origin.git/    <-- bare repo (acts as "origin")
        project/       <-- working repo (where tests run)

    The working repo has:
      - One commit on "main", pushed to origin
      - origin/main tracking ref (so the freshness check can find it)
      - A moat.yaml so mcl doesn't try to auto-create one

    Returns the path to the working repo directory.
    """
    origin = tmp_path / "origin.git"
    workdir = tmp_path / "project"
    workdir.mkdir()

    # Step 1: Create a bare repo to act as "origin".
    # A bare repo has no working directory — it's just the .git internals.
    # This is what GitHub/GitLab repos look like on the server side.
    _run_git(f"git init --bare {origin}", workdir, fake_home)

    # Step 2: Initialize the working repo and point it at our bare repo.
    _run_git("git init", workdir, fake_home)
    _run_git(f"git remote add origin {origin}", workdir, fake_home)

    # Step 3: Create an initial commit and push it to origin.
    # After this, both the local "main" and "origin/main" exist and match.
    (workdir / "README.md").write_text("test repo\n")
    (workdir / "moat.yaml").write_text("runtime: apple\n")
    _run_git("git add -A && git commit -m 'initial commit'", workdir, fake_home)
    _run_git("git push -u origin main", workdir, fake_home)

    return workdir


def run_bash_function(func_call: str, *, repo_dir: Path, mock_bin, fake_home: Path, cwd=None):
    """Source bashrc_main and run a shell function, with mocked externals.

    This is the main test harness. It:
      1. Sets HOME to fake_home (isolates git config, cargo, etc.)
      2. Puts mock_bin first on PATH (so mocked commands like `moat` are found)
      3. Keeps /usr/bin etc. on PATH (so real `git` is still available)
      4. Sources bashrc_main (which defines the functions under test)
      5. Runs the requested function call

    The 2>/dev/null on source suppresses noisy warnings from bashrc_main
    (e.g., oh-my-bash not found, ruby gems path issues) that don't affect
    the functions we're testing.
    """
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    # mock_bin first so mocked commands (moat, gh) shadow system ones,
    # but real git from /usr/bin is still reachable.
    env["PATH"] = f"{mock_bin.path}:/usr/bin:/bin:/usr/local/bin"

    # Re-prepend mock_bin AFTER sourcing so mocks aren't shadowed by
    # directories bashrc_main adds (e.g. /opt/homebrew/bin has real moat).
    cmd = f'source "{repo_dir}/bashrc_main" 2>/dev/null; export PATH="{mock_bin.path}:$PATH"; {func_call}'
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd or str(fake_home),
    )
