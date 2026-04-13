#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="${XCODE_PROXY_REPO:?Set XCODE_PROXY_REPO to the main git repo path}"
PID_FILE="/tmp/xcode-proxy.pid"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Xcode MCP proxy already running (PID: $(cat "$PID_FILE"))"
  exit 0
fi

pip3 install -q -r "$SCRIPT_DIR/requirements.txt"

XCODE_PROXY_REPO="$REPO" python3 "$SCRIPT_DIR/server.py" &
echo $! > "$PID_FILE"
echo "Xcode MCP proxy started on http://localhost:9400/mcp (PID: $(cat "$PID_FILE"))"
