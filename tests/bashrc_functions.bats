#!/usr/bin/env bats

setup() {
  REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  load "$REPO_DIR/tests/libs/bats-support/load"
  load "$REPO_DIR/tests/libs/bats-assert/load"
  load "$REPO_DIR/tests/helpers/setup.bash"
  setup_mocks

  # Set up fake HOME to isolate side effects
  export ORIG_HOME="$HOME"
  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$HOME/setup_scripts/skills/skill-a"
  mkdir -p "$HOME/setup_scripts/templates"
  cp "$REPO_DIR/templates/moat.yaml" "$HOME/setup_scripts/templates/moat.yaml"
  mkdir -p "$HOME/.codex/skills"
  mkdir -p "$HOME/.claude/skills"
  mkdir -p "$HOME/code"

  # Stub commands that bashrc_main calls at source time
  create_mock "gem" 0 "/fake/gem/dir"
  create_mock "bind" 0
  # cargo env — create a no-op file to source
  mkdir -p "$HOME/.cargo"
  echo "" > "$HOME/.cargo/env"
  mkdir -p "$HOME/.local/bin"
  echo "" > "$HOME/.local/bin/env"

  # Source only the function definitions from bashrc_main.
  # The oh-my-bash guard (case $-) returns early in non-interactive mode,
  # so everything after it is skipped — which is fine, functions are above it.
  source "$REPO_DIR/bashrc_main" 2>/dev/null || true
}

teardown() {
  export HOME="$ORIG_HOME"
}

# ===== moat-init =====

@test "moat-init: copies template when moat.yaml missing" {
  cd "$BATS_TEST_TMPDIR"
  run moat-init
  assert_success
  assert_output --partial "Copied moat.yaml template"
  [[ -f "$BATS_TEST_TMPDIR/moat.yaml" ]]
}

@test "moat-init: refuses when moat.yaml exists" {
  cd "$BATS_TEST_TMPDIR"
  touch moat.yaml
  run moat-init
  assert_failure
  assert_output --partial "already exists"
}

# ===== sync-skills =====

@test "sync-skills: creates symlinks in ~/.codex/skills" {
  run sync-skills
  assert_success
  [[ -L "$HOME/.codex/skills/skill-a" ]]
}

# ===== mcl =====

@test "mcl: auto-inits git repo when not in one" {
  # Make git rev-parse fail (not a repo), then succeed for subsequent calls
  create_mock "git" 0
  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
echo "git $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then
  exit 1
fi
if [[ "$1" == "init" ]]; then
  echo "Initialized empty Git repository"
  exit 0
fi
if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then
  exit 0
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"
  export MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"

  create_mock "moat" 0
  cd "$BATS_TEST_TMPDIR"

  run mcl test-branch
  assert_success
  assert_output --partial "Initialized"
}

@test "mcl: auto-creates moat.yaml from template" {
  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
echo "git $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then
  exit 0
fi
if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then
  exit 0
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"
  export MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"

  create_mock "moat" 0
  # Use a subdir so there's no moat.yaml
  local workdir="$BATS_TEST_TMPDIR/project"
  mkdir -p "$workdir"
  cd "$workdir"

  # Restore real cp for the template copy
  unset -f cp 2>/dev/null || true
  export PATH="$MOCK_BIN:$ORIG_HOME/../usr/bin:/usr/bin:/bin:$PATH"

  run mcl test-branch
  assert_success
  assert_output --partial "Created moat.yaml from template"
}

@test "mcl -m: fails with dirty working tree" {
  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then
  exit 0
fi
if [[ "$1" == "diff" && "$2" == "--quiet" ]]; then
  exit 1  # dirty
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"

  create_mock "moat" 0
  cd "$BATS_TEST_TMPDIR"
  touch moat.yaml

  run mcl -m test-branch
  assert_failure
  assert_output --partial "uncommitted changes"
}

@test "mcl -m: creates branch and runs moat in mount mode" {
  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
echo "git $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then
  exit 0
fi
if [[ "$1" == "diff" ]]; then
  exit 0  # clean
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"
  export MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"

  cat > "$MOCK_BIN/moat" <<'MOCK'
#!/usr/bin/env bash
echo "moat $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
exit 0
MOCK
  chmod +x "$MOCK_BIN/moat"

  cd "$BATS_TEST_TMPDIR"
  touch moat.yaml

  run mcl -m my-branch
  assert_success
  assert_mock_called_with "git checkout -b my-branch"
  assert_mock_called_with "moat claude -- --model=opus"
}

@test "mcl: worktree mode runs moat with --worktree" {
  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
echo "git $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then
  exit 0
fi
if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then
  exit 0
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"
  export MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"

  cat > "$MOCK_BIN/moat" <<'MOCK'
#!/usr/bin/env bash
echo "moat $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
exit 0
MOCK
  chmod +x "$MOCK_BIN/moat"

  cd "$BATS_TEST_TMPDIR"
  touch moat.yaml

  run mcl my-branch
  assert_success
  assert_mock_called_with "moat claude --worktree my-branch -- --model=opus"
  assert_output --partial "Cleaning up worktree"
}

# ===== mclpr =====

@test "mclpr: fails without argument" {
  run mclpr
  assert_failure
  assert_output --partial "Usage: mclpr"
}

@test "mclpr: fetches PR branch and runs moat worktree" {
  cat > "$MOCK_BIN/gh" <<'MOCK'
#!/usr/bin/env bash
echo "gh $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
echo "feat/cool-feature"
exit 0
MOCK
  chmod +x "$MOCK_BIN/gh"

  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
echo "git $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
if [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" ]]; then
  echo "main"
  exit 0
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"
  export MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"

  cat > "$MOCK_BIN/moat" <<'MOCK'
#!/usr/bin/env bash
echo "moat $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
exit 0
MOCK
  chmod +x "$MOCK_BIN/moat"

  run mclpr 42
  assert_success
  assert_mock_called_with "gh pr view 42"
  assert_mock_called_with "git fetch origin feat/cool-feature"
  assert_mock_called_with "moat claude --worktree feat/cool-feature -- --model=opus"
}

# ===== mclb =====

@test "mclb: fails without argument" {
  run mclb
  assert_failure
  assert_output --partial "Usage: mclb"
}

@test "mclb: fetches branch and runs moat worktree" {
  cat > "$MOCK_BIN/git" <<'MOCK'
#!/usr/bin/env bash
echo "git $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
if [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" ]]; then
  echo "main"
  exit 0
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/git"
  export MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"

  cat > "$MOCK_BIN/moat" <<'MOCK'
#!/usr/bin/env bash
echo "moat $*" >> "$BATS_TEST_TMPDIR/mock_calls.log"
exit 0
MOCK
  chmod +x "$MOCK_BIN/moat"

  run mclb feat/my-branch
  assert_success
  assert_mock_called_with "git fetch origin feat/my-branch"
  assert_mock_called_with "moat claude --worktree feat/my-branch -- --model=opus"
  assert_output --partial "Cleaning up worktree"
}
