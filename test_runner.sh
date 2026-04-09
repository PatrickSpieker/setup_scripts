#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$REPO_DIR/tests"
LIBS_DIR="$TESTS_DIR/libs"

mkdir -p "$LIBS_DIR"

# Bootstrap bats-core + helpers
for lib in bats-core bats-support bats-assert; do
  if [[ ! -d "$LIBS_DIR/$lib" ]]; then
    echo "Installing $lib..."
    git clone --depth 1 "https://github.com/bats-core/$lib.git" "$LIBS_DIR/$lib" 2>&1
  fi
done

# Install shellcheck + js-yaml via npm
if [[ ! -d "$LIBS_DIR/node_modules/shellcheck" ]] || [[ ! -d "$LIBS_DIR/node_modules/js-yaml" ]]; then
  echo "Installing npm dependencies (shellcheck, js-yaml)..."
  npm install --prefix "$LIBS_DIR" shellcheck js-yaml 2>&1
fi

# Make npm bin available
export PATH="$LIBS_DIR/node_modules/.bin:$PATH"

echo ""
echo "Running tests..."
echo ""
"$LIBS_DIR/bats-core/bin/bats" "$TESTS_DIR"/*.bats
