"""Tests for shell functions defined in bashrc_main."""

import textwrap

from conftest import REPO_DIR, run_bash_function


# ===== moat-init =====

def test_moat_init_copies_template(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    workdir = tmp_path / "project"
    workdir.mkdir()

    r = run_bash_function("moat-init", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    assert "Copied moat.yaml template" in r.stdout
    assert (workdir / "moat.yaml").exists()


def test_moat_init_refuses_when_exists(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    workdir = tmp_path / "project"
    workdir.mkdir()
    (workdir / "moat.yaml").touch()

    r = run_bash_function("moat-init", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode != 0
    assert "already exists" in r.stdout


# ===== sync-skills =====

def test_sync_skills_creates_symlinks(repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")

    r = run_bash_function("sync-skills", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode == 0
    assert (fake_home / ".codex/skills/skill-a").is_symlink()


# ===== mcl =====

def test_mcl_auto_inits_git_repo(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("moat")
    mock_bin.create("git", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "git $*" >> "{mock_bin.log}"
        if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then exit 1; fi
        if [[ "$1" == "init" ]]; then echo "Initialized empty Git repository"; exit 0; fi
        if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then exit 0; fi
        exit 0
    """))

    r = run_bash_function("mcl test-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode == 0
    assert "Initialized" in r.stdout


def test_mcl_auto_creates_moat_yaml(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("moat")
    mock_bin.create("git", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "git $*" >> "{mock_bin.log}"
        if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then exit 0; fi
        if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then exit 0; fi
        exit 0
    """))
    workdir = tmp_path / "project"
    workdir.mkdir()

    r = run_bash_function("mcl test-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    assert "Created moat.yaml from template" in r.stdout


def test_mcl_mount_fails_with_dirty_tree(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("moat")
    mock_bin.create("git", script=textwrap.dedent("""\
        #!/usr/bin/env bash
        if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then exit 0; fi
        if [[ "$1" == "diff" && "$2" == "--quiet" ]]; then exit 1; fi
        exit 0
    """))
    workdir = tmp_path / "project"
    workdir.mkdir()
    (workdir / "moat.yaml").touch()

    r = run_bash_function("mcl -m test-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode != 0
    assert "uncommitted changes" in r.stdout


def test_mcl_mount_creates_branch_and_runs_moat(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("git", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "git $*" >> "{mock_bin.log}"
        if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then exit 0; fi
        if [[ "$1" == "diff" ]]; then exit 0; fi
        exit 0
    """))
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))
    workdir = tmp_path / "project"
    workdir.mkdir()
    (workdir / "moat.yaml").touch()

    r = run_bash_function("mcl -m my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    mock_bin.assert_called_with("git checkout -b my-branch")
    mock_bin.assert_called_with("moat claude -- --model=opus")


def test_mcl_worktree_mode(tmp_path, repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("git", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "git $*" >> "{mock_bin.log}"
        if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then exit 0; fi
        if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then exit 0; fi
        exit 0
    """))
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))
    workdir = tmp_path / "project"
    workdir.mkdir()
    (workdir / "moat.yaml").touch()

    r = run_bash_function("mcl my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home, cwd=str(workdir))
    assert r.returncode == 0
    mock_bin.assert_called_with("moat claude --worktree my-branch -- --model=opus")
    assert "Cleaning up worktree" in r.stdout


# ===== mclpr =====

def test_mclpr_fails_without_argument(repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")

    r = run_bash_function("mclpr", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode != 0
    assert "Usage: mclpr" in r.stdout


def test_mclpr_fetches_pr_branch(repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("gh", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "gh $*" >> "{mock_bin.log}"
        echo "feat/cool-feature"
        exit 0
    """))
    mock_bin.create("git", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "git $*" >> "{mock_bin.log}"
        if [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" ]]; then echo "main"; exit 0; fi
        exit 0
    """))
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mclpr 42", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode == 0
    mock_bin.assert_called_with("gh pr view 42")
    mock_bin.assert_called_with("git fetch origin feat/cool-feature")
    mock_bin.assert_called_with("moat claude --worktree feat/cool-feature -- --model=opus")


# ===== mclb =====

def test_mclb_fails_without_argument(repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")

    r = run_bash_function("mclb", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode != 0
    assert "Usage: mclb" in r.stdout


def test_mclb_fetches_branch(repo_dir, mock_bin, fake_home):
    mock_bin.create("gem", stdout="/fake/gem/dir")
    mock_bin.create("bind")
    mock_bin.create("git", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "git $*" >> "{mock_bin.log}"
        if [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" ]]; then echo "main"; exit 0; fi
        exit 0
    """))
    mock_bin.create("moat", script=textwrap.dedent(f"""\
        #!/usr/bin/env bash
        echo "moat $*" >> "{mock_bin.log}"
        exit 0
    """))

    r = run_bash_function("mclb feat/my-branch", repo_dir=repo_dir, mock_bin=mock_bin, fake_home=fake_home)
    assert r.returncode == 0
    mock_bin.assert_called_with("git fetch origin feat/my-branch")
    mock_bin.assert_called_with("moat claude --worktree feat/my-branch -- --model=opus")
    assert "Cleaning up worktree" in r.stdout
