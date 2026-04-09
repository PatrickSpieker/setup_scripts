# Shared test helpers for bats tests

REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"

# Load bats helpers
load "$REPO_DIR/tests/libs/bats-support/load"
load "$REPO_DIR/tests/libs/bats-assert/load"

# Create a mock command on a temporary PATH
# Usage: create_mock <command> [exit_code] [stdout_output]
create_mock() {
  local cmd="$1"
  local exit_code="${2:-0}"
  local output="${3:-}"
  mkdir -p "$MOCK_BIN"
  cat > "$MOCK_BIN/$cmd" <<MOCK
#!/usr/bin/env bash
echo "\$0 \$*" >> "$MOCK_LOG"
${output:+echo "$output"}
exit $exit_code
MOCK
  chmod +x "$MOCK_BIN/$cmd"
}

# Initialize mock environment
setup_mocks() {
  MOCK_BIN="$BATS_TEST_TMPDIR/bin"
  MOCK_LOG="$BATS_TEST_TMPDIR/mock_calls.log"
  mkdir -p "$MOCK_BIN"
  export PATH="$MOCK_BIN:$PATH"
  : > "$MOCK_LOG"
}

# Check if a mock was called with a pattern
assert_mock_called_with() {
  local pattern="$1"
  grep -q "$pattern" "$MOCK_LOG" || {
    echo "Expected mock call matching: $pattern"
    echo "Actual calls:"
    cat "$MOCK_LOG"
    return 1
  }
}
