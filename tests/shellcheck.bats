#!/usr/bin/env bats

setup() {
  REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  load "$REPO_DIR/tests/libs/bats-support/load"
  load "$REPO_DIR/tests/libs/bats-assert/load"
}

@test "shellcheck: hooks/pre-push" {
  run shellcheck "$REPO_DIR/hooks/pre-push"
  assert_success
}

@test "shellcheck: bashrc_main" {
  # SC2034: oh-my-bash vars (OSH_THEME, OMB_USE_SUDO, completions, plugins) are consumed by sourced framework
  # SC1091: external sources (~/.cargo/env, oh-my-bash.sh) not available in test
  # SC2155: gem PATH line — intentional one-liner
  run shellcheck \
    --exclude=SC2034,SC1091,SC2155 \
    "$REPO_DIR/bashrc_main"
  assert_success
}

@test "shellcheck: setup.sh" {
  # SC1090: non-constant source (~/.bash_profile)
  run shellcheck \
    --exclude=SC1090 \
    "$REPO_DIR/setup.sh"
  assert_success
}
