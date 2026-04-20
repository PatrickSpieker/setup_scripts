"""Tests for shell functions defined in bashrc_main.

These tests use REAL git repos (via the git_repo and git_repo_with_remote
fixtures) instead of mock git scripts. Only non-git externals are mocked:
  - gem/bind: needed to source bashrc_main without errors
  - moat: can't run a real moat container in tests
  - gh: can't call real GitHub API in tests

This makes tests easier to read: instead of decoding a 15-line bash mock
script to understand what git state the test assumes, you can see the
actual repo setup (git init, git add, git commit, etc.) directly.
"""

import json
import os
import subprocess
import textwrap
from datetime import datetime, timezone, timedelta

from conftest import REPO_DIR, run_bash_function


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_sourcing_mocks(mock_bin):
    """Create the mocks needed just to source bashrc_main without errors.

    bashrc_main runs `gem environment gemdir` (for PATH setup) and
    `bind 'set bell-style none'` on load. These aren't part of our tests,
    but they'll fail if the commands don't exist on PATH.

    Also mocks ssh-add so _mcl_ensure_ssh_key succeeds (reports the
    Moat SSH key as already loaded).
    """
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("ssh-add", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "$0 $*" >> "{mock_bin.log}"
        if [[ "$1" == "-l" ]]; then
            echo "256 SHA256:xxxx id_ed25519_moat (ED25519)"
        fi
        exit 0
    """))


def _run_git(cmd, cwd, fake_home):
    """Run a git command using the test's fake HOME for config isolation."""
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    return subprocess.run(
        ["bash", "-c", cmd],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


# ===========================================================================
# moat-init
# ===========================================================================

def test_moat_init_copies_template(tmp_path, repo_dir, mock_bin, fake_home):
    """moat-init should copy the template moat.yaml into the current directory."""
    _setup_sourcing_mocks(mock_bin)
    workdir = tmp_path / "project"
    workdir.mkdir()

    r = run_bash_function("moat-init", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    assert "Copied moat.yaml template" in r.stdout
    assert (workdir / "moat.yaml").exists()


def test_moat_init_refuses_when_exists(tmp_path, repo_dir, mock_bin, fake_home):
    """moat-init should refuse if moat.yaml already exists."""
    _setup_sourcing_mocks(mock_bin)
    workdir = tmp_path / "project"
    workdir.mkdir()
    (workdir / "moat.yaml").touch()

    r = run_bash_function("moat-init", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode != 0
    assert "already exists" in r.stdout


# ===========================================================================
# sync-skills
# ===========================================================================

def test_sync_skills_creates_symlinks(repo_dir, mock_bin, fake_home):
    """sync-skills should symlink each skill dir into ~/.codex/skills/."""
    _setup_sourcing_mocks(mock_bin)

    r = run_bash_function("sync-skills", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode == 0
    assert (fake_home / ".codex/skills/skill-a").is_symlink()


# ===========================================================================
# mcl — basic behavior
# ===========================================================================

def test_mcl_auto_inits_git_repo(tmp_path, repo_dir, mock_bin, fake_home):
    """mcl in a non-git directory should auto-run `git init`."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat")
    # Start in a plain directory (no .git/) so mcl triggers its auto-init.
    workdir = tmp_path / "project"
    workdir.mkdir()

    r = run_bash_function("mcl test-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    assert "Initialized git repo" in r.stdout
    # Verify git actually initialized a repo
    assert (workdir / ".git").exists()


def test_mcl_auto_creates_moat_yaml(tmp_path, repo_dir, mock_bin, fake_home, git_repo):
    """mcl in a repo without moat.yaml should auto-create it from the template."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat")
    # Remove the moat.yaml that git_repo creates by default,
    # so mcl triggers its auto-create logic.
    (git_repo / "moat.yaml").unlink()
    _run_git("git add -A && git commit -m 'remove moat.yaml'", git_repo, fake_home)

    r = run_bash_function("mcl test-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo))
    assert r.returncode == 0
    assert "Created moat.yaml from template" in r.stdout


def test_mcl_worktree_mode(repo_dir, mock_bin, fake_home, git_repo):
    """mcl (default, no -m) should invoke moat with --worktree."""
    _setup_sourcing_mocks(mock_bin)
    # moat is the only thing we mock — git is real.
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo))
    assert r.returncode == 0
    mock_bin.assert_called_with("moat claude --worktree my-branch -- --model=opus")
    assert "Cleaning up worktree" in r.stdout


def test_mcl_mount_creates_branch_and_runs_moat(repo_dir, mock_bin, fake_home, git_repo):
    """mcl -m should create a new branch and invoke moat without --worktree."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mcl -m my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo))
    assert r.returncode == 0
    mock_bin.assert_called_with("moat claude -- --model=opus")
    # Verify git actually created the branch
    result = _run_git("git branch --show-current", git_repo, fake_home)
    assert result.stdout.strip() == "my-branch"


# ===========================================================================
# mco
# ===========================================================================

def test_mco_worktree_mode_uses_nonprompting_codex_flags(repo_dir, mock_bin, fake_home, git_repo):
    """mco should start Codex in Moat without Codex's first-run prompts."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mco my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo))
    assert r.returncode == 0
    mock_bin.assert_called_with(
        "moat codex --worktree my-branch --full-auto=false -- "
        "--dangerously-bypass-approvals-and-sandbox -m gpt-5.4 -C /workspace"
    )
    assert "Cleaning up worktree" in r.stdout


def test_mco_mount_mode_uses_nonprompting_codex_flags(repo_dir, mock_bin, fake_home, git_repo):
    """mco -m should pass the same non-prompting Codex flags."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mco -m my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo))
    assert r.returncode == 0
    mock_bin.assert_called_with(
        "moat codex --full-auto=false -- "
        "--dangerously-bypass-approvals-and-sandbox -m gpt-5.4 -C /workspace"
    )
    result = _run_git("git branch --show-current", git_repo, fake_home)
    assert result.stdout.strip() == "my-branch"


# ===========================================================================
# mcl — freshness check (_mcl_ensure_default_branch_fresh)
# ===========================================================================
# The freshness check runs before every mcl/mclpr invocation. It:
#   1. Skips if there's no "origin" remote
#   2. Fails if there are uncommitted changes
#   3. Detects the default branch (main or master)
#   4. Fetches, checks out, and pulls the default branch
#
# These tests use git_repo_with_remote, which sets up a local bare repo
# as "origin" so fetch/pull work without network access.

def test_mcl_fetches_and_pulls_default_branch(repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mcl should checkout and pull the default branch before starting."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode == 0
    assert "Fetching latest main from origin" in r.stdout
    # After the freshness check, we should be on main (the default branch)
    # and moat should have been invoked.
    mock_bin.assert_called_with("moat claude --worktree my-branch -- --model=opus")


def test_mcl_pulls_new_commits_from_origin(tmp_path, repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mcl should pull commits that exist on origin but not locally."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    # Simulate someone else pushing a commit to origin:
    # Clone the bare repo into a separate directory, make a commit, push it.
    # Now origin has a commit that our working repo doesn't.
    other_clone = tmp_path / "other-clone"
    _run_git(f"git clone {tmp_path / 'origin.git'} {other_clone}", tmp_path, fake_home)
    (other_clone / "new_file.txt").write_text("from another contributor\n")
    _run_git("git add -A && git commit -m 'new commit from other clone'", other_clone, fake_home)
    _run_git("git push origin main", other_clone, fake_home)

    # Now run mcl — it should fetch+pull the new commit before proceeding.
    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode == 0
    # Verify the new file was actually pulled down
    assert (git_repo_with_remote / "new_file.txt").exists()


def test_mcl_skips_freshness_without_remote(repo_dir, mock_bin, fake_home, git_repo):
    """mcl should skip the freshness check when there's no origin remote."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))
    # git_repo has no remote — freshness check should be skipped entirely.

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo))
    assert r.returncode == 0
    assert "Fetching latest" not in r.stdout
    mock_bin.assert_called_with("moat claude --worktree my-branch -- --model=opus")


def test_mcl_fails_with_dirty_tree(repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mcl should refuse to run if there are uncommitted changes."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat")
    # Create a dirty working tree by modifying a tracked file without committing.
    (git_repo_with_remote / "README.md").write_text("modified but not committed\n")

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode != 0
    assert "uncommitted changes" in r.stdout


def test_mcl_fails_with_staged_changes(repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mcl should also catch staged-but-uncommitted changes."""
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat")
    # Stage a change without committing it.
    (git_repo_with_remote / "README.md").write_text("staged but not committed\n")
    _run_git("git add README.md", git_repo_with_remote, fake_home)

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode != 0
    assert "uncommitted changes" in r.stdout


def test_mcl_detects_master_as_default(tmp_path, repo_dir, mock_bin, fake_home):
    """mcl should detect 'master' when that's the default branch name.

    This tests the fallback detection path: when symbolic-ref doesn't work
    and origin/main doesn't exist, it should find origin/master.
    """
    _setup_sourcing_mocks(mock_bin)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    # Build a repo that uses "master" instead of "main" by overriding
    # the init.defaultBranch config for this specific repo.
    origin = tmp_path / "origin.git"
    workdir = tmp_path / "project"
    workdir.mkdir()
    home = fake_home

    _run_git(f"git init --bare {origin}", tmp_path, home)
    _run_git("git init", workdir, home)
    # Override the default branch to "master" for this repo only.
    _run_git("git config init.defaultBranch master", workdir, home)
    _run_git("git checkout -b master", workdir, home)
    _run_git(f"git remote add origin {origin}", workdir, home)
    (workdir / "README.md").write_text("test\n")
    (workdir / "moat.yaml").write_text("runtime: apple\n")
    _run_git("git add -A && git commit -m 'init'", workdir, home)
    _run_git("git push -u origin master", workdir, home)

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    assert "Fetching latest master from origin" in r.stdout


# ===========================================================================
# mclpr
# ===========================================================================
# mclpr takes a PR number, looks up the branch via `gh`, fetches it,
# and starts a moat session on that branch. It also runs the freshness
# check before doing anything.

def test_mclpr_fails_without_argument(repo_dir, mock_bin, fake_home):
    """mclpr with no args should print usage and exit non-zero."""
    _setup_sourcing_mocks(mock_bin)

    r = run_bash_function("mclpr", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode != 0
    assert "Usage: mclpr" in r.stdout


def test_mclpr_fetches_pr_branch_and_runs_moat(repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mclpr should look up the PR branch, fetch it, and start moat."""
    _setup_sourcing_mocks(mock_bin)

    # Create a feature branch on origin so there's something to fetch.
    # We push it directly to the bare repo via our working copy.
    _run_git("git checkout -b feat/cool-feature", git_repo_with_remote, fake_home)
    (git_repo_with_remote / "feature.txt").write_text("new feature\n")
    _run_git("git add -A && git commit -m 'add feature'", git_repo_with_remote, fake_home)
    _run_git("git push origin feat/cool-feature", git_repo_with_remote, fake_home)
    # Switch back to main so mclpr's worktree can use the feature branch.
    _run_git("git checkout main", git_repo_with_remote, fake_home)

    # Mock gh to return the branch name (we can't call real GitHub API).
    mock_bin.create("gh", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "gh $*" >> "{mock_bin.log}"
        echo "feat/cool-feature"
        exit 0
    """))
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mclpr 42", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode == 0
    # Verify it looked up the PR, then started moat on the right branch.
    mock_bin.assert_called_with("gh pr view 42")
    mock_bin.assert_called_with("moat claude --worktree feat/cool-feature -- --model=opus")


def test_mclpr_runs_freshness_check(repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mclpr should fetch+pull the default branch before fetching the PR branch."""
    _setup_sourcing_mocks(mock_bin)

    # Create a feature branch on origin for the PR.
    _run_git("git checkout -b feat/pr-branch", git_repo_with_remote, fake_home)
    (git_repo_with_remote / "pr.txt").write_text("pr content\n")
    _run_git("git add -A && git commit -m 'pr commit'", git_repo_with_remote, fake_home)
    _run_git("git push origin feat/pr-branch", git_repo_with_remote, fake_home)
    _run_git("git checkout main", git_repo_with_remote, fake_home)

    mock_bin.create("gh", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "gh $*" >> "{mock_bin.log}"
        echo "feat/pr-branch"
        exit 0
    """))
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mclpr 99", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode == 0
    # The freshness check should have run (fetching main) before the PR fetch.
    assert "Fetching latest main from origin" in r.stdout


# ===========================================================================
# mclb
# ===========================================================================
# mclb is like mclpr but takes a branch name directly instead of a PR number.

def test_mclb_fails_without_argument(repo_dir, mock_bin, fake_home):
    """mclb with no args should print usage and exit non-zero."""
    _setup_sourcing_mocks(mock_bin)

    r = run_bash_function("mclb", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode != 0
    assert "Usage: mclb" in r.stdout


def test_mclb_fetches_branch_and_runs_moat(repo_dir, mock_bin, fake_home, git_repo_with_remote):
    """mclb should fetch the named branch from origin and start moat."""
    _setup_sourcing_mocks(mock_bin)

    # Create a branch on origin so there's something to fetch.
    _run_git("git checkout -b feat/my-branch", git_repo_with_remote, fake_home)
    (git_repo_with_remote / "branch.txt").write_text("branch content\n")
    _run_git("git add -A && git commit -m 'branch commit'", git_repo_with_remote, fake_home)
    _run_git("git push origin feat/my-branch", git_repo_with_remote, fake_home)
    _run_git("git checkout main", git_repo_with_remote, fake_home)

    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mclb feat/my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo_with_remote))
    assert r.returncode == 0
    mock_bin.assert_called_with("moat claude --worktree feat/my-branch -- --model=opus")
    assert "Cleaning up worktree" in r.stdout


# ===========================================================================
# _mcl_warn_orphaned_containers
# ===========================================================================
# The orphan warning runs before every mcl/mco/mclpr/mclb invocation. It:
#   1. Skips silently if moat isn't on PATH
#   2. Calls moat list --json, pipes through python3 to find stale containers
#   3. Prints a warning if any running containers are older than 2 hours
#   4. Prompts to stop them (defaults to "N" when no TTY — safe in tests)

def _make_moat_list_json(runs):
    """Build a moat list --json mock script that outputs the given run dicts."""
    return json.dumps(runs)


def test_mcl_warns_about_orphaned_containers(repo_dir, mock_bin, fake_home, git_repo):
    """mcl should warn when stale Moat containers are still running."""
    _setup_sourcing_mocks(mock_bin)

    # Build a moat mock that returns JSON with a stale running container
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    runs = [
        {
            "Name": "moat-stale-test",
            "State": "running",
            "CreatedAt": stale_time,
            "Workspace": "/Users/test/project/stale-workspace",
            "Agent": "claude",
        },
    ]
    moat_json = _make_moat_list_json(runs)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "$0 $*" >> "{mock_bin.log}"
        if [[ "$1" == "list" && "$2" == "--json" ]]; then
            echo '{moat_json}'
            exit 0
        fi
        exit 0
    """))

    r = run_bash_function(
        "_mcl_warn_orphaned_containers",
        repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo),
    )
    assert r.returncode == 0
    assert "stale Moat containers" in r.stdout
    assert "moat-stale-test" in r.stdout


def test_mcl_no_warning_when_no_orphans(repo_dir, mock_bin, fake_home, git_repo):
    """mcl should not warn when all containers are stopped."""
    _setup_sourcing_mocks(mock_bin)

    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    runs = [
        {
            "Name": "moat-recent-ok",
            "State": "stopped",
            "CreatedAt": recent_time,
            "Workspace": "/Users/test/project",
            "Agent": "claude",
        },
    ]
    moat_json = _make_moat_list_json(runs)
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "$0 $*" >> "{mock_bin.log}"
        if [[ "$1" == "list" && "$2" == "--json" ]]; then
            echo '{moat_json}'
            exit 0
        fi
        exit 0
    """))

    r = run_bash_function(
        "_mcl_warn_orphaned_containers",
        repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo),
    )
    assert r.returncode == 0
    assert "stale Moat containers" not in r.stdout


def test_mcl_no_warning_when_moat_list_errors(repo_dir, mock_bin, fake_home, git_repo):
    """Function should proceed silently when moat list fails."""
    _setup_sourcing_mocks(mock_bin)
    # moat exists but list always errors — simulates broken or old moat.
    mock_bin.create("moat", exit_code=1)

    r = run_bash_function(
        "_mcl_warn_orphaned_containers",
        repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(git_repo),
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""
