#!/usr/bin/env bash
# Launcher for @playwright/mcp inside a Moat container.
#
# Three things this handles that the MCP can't on its own:
# 1. Resolves the bundled Chromium binary. post_build runs
#    `npx playwright install chromium`, which lays it down at a versioned
#    path under ~/.cache/ms-playwright/chromium-<rev>/. The MCP defaults to
#    the proprietary Chrome channel, which isn't installed in the rootless
#    Apple runtime — so we point it at the bundled binary explicitly.
# 2. Bridges Moat's authenticated HTTPS_PROXY into Chromium. Chromium's
#    --proxy-server URL doesn't accept basic auth (ERR_NO_SUPPORTED_PROXIES),
#    and Playwright's proxy.{username,password} also fails against this
#    proxy with ERR_PROXY_AUTH_UNSUPPORTED. Workaround: spawn a tiny local
#    CONNECT-proxy that forwards to Moat's proxy with Proxy-Authorization
#    injected, point Chromium at the unauthenticated localhost endpoint.
# 3. Tells Chromium to ignore the Moat CA's intercepted certs. The proxy
#    still verifies the real upstream cert (per Moat docs / TLS interception
#    section), so this isn't loosening real network security.
#
# The MCP --config file is built fresh on each run; everything (executable
# path, headless, isolated, --no-sandbox, proxy server, ignore-cert) goes
# in there. moat.yaml's `args:` should be empty.
set -euo pipefail

CHROMIUM="$(find "$HOME/.cache/ms-playwright" -type f -path '*/chrome-linux/chrome' 2>/dev/null | head -1)"
if [[ -z "$CHROMIUM" ]]; then
  echo "playwright-mcp.sh: no chromium under $HOME/.cache/ms-playwright — did post_build run 'playwright install chromium'?" >&2
  exit 1
fi

LOCAL_PROXY_PID=
cleanup() {
  if [[ -n "${LOCAL_PROXY_PID:-}" ]]; then
    kill "$LOCAL_PROXY_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT TERM INT

PROXY_PORT=
UPSTREAM="${https_proxy:-${HTTPS_PROXY:-}}"
if [[ -n "$UPSTREAM" ]]; then
  PORT_FILE="$(mktemp)"
  https_proxy="$UPSTREAM" PORT_FILE="$PORT_FILE" node -e '
    const http = require("http"), net = require("net"), fs = require("fs");
    const u = new URL(process.env.https_proxy);
    const auth = "Basic " + Buffer.from(decodeURIComponent(u.username) + ":" + decodeURIComponent(u.password)).toString("base64");
    http.createServer()
      .on("connect", (req, c, head) => {
        const s = net.connect(+u.port, u.hostname, () => {
          s.write("CONNECT " + req.url + " HTTP/1.1\r\nHost: " + req.url + "\r\nProxy-Authorization: " + auth + "\r\n\r\n");
          s.once("data", d => {
            c.write(d);
            if (head && head.length) s.write(head);
            s.pipe(c); c.pipe(s);
          });
        });
        s.on("error", () => c.end());
        c.on("error", () => s.destroy());
      })
      .listen(0, "127.0.0.1", function () {
        fs.writeFileSync(process.env.PORT_FILE, String(this.address().port));
      });
  ' </dev/null >/dev/null 2>&1 &
  LOCAL_PROXY_PID=$!
  for _ in $(seq 1 50); do
    [[ -s "$PORT_FILE" ]] && break
    sleep 0.1
  done
  if [[ ! -s "$PORT_FILE" ]]; then
    echo "playwright-mcp.sh: local proxy failed to start within 5s" >&2
    exit 1
  fi
  PROXY_PORT="$(cat "$PORT_FILE")"
fi

CONFIG="$(mktemp --suffix=.json)"
EXE="$CHROMIUM" PROXY_PORT="$PROXY_PORT" node -e '
  const fs = require("fs");
  const args = ["--no-sandbox"];
  if (process.env.PROXY_PORT) {
    args.push("--proxy-server=http://127.0.0.1:" + process.env.PROXY_PORT);
    args.push("--ignore-certificate-errors");
  }
  fs.writeFileSync(process.argv[1], JSON.stringify({
    browser: {
      isolated: true,
      launchOptions: {
        executablePath: process.env.EXE,
        headless: true,
        args,
      },
    },
  }));
' "$CONFIG"

npx -y @playwright/mcp@latest --config "$CONFIG" "$@"
