"""Tests for xcode-proxy/server.py."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

# Make the xcode-proxy module importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "xcode-proxy"))

import server  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_simulators():
    """Reset the SIMULATORS dict between tests."""
    server.SIMULATORS.clear()
    yield
    server.SIMULATORS.clear()


@pytest.fixture
def fake_home(tmp_path):
    """Minimal HOME with git config for worktree tests."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(
        "[user]\n"
        "    name = Test User\n"
        "    email = test@example.com\n"
        "[init]\n"
        "    defaultBranch = main\n"
    )
    return home


def _run_git(cmd: str, cwd: Path, home: Path):
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
def repo_with_worktrees(tmp_path, fake_home):
    """Create a git repo with two worktrees for testing resolve_worktree."""
    main = tmp_path / "main-repo"
    main.mkdir()
    _run_git("git init", main, fake_home)
    (main / "README.md").write_text("main\n")
    _run_git("git add -A && git commit -m 'init'", main, fake_home)

    wt_feat = tmp_path / "wt-feat"
    _run_git(f"git worktree add {wt_feat} -b feat/my-feature", main, fake_home)

    wt_moat = tmp_path / "wt-moat"
    _run_git(f"git worktree add {wt_moat} -b moat/20260413-120000", main, fake_home)

    return main


# ---------------------------------------------------------------------------
# Unit tests — pure functions, no mocks
# ---------------------------------------------------------------------------

class TestTruncate:
    def test_short_string_unchanged(self):
        assert server._truncate("hello", limit=100) == "hello"

    def test_exact_limit_unchanged(self):
        text = "x" * 4000
        assert server._truncate(text, limit=4000) == text

    def test_long_string_truncated(self):
        text = "A" * 1000 + "B" * 4000
        result = server._truncate(text, limit=4000)
        assert result.endswith("B" * 4000)
        assert result.startswith("...[truncated 1000 characters]...")

    def test_empty_string(self):
        assert server._truncate("", limit=4000) == ""


class TestSanitizeBranch:
    def test_slashes_replaced(self):
        assert server._sanitize_branch("feat/my-branch") == "feat-my-branch"

    def test_moat_branch(self):
        assert server._sanitize_branch("moat/20260413-120000") == "moat-20260413-120000"

    def test_clean_name_unchanged(self):
        assert server._sanitize_branch("simple-branch") == "simple-branch"

    def test_special_chars(self):
        assert server._sanitize_branch("feat/foo@bar.baz") == "feat-foo-bar-baz"


# ---------------------------------------------------------------------------
# Worktree resolution — uses real git repos
# ---------------------------------------------------------------------------

class TestResolveWorktree:
    def test_resolves_feature_branch(self, repo_with_worktrees, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "REPO_ROOT", str(repo_with_worktrees))
        result = server.resolve_worktree("feat/my-feature")
        assert result == tmp_path / "wt-feat"

    def test_resolves_moat_branch(self, repo_with_worktrees, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "REPO_ROOT", str(repo_with_worktrees))
        result = server.resolve_worktree("moat/20260413-120000")
        assert result == tmp_path / "wt-moat"

    def test_unknown_branch_raises(self, repo_with_worktrees, monkeypatch):
        monkeypatch.setattr(server, "REPO_ROOT", str(repo_with_worktrees))
        with pytest.raises(ValueError, match="No worktree found"):
            server.resolve_worktree("nonexistent-branch")

    def test_no_repo_root_raises(self, monkeypatch):
        monkeypatch.setattr(server, "REPO_ROOT", "")
        with pytest.raises(ValueError, match="XCODE_PROXY_REPO is not set"):
            server.resolve_worktree("any-branch")


# ---------------------------------------------------------------------------
# Tool tests — mock subprocess calls to xcodebuild/xcrun
# ---------------------------------------------------------------------------

