#!/usr/bin/env bash
# Launch installed Chrome in Moat, preserving its authenticated proxy bridge.
# The image must provide stable Chrome and support Chrome's sandbox.
# EXTRA_CHROMIUM_ARGS supplies project-specific flags, as before.
set -euo pipefail

LOCAL_PROXY_PID=
PORT_FILE=
CONFIG=
cleanup() {
  if [[ -n "${LOCAL_PROXY_PID:-}" ]]; then
    kill "$LOCAL_PROXY_PID" 2>/dev/null || true
  fi
  [[ -z "$PORT_FILE" ]] || rm -f "$PORT_FILE"
  [[ -z "$CONFIG" ]] || rm -f "$CONFIG"
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

CONFIG="$(mktemp)"
PROXY_PORT="$PROXY_PORT" EXTRA_CHROMIUM_ARGS="${EXTRA_CHROMIUM_ARGS:-}" node -e '
  const fs = require("fs");
  const args = [];
  if (process.env.PROXY_PORT) {
    args.push("--proxy-server=http://127.0.0.1:" + process.env.PROXY_PORT);
    args.push("--ignore-certificate-errors");
  }
  // Project-specific Chromium flags from moat.yaml. Whitespace-separated;
  // empty / unset env var = no extra args, preserving prior behavior.
  const extra = (process.env.EXTRA_CHROMIUM_ARGS || "").trim();
  if (extra) args.push(...extra.split(/\s+/));
  fs.writeFileSync(process.argv[1], JSON.stringify({
    browser: {
      isolated: true,
      launchOptions: {
        channel: "chrome",
        chromiumSandbox: true,
        headless: true,
        args,
      },
    },
  }));
' "$CONFIG"

npx -y @playwright/mcp@latest --config "$CONFIG" "$@" --browser chrome --sandbox
