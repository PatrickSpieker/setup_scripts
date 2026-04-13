#!/usr/bin/env bash
set -euo pipefail

# Creates N iOS simulators for parallel Xcode agent sessions.
# Must be run from inside a git repo. Derives repo-id from git remote.
#
# Usage: setup-xcode-agents.sh [count=5] [device="iPhone 16"]

COUNT="${1:-5}"
DEVICE="${2:-iPhone 16}"
CONFIG_DIR="$HOME/.moat/xcode-bridge"

# --- Derive repo-id from git remote (matches Moat's host/owner/repo convention) ---
_derive_repo_id() {
  local remote
  remote=$(git remote get-url origin 2>/dev/null || true)

  if [[ -z "$remote" ]]; then
    echo "_local/$(basename "$(git rev-parse --show-toplevel)")"
    return
  fi

  # git@github.com:owner/repo.git → github.com/owner/repo
  # https://github.com/owner/repo.git → github.com/owner/repo
  echo "$remote" \
    | sed -E 's#^(ssh://)?git@##; s#^https?://##; s#:#/#; s#\.git$##'
}

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "Error: not inside a git repo. Run from your Xcode project root."
  exit 1
fi

REPO_ID=$(_derive_repo_id)
REPO_SLUG=$(basename "$REPO_ID")
CONFIG_FILE="$CONFIG_DIR/$REPO_ID.json"

# Pick the latest iOS runtime
RUNTIME=$(xcrun simctl list runtimes iOS -j \
  | jq -r '.runtimes | map(select(.isAvailable)) | last | .identifier')

if [[ -z "$RUNTIME" || "$RUNTIME" == "null" ]]; then
  echo "Error: no available iOS runtime found. Install one via Xcode."
  exit 1
fi

echo "Repo:    $REPO_ID"
echo "Runtime: $RUNTIME"
echo "Device:  $DEVICE"
echo "Count:   $COUNT"
echo ""

# Create config directory (may include slashes in repo-id path)
mkdir -p "$(dirname "$CONFIG_FILE")"

# Build the config JSON incrementally
UDIDS=()
echo '{"slots":{}}' > "$CONFIG_FILE"

for i in $(seq 1 "$COUNT"); do
  NAME="xcode-bridge-${REPO_SLUG}-${i}"
  BRANCH="moat/agent-${i}"

  # Delete existing sim with same name (idempotent re-runs)
  EXISTING=$(xcrun simctl list devices -j \
    | jq -r --arg n "$NAME" '.devices[][] | select(.name == $n) | .udid' 2>/dev/null || true)
  if [[ -n "$EXISTING" ]]; then
    xcrun simctl delete "$EXISTING" 2>/dev/null || true
  fi

  UDID=$(xcrun simctl create "$NAME" "$DEVICE" "$RUNTIME")
  UDIDS+=("$UDID")

  # Add slot to config
  jq --arg b "$BRANCH" --arg u "$UDID" \
    '.slots[$b] = $u' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" \
    && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

  echo "  Created '$NAME' ($UDID) -> $BRANCH"
done

echo ""
echo "Config written to: $CONFIG_FILE"
echo ""
echo "To tear down:"
echo "  xcrun simctl delete ${UDIDS[*]}"
echo ""
echo "Ready. Run: mcl-xcode \"your prompt here\""