class TestXcodebuildTool:
    def test_build_constructs_correct_command(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            result = json.loads(server.xcodebuild("my-branch", "build", "MyApp"))

        assert result["success"] is True
        cmd = mock_run.call_args[0][0]
        assert cmd[:2] == ["xcodebuild", "build"]
        assert "-scheme" in cmd
        assert cmd[cmd.index("-scheme") + 1] == "MyApp"
        assert "-derivedDataPath" in cmd
        assert str(worktree / "DerivedData") in cmd

    def test_build_includes_simulator_destination(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)
        server.SIMULATORS["my-branch"] = {"udid": "FAKE-UUID", "device_name": "Moat-my-branch"}

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            server.xcodebuild("my-branch", "build", "MyApp")

        cmd = mock_run.call_args[0][0]
        assert "-destination" in cmd
        assert "platform=iOS Simulator,id=FAKE-UUID" in cmd

    def test_test_action_passes_destination(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)
        server.SIMULATORS["my-branch"] = {"udid": "TEST-UUID", "device_name": "Moat-test"}

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            server.xcodebuild("my-branch", "test", "MyApp")

        cmd = mock_run.call_args[0][0]
        assert cmd[1] == "test"
        assert "platform=iOS Simulator,id=TEST-UUID" in cmd

    def test_extra_args_appended(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            server.xcodebuild("my-branch", "build", "MyApp", extra_args=["CODE_SIGNING_ALLOWED=NO"])

        cmd = mock_run.call_args[0][0]
        assert "CODE_SIGNING_ALLOWED=NO" in cmd

    def test_invalid_action(self):
        result = json.loads(server.xcodebuild("b", "destroy", "MyApp"))
        assert result["success"] is False
        assert "Invalid action" in result["output"]

    def test_bad_branch_returns_error(self, monkeypatch):
        monkeypatch.setattr(server, "REPO_ROOT", "/nonexistent")
        result = json.loads(server.xcodebuild("bad-branch", "build", "MyApp"))
        assert result["success"] is False


class TestSimulatorTool:
    def test_boot_creates_and_stores(self):
        fake_create = mock.MagicMock(
            return_value=mock.Mock(returncode=0, stdout="NEW-UUID\n", stderr="")
        )
        fake_boot = mock.MagicMock(
            return_value=mock.Mock(returncode=0, stdout="", stderr="")
        )

        with mock.patch.object(server, "_find_existing_simulator", return_value=None), \
             mock.patch.object(server, "_detect_runtime_and_device", return_value=("runtime-id", "device-type")), \
             mock.patch("server.subprocess.run", side_effect=[fake_create.return_value, fake_boot.return_value]):
            result = json.loads(server.simulator("feat/test", "boot"))

        assert result["success"] is True
        assert result["udid"] == "NEW-UUID"
        assert "feat/test" in server.SIMULATORS

    def test_boot_reuses_existing_simulator(self):
        fake_boot = mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(server, "_find_existing_simulator", return_value="EXISTING-UUID"), \
             mock.patch("server.subprocess.run", return_value=fake_boot):
            result = json.loads(server.simulator("feat/test", "boot"))

        assert result["success"] is True
        assert result["udid"] == "EXISTING-UUID"

    def test_shutdown_deletes_simulator(self):
        server.SIMULATORS["feat/test"] = {"udid": "DEL-UUID", "device_name": "Moat-feat-test"}

        with mock.patch("server.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
            result = json.loads(server.simulator("feat/test", "shutdown"))

        assert result["success"] is True
        assert "feat/test" not in server.SIMULATORS
        # Should call shutdown then delete
        assert mock_run.call_count == 2

    def test_shutdown_no_simulator(self):
        result = json.loads(server.simulator("feat/test", "shutdown"))
        assert result["success"] is True
        assert "No simulator" in result["output"]

    def test_status_returns_state(self):
        server.SIMULATORS["feat/test"] = {"udid": "STATUS-UUID", "device_name": "Moat-feat-test"}
        devices_json = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-18-0": [
                    {"udid": "STATUS-UUID", "name": "Moat-feat-test", "state": "Booted", "isAvailable": True}
                ]
            }
        }

        with mock.patch("server.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=json.dumps(devices_json),
                stderr="",
            )
            result = json.loads(server.simulator("feat/test", "status"))

        assert result["success"] is True
        assert result["state"] == "Booted"

    def test_invalid_action(self):
        result = json.loads(server.simulator("feat/test", "restart"))
        assert result["success"] is False


class TestInstallAndLaunchTool:
    def test_installs_and_launches(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        app_dir = worktree / "DerivedData/Build/Products/Debug-iphonesimulator/MyApp.app"
        app_dir.mkdir(parents=True)
        (app_dir / "Info.plist").write_text("")  # placeholder

        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)
        server.SIMULATORS["my-branch"] = {"udid": "SIM-UUID", "device_name": "Moat-my-branch"}

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            result = json.loads(server.install_and_launch(
                "my-branch",
                "DerivedData/Build/Products/Debug-iphonesimulator/MyApp.app",
                bundle_id="com.example.MyApp",
            ))

        assert result["success"] is True
        assert result["bundle_id"] == "com.example.MyApp"
        # install + launch = 2 calls
        assert mock_run.call_count == 2

    def test_missing_app_returns_error(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)
        server.SIMULATORS["my-branch"] = {"udid": "SIM-UUID", "device_name": "Moat-my-branch"}

        result = json.loads(server.install_and_launch("my-branch", "NoSuch.app"))
        assert result["success"] is False
        assert "not found" in result["output"]

    def test_no_simulator_returns_error(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)

        result = json.loads(server.install_and_launch("my-branch", "App.app"))
        assert result["success"] is False
        assert "No simulator" in result["output"]


class TestScreenshotTool:
    def test_captures_screenshot(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)
        server.SIMULATORS["my-branch"] = {"udid": "SIM-UUID", "device_name": "Moat-my-branch"}

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            result = json.loads(server.screenshot("my-branch", "test.png"))

        assert result["success"] is True
        assert result["path"] == str(worktree / "test.png")
        cmd = mock_run.call_args[0][0]
        assert cmd[:2] == ["xcrun", "simctl"]
        assert "screenshot" in cmd

    def test_default_filename(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)
        server.SIMULATORS["my-branch"] = {"udid": "SIM-UUID", "device_name": "Moat-my-branch"}

        with mock.patch.object(server, "_run_cmd") as mock_run:
            mock_run.return_value = {"success": True, "exit_code": 0, "output": "ok"}
            result = json.loads(server.screenshot("my-branch"))

        assert result["path"].endswith("screenshot.png")

    def test_no_simulator_returns_error(self, tmp_path, monkeypatch):
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        monkeypatch.setattr(server, "resolve_worktree", lambda b: worktree)

        result = json.loads(server.screenshot("my-branch"))
        assert result["success"] is False


# ---------------------------------------------------------------------------
# _run_cmd tests
# ---------------------------------------------------------------------------

class TestRunCmd:
    def test_successful_command(self, tmp_path):
        result = server._run_cmd(["echo", "hello"], cwd=tmp_path)
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "hello" in result["output"]

    def test_failed_command(self, tmp_path):
        result = server._run_cmd(["false"], cwd=tmp_path)
        assert result["success"] is False
        assert result["exit_code"] != 0

    def test_command_not_found(self, tmp_path):
        result = server._run_cmd(["nonexistent_binary_xyz"], cwd=tmp_path)
        assert result["success"] is False
        assert "Command not found" in result["output"]

    def test_timeout(self, tmp_path):
        result = server._run_cmd(["sleep", "10"], cwd=tmp_path, timeout=1)
        assert result["success"] is False
        assert "timed out" in result["output"]
