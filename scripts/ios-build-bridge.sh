#!/bin/bash
# ios-build-bridge: host-side watcher that processes build requests from Moat containers.
#
# Each Moat container writes a .moat-build-req file into its worktree.
# This script polls all registered worktrees, runs the real xcodebuild or
# xcrun simctl command, and writes .moat-build-res with the exit code and
# output (last 200 lines).
#
# Usage:
#   ios-build-bridge.sh <project-relative-path> <scheme> <wt1:sim1> [wt2:sim2 ...]
#
# Example:
#   ios-build-bridge.sh MyApp.xcodeproj MyApp \
#     /path/to/worktree1:AAAA-BBBB-CCCC \
#     /path/to/worktree2:DDDD-EEEE-FFFF
#
# Or with dynamic discovery (reads .moat-simulator-udid from each worktree):
#   ios-build-bridge.sh MyApp.xcodeproj MyApp --auto
#
# Press Ctrl-C to stop.

set -euo pipefail

PROJECT="${1:?Usage: ios-build-bridge.sh <project> <scheme> <wt:sim ...>}"
SCHEME="${2:?Usage: ios-build-bridge.sh <project> <scheme> <wt:sim ...>}"
shift 2

OUTPUT_LINES=200  # max lines of xcodebuild output to return
POLL_INTERVAL=0.5

declare -A SIM_MAP  # worktree_path -> simulator_udid
AUTO_MODE=false

# ── Parse arguments ──
if [[ "${1:-}" == "--auto" ]]; then
  AUTO_MODE=true
  shift
else
  for pair in "$@"; do
    wt="${pair%%:*}"
    sim="${pair##*:}"
    SIM_MAP["$wt"]="$sim"
  done
fi

# ── Auto-discover worktrees that have a .moat-simulator-udid file ──
refresh_worktrees() {
  if [[ "$AUTO_MODE" != true ]]; then
    return
  fi
  while IFS= read -r line; do
    # git worktree list --porcelain outputs "worktree <path>" lines
    if [[ "$line" == worktree\ * ]]; then
      local wt="${line#worktree }"
      local udid_file="$wt/.moat-simulator-udid"
      if [[ -f "$udid_file" ]] && [[ -z "${SIM_MAP[$wt]+x}" ]]; then
        SIM_MAP["$wt"]="$(cat "$udid_file")"
        echo "[bridge] discovered worktree: $wt → ${SIM_MAP[$wt]}"
      fi
    fi
  done < <(git worktree list --porcelain 2>/dev/null || true)
}

# ── Process a single build request ──
process_request() {
  local wt_path="$1"
  local sim_udid="$2"
  local req="$wt_path/.moat-build-req"
  local res="$wt_path/.moat-build-res"

  [[ ! -f "$req" ]] && return

  local action
  action=$(cat "$req")
  rm -f "$req"

  echo "[$(date +%H:%M:%S)] $wt_path: $action"

  local exit_code=0
  local output=""

  if [[ "$action" == simctl\ * ]]; then
    # xcrun simctl passthrough
    local simctl_args="${action#simctl }"
    output=$(xcrun simctl $simctl_args 2>&1) || exit_code=$?
  else
    # xcodebuild — run from within the worktree so relative paths work
    output=$(
      cd "$wt_path" && \
      xcodebuild \
        -project "$PROJECT" \
        -scheme "$SCHEME" \
        -destination "id=$sim_udid" \
        $action 2>&1
    ) || exit_code=$?
  fi

  # Write result: first line is exit code, rest is truncated output
  {
    echo "$exit_code"
    echo "$output" | tail -"$OUTPUT_LINES"
  } > "$res"

  if [[ "$exit_code" -eq 0 ]]; then
    echo "[$(date +%H:%M:%S)] $wt_path: ✓ success"
  else
    echo "[$(date +%H:%M:%S)] $wt_path: ✗ failed (exit $exit_code)"
  fi
}

# ── Cleanup on exit ──
cleanup() {
  echo ""
  echo "[bridge] shutting down..."
  # Remove any pending request files so shims don't hang
  for wt_path in "${!SIM_MAP[@]}"; do
    rm -f "$wt_path/.moat-build-req" "$wt_path/.moat-build-res" "$wt_path/.moat-build-lock"
  done
}
trap cleanup EXIT

# ── Main loop ──
echo "ios-build-bridge: project=$PROJECT scheme=$SCHEME"
echo "Polling every ${POLL_INTERVAL}s..."
if [[ "$AUTO_MODE" == true ]]; then
  echo "Auto-discovery mode: watching for .moat-simulator-udid files in worktrees"
fi
echo "Press Ctrl-C to stop."
echo ""

tick=0
while true; do
  # Re-scan for new worktrees every ~5 seconds in auto mode
  if [[ "$AUTO_MODE" == true ]] && (( tick % 10 == 0 )); then
    refresh_worktrees
  fi

  for wt_path in "${!SIM_MAP[@]}"; do
    process_request "$wt_path" "${SIM_MAP[$wt_path]}"
  done

  sleep "$POLL_INTERVAL"
  tick=$((tick + 1))
done
