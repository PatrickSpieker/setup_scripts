#!/bin/bash
set -euo pipefail

PID_FILE="/tmp/xcode-proxy.pid"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Xcode MCP proxy stopped (PID: $PID)."
  else
    echo "PID $PID not running."
  fi
  rm -f "$PID_FILE"
else
  echo "No PID file found."
fi
