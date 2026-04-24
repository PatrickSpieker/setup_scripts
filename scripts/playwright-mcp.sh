#!/usr/bin/env bash
# Launcher for @playwright/mcp inside a Moat container.
#
# The MCP defaults to the Chrome (proprietary) channel, which is NOT installed
# in our rootless Apple runtime. `post_build` installs the bundled Chromium
# via `npx playwright install chromium`, but the resulting path is versioned
# (e.g. chromium-1217/chrome-linux/chrome), so we resolve it at launch time
# and inject `--executable-path` before handing off to the real MCP.
set -euo pipefail

CHROMIUM="$(find "$HOME/.cache/ms-playwright" -type f -path '*/chrome-linux/chrome' 2>/dev/null | head -1)"
if [[ -z "$CHROMIUM" ]]; then
  echo "playwright-mcp.sh: no chromium found under $HOME/.cache/ms-playwright — did post_build run 'playwright install chromium'?" >&2
  exit 1
fi

exec npx -y @playwright/mcp@latest --executable-path "$CHROMIUM" "$@"
