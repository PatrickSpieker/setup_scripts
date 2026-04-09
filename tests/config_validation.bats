#!/usr/bin/env bats

setup() {
  REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  load "$REPO_DIR/tests/libs/bats-support/load"
  load "$REPO_DIR/tests/libs/bats-assert/load"
  export NODE_PATH="$REPO_DIR/tests/libs/node_modules"
  VALIDATOR="$REPO_DIR/validate_configs.mjs"
}

@test "defaults/settings.json is valid JSON" {
  run node "$VALIDATOR" "$REPO_DIR/defaults/settings.json"
  assert_success
  assert_output --partial "OK"
}

@test "vscode_settings.json is valid JSONC" {
  run node "$VALIDATOR" "$REPO_DIR/vscode_settings.json"
  assert_success
  assert_output --partial "OK"
}

@test "moat.yaml is valid YAML" {
  run node "$VALIDATOR" "$REPO_DIR/moat.yaml"
  assert_success
  assert_output --partial "OK"
}

@test "templates/moat.yaml is valid YAML" {
  run node "$VALIDATOR" "$REPO_DIR/templates/moat.yaml"
  assert_success
  assert_output --partial "OK"
}

@test "validator rejects invalid JSON" {
  local bad="$BATS_TEST_TMPDIR/bad.json"
  echo '{"missing": value}' > "$bad"
  run node "$VALIDATOR" "$bad"
  assert_failure
  assert_output --partial "FAIL"
}
