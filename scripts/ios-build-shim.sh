#!/bin/bash
# ios-build-shim: bridges xcodebuild/simctl calls from a Moat container to the host.
#
# Inside the container there is no Xcode toolchain.  This shim writes a
# request file to /workspace and blocks until the host-side bridge
# (ios-build-bridge.sh) processes it and writes a result file back.
#
# Usage:
#   ios-build build                 # xcodebuild build
#   ios-build test                  # xcodebuild test
#   ios-build clean build           # xcodebuild clean build
#   ios-build simctl <args...>      # xcrun simctl <args...>
#
# The shim is installed by the moat pre_run hook:
#   cp /workspace/scripts/ios-build-shim.sh /usr/local/bin/ios-build
#   chmod +x /usr/local/bin/ios-build

set -euo pipefail

REQ="/workspace/.moat-build-req"
RES="/workspace/.moat-build-res"
LOCK="/workspace/.moat-build-lock"
TIMEOUT=300  # seconds

# ── Guard against concurrent requests from the same container ──
acquire_lock() {
  local waited=0
  while [ -f "$LOCK" ]; do
    sleep 1
    waited=$((waited + 1))
    if [ "$waited" -ge "$TIMEOUT" ]; then
      echo "ERROR: timed out waiting for lock (another build may be stuck)" >&2
      exit 1
    fi
  done
  echo $$ > "$LOCK"
}

release_lock() {
  rm -f "$LOCK"
}
trap release_lock EXIT

# ── Main ──
if [ $# -eq 0 ]; then
  echo "Usage: ios-build <build|test|clean|simctl> [args...]" >&2
  exit 1
fi

acquire_lock

# Clean up any stale result from a previous run
rm -f "$RES"

# Write the request — the bridge reads the full line as the action
echo "$*" > "$REQ"
echo "⏳ Waiting for host build bridge..." >&2

# Poll for the result file
elapsed=0
while [ ! -f "$RES" ]; do
  sleep 1
  elapsed=$((elapsed + 1))
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "ERROR: Build bridge timed out after ${TIMEOUT}s." >&2
    echo "Is ios-build-bridge.sh running on the host?" >&2
    rm -f "$REQ"
    exit 1
  fi
done

# First line of the result is the exit code; the rest is output
exit_code=$(head -1 "$RES")
tail -n +2 "$RES"
rm -f "$RES"

exit "$exit_code"
