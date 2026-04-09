#!/usr/bin/env bats

setup() {
  REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  load "$REPO_DIR/tests/libs/bats-support/load"
  load "$REPO_DIR/tests/libs/bats-assert/load"
  HOOK="$REPO_DIR/hooks/pre-push"
}

@test "allows push when CLAUDECODE is not set" {
  unset CLAUDECODE
  run bash -c 'echo "refs/heads/foo abc123 refs/heads/main def456" | bash '"$HOOK"
  assert_success
}

@test "blocks Claude push to main" {
  run bash -c 'CLAUDECODE=1 echo "refs/heads/foo abc123 refs/heads/main def456" | CLAUDECODE=1 bash '"$HOOK"
  assert_failure
  assert_output --partial "blocked"
}

@test "blocks Claude push to master" {
  run bash -c 'echo "refs/heads/foo abc123 refs/heads/master def456" | CLAUDECODE=1 bash '"$HOOK"
  assert_failure
  assert_output --partial "blocked"
}

@test "allows Claude push to feature branch" {
  run bash -c 'echo "refs/heads/foo abc123 refs/heads/feature/bar def456" | CLAUDECODE=1 bash '"$HOOK"
  assert_success
}

@test "allows Claude push when no refs target main" {
  run bash -c 'echo "refs/heads/foo abc123 refs/heads/dev def456" | CLAUDECODE=1 bash '"$HOOK"
  assert_success
}
