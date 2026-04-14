#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$REPO_DIR/tests"
LIBS_DIR="$TESTS_DIR/libs"
MODE="${1:-all}"

mkdir -p "$LIBS_DIR"

# Install shellcheck via npm if not already available
if ! command -v shellcheck &>/dev/null; then
  if [[ ! -d "$LIBS_DIR/node_modules/shellcheck" ]]; then
    echo "Installing shellcheck..."
    npm install --prefix "$LIBS_DIR" shellcheck 2>&1
  fi
  export PATH="$LIBS_DIR/node_modules/.bin:$PATH"
fi

# Install pytest + pyyaml if needed
if ! python3 -c "import pytest" 2>/dev/null; then
  echo "Installing pytest and pyyaml..."
  pip3 install --quiet --break-system-packages pytest pyyaml
fi

case "$MODE" in
  lint)
    echo "Running linters..."
    python3 -m pytest "$TESTS_DIR/test_lint.py" "$TESTS_DIR/test_skill_structure.py" -v ;;
  test)
    echo "Running tests..."
    python3 -m pytest "$TESTS_DIR/test_pre_push.py" "$TESTS_DIR/test_bashrc_functions.py" -v ;;
  all)
    echo "Running all..."
    python3 -m pytest "$TESTS_DIR" -v ;;
  *)
    echo "Usage: $0 [lint|test|all]"
    exit 1 ;;
esac
