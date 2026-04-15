#!/usr/bin/env python3
"""Localhost web viewer for Claude Code plan files with notes, repo filtering, and live updates."""

from __future__ import annotations

import json
import os
import socketserver
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import typer

app = typer.Typer(help="Serve a localhost plan viewer for Claude Code plans.")

# --- Defaults (overridable via CLI) ---
PLANS_DIR = Path.home() / ".claude" / "plans"
PROJECTS_DIR = Path.home() / ".claude" / "projects"
HISTORY_FILE = Path.home() / ".claude" / "history.jsonl"
NOTES_FILE = Path.home() / ".claude" / "plan-viewer-notes.json"

# --- Global state ---
plan_index: dict[str, dict] = {}
sse_connections: list = []
sse_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Plan-repo index builder
# ---------------------------------------------------------------------------

def build_plan_index() -> dict[str, dict]:
    """Scan session JSONL files to map plan slugs to repo/project metadata."""
    index: dict[str, dict] = {}

    if not PROJECTS_DIR.exists():
        return index

    # Walk all session JSONL files
    for jsonl_path in PROJECTS_DIR.rglob("*.jsonl"):
        try:
            with open(jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or "plan_mode" not in line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") != "attachment":
                        continue
                    att = entry.get("attachment", {})
                    if att.get("type") != "plan_mode":
                        continue
                    plan_path = att.get("planFilePath", "")
                    slug = Path(plan_path).stem if plan_path else entry.get("slug", "")
                    if not slug:
                        continue
                    index[slug] = {
                        "slug": slug,
                        "planFilePath": plan_path,
                        "cwd": entry.get("cwd", ""),
                        "gitBranch": entry.get("gitBranch", ""),
                        "sessionId": entry.get("sessionId", ""),
                    }
        except (OSError, PermissionError):
            continue

    # Enrich with display text from history.jsonl
    if HISTORY_FILE.exists():
        session_displays: dict[str, str] = {}
        try:
            with open(HISTORY_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    sid = entry.get("sessionId", "")
                    display = entry.get("display", "")
                    if sid and display:
                        # Keep first non-command display per session
                        if sid not in session_displays and not display.startswith("/"):
                            session_displays[sid] = display
            for slug, meta in index.items():
                sid = meta.get("sessionId", "")
                if sid in session_displays:
                    meta["display"] = session_displays[sid]
        except (OSError, PermissionError):
            pass

    return index


# ---------------------------------------------------------------------------
# Notes persistence
# ---------------------------------------------------------------------------

def load_notes() -> dict[str, str]:
    if not NOTES_FILE.exists():
        return {}
    try:
        return json.loads(NOTES_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_note(slug: str, text: str) -> None:
    notes = load_notes()
    notes[slug] = text
    tmp = NOTES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(notes, indent=2))
    os.replace(tmp, NOTES_FILE)


# ---------------------------------------------------------------------------
# SSE infrastructure
# ---------------------------------------------------------------------------

def broadcast(event_type: str, data: dict) -> None:
    payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    dead = []
    with sse_lock:
        for wfile in sse_connections:
            try:
                wfile.write(payload.encode())
                wfile.flush()
            except Exception:
                dead.append(wfile)
        for d in dead:
            sse_connections.remove(d)


# ---------------------------------------------------------------------------
# File watcher thread
# ---------------------------------------------------------------------------

def watch_plans() -> None:
    """Watch PLANS_DIR for changes and broadcast SSE events."""
    from watchfiles import watch, Change

    for changes in watch(PLANS_DIR):
        for change_type, path_str in changes:
            path = Path(path_str)
            if path.suffix != ".md":
                continue
            slug = path.stem
            content = None
            if change_type != Change.deleted and path.exists():
                try:
                    content = path.read_text()
                except OSError:
                    content = None
            broadcast("plan_changed", {
                "slug": slug,
                "content": content,
                "change": change_type.name if hasattr(change_type, "name") else str(change_type),
            })


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class PlanHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default access logs
        pass

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path == "/":
            self._send_html(HTML_PAGE)

        elif path == "/api/plans":
            self._handle_list_plans()

        elif path.startswith("/api/plans/"):
            slug = path[len("/api/plans/"):]
            self._handle_get_plan(slug)

        elif path == "/api/reindex":
            global plan_index
            plan_index = build_plan_index()
            self._handle_list_plans()

        elif path == "/events":
            self._handle_sse()

        else:
            self.send_error(404)

    def do_POST(self) -> None:
        path = self.path.split("?")[0]

        if path.startswith("/api/notes/"):
            slug = path[len("/api/notes/"):]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode() if length else ""
            try:
                data = json.loads(body)
                text = data.get("text", "")
            except json.JSONDecodeError:
                text = body
            save_note(slug, text)
            self._send_json({"ok": True})
        else:
            self.send_error(404)

    def _handle_list_plans(self) -> None:
        plans = []
        if PLANS_DIR.exists():
            for p in sorted(PLANS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                slug = p.stem
                meta = plan_index.get(slug, {})
                plans.append({
                    "slug": slug,
                    "filename": p.name,
                    "mtime": p.stat().st_mtime,
                    "cwd": meta.get("cwd", ""),
                    "gitBranch": meta.get("gitBranch", ""),
                    "display": meta.get("display", ""),
                })
        self._send_json(plans)

    def _handle_get_plan(self, slug: str) -> None:
        plan_path = PLANS_DIR / f"{slug}.md"
        if not plan_path.exists():
            self._send_json({"error": "not found"}, 404)
            return
        content = plan_path.read_text()
        notes = load_notes()
        meta = plan_index.get(slug, {})
        self._send_json({
            "slug": slug,
            "content": content,
            "notes": notes.get(slug, ""),
            "meta": meta,
        })

    def _handle_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with sse_lock:
            sse_connections.append(self.wfile)

        # Send initial connected event
        try:
            self.wfile.write(b"event: connected\ndata: {}\n\n")
            self.wfile.flush()
        except Exception:
            return

        # Keep alive
        try:
            while True:
                time.sleep(30)
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except Exception:
            pass
        finally:
            with sse_lock:
                if self.wfile in sse_connections:
                    sse_connections.remove(self.wfile)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


# ---------------------------------------------------------------------------
# Embedded HTML/CSS/JS
# ---------------------------------------------------------------------------

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plan Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    background: #1a1a2e; color: #e0e0e0; height: 100vh;
    display: grid; grid-template-columns: 260px 1fr 320px;
  }

  /* Sidebar */
  .sidebar {
    background: #16213e; border-right: 1px solid #2a2a4a;
    display: flex; flex-direction: column; overflow: hidden;
  }
  .sidebar-header { padding: 16px; border-bottom: 1px solid #2a2a4a; }
  .sidebar-header h1 { font-size: 14px; font-weight: 600; color: #a0a0c0; margin-bottom: 10px; }
  .search-box {
    width: 100%; padding: 8px 10px; background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 4px; color: #e0e0e0; font-size: 13px; outline: none;
  }
  .search-box:focus { border-color: #5a5a8a; }
  .search-box::placeholder { color: #555; }
  .plan-list { flex: 1; overflow-y: auto; }
  .plan-item {
    padding: 10px 16px; cursor: pointer; border-bottom: 1px solid #1a1a2e;
    transition: background 0.15s;
  }
  .plan-item:hover { background: #1a1a2e; }
  .plan-item.active { background: #0f3460; border-left: 3px solid #e94560; }
  .plan-item .plan-name {
    font-size: 13px; font-weight: 500; color: #c0c0e0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .plan-item .plan-repo {
    font-size: 11px; color: #666; margin-top: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .plan-item .plan-time {
    font-size: 10px; color: #555; margin-top: 2px;
  }

  /* Main content */
  .content {
    overflow-y: auto; padding: 32px 40px;
    border-right: 1px solid #2a2a4a;
  }
  .content .empty-state {
    color: #555; text-align: center; margin-top: 120px; font-size: 14px;
  }
  /* Markdown styles */
  .content h1 { font-size: 22px; color: #e94560; margin: 0 0 16px; border-bottom: 1px solid #2a2a4a; padding-bottom: 8px; }
  .content h2 { font-size: 18px; color: #a0a0c0; margin: 24px 0 12px; }
  .content h3 { font-size: 15px; color: #8080a0; margin: 20px 0 8px; }
  .content p { line-height: 1.6; margin: 8px 0; }
  .content ul, .content ol { margin: 8px 0 8px 24px; }
  .content li { line-height: 1.6; margin: 4px 0; }
  .content code {
    background: #2a2a4a; padding: 2px 6px; border-radius: 3px;
    font-size: 13px; font-family: "SF Mono", Monaco, monospace;
  }
  .content pre {
    background: #0d1117; border: 1px solid #2a2a4a; border-radius: 6px;
    padding: 16px; overflow-x: auto; margin: 12px 0;
  }
  .content pre code { background: none; padding: 0; }
  .content table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  .content th, .content td {
    border: 1px solid #2a2a4a; padding: 8px 12px; text-align: left; font-size: 13px;
  }
  .content th { background: #16213e; color: #a0a0c0; }
  .content blockquote {
    border-left: 3px solid #e94560; padding: 8px 16px; margin: 12px 0;
    background: #16213e; color: #a0a0c0;
  }
  .content a { color: #5dade2; }

  /* Notes panel */
  .notes {
    background: #16213e; display: flex; flex-direction: column; overflow: hidden;
  }
  .notes-header {
    padding: 16px; border-bottom: 1px solid #2a2a4a;
    display: flex; align-items: center; justify-content: space-between;
  }
  .notes-header h2 { font-size: 14px; font-weight: 600; color: #a0a0c0; }
  .save-indicator { font-size: 11px; color: #555; transition: color 0.3s; }
  .save-indicator.saved { color: #27ae60; }
  .notes textarea {
    flex: 1; width: 100%; padding: 16px; background: #1a1a2e; border: none;
    color: #e0e0e0; font-size: 13px; font-family: inherit; resize: none;
    line-height: 1.6; outline: none;
  }
  .notes textarea::placeholder { color: #444; }
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">
    <h1>Plan Viewer</h1>
    <input type="text" class="search-box" id="search" placeholder="Search plans or /repo/path...">
  </div>
  <div class="plan-list" id="plan-list"></div>
</div>

<div class="content" id="content">
  <div class="empty-state">Select a plan from the sidebar</div>
</div>

<div class="notes">
  <div class="notes-header">
    <h2>Notes</h2>
    <span class="save-indicator" id="save-indicator"></span>
  </div>
  <textarea id="notes" placeholder="Write notes here..."></textarea>
</div>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
(function() {
  const planList = document.getElementById('plan-list');
  const content = document.getElementById('content');
  const notesEl = document.getElementById('notes');
  const searchEl = document.getElementById('search');
  const saveIndicator = document.getElementById('save-indicator');

  let plans = [];
  let currentSlug = null;
  let saveTimeout = null;

  // Configure marked if available, else fallback to <pre>
  const renderMd = typeof marked !== 'undefined'
    ? (md) => marked.parse(md)
    : (md) => '<pre>' + md.replace(/</g, '&lt;') + '</pre>';

  function timeAgo(ts) {
    const diff = (Date.now() / 1000) - ts;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  }

  function repoName(cwd) {
    if (!cwd) return '';
    const parts = cwd.split('/');
    return parts[parts.length - 1] || cwd;
  }

  function renderPlanList(filter) {
    const q = (filter || '').toLowerCase();
    planList.innerHTML = '';
    const filtered = plans.filter(p => {
      if (!q) return true;
      return p.slug.toLowerCase().includes(q)
        || (p.cwd && p.cwd.toLowerCase().includes(q))
        || (p.display && p.display.toLowerCase().includes(q));
    });
    if (filtered.length === 0) {
      planList.innerHTML = '<div style="padding:16px;color:#555;font-size:13px;">No plans found</div>';
      return;
    }
    filtered.forEach(p => {
      const div = document.createElement('div');
      div.className = 'plan-item' + (p.slug === currentSlug ? ' active' : '');
      div.innerHTML =
        '<div class="plan-name">' + p.slug + '</div>' +
        (p.cwd ? '<div class="plan-repo">' + repoName(p.cwd) + ' &mdash; ' + p.cwd + '</div>' : '') +
        '<div class="plan-time">' + timeAgo(p.mtime) + '</div>';
      div.addEventListener('click', () => selectPlan(p.slug));
      planList.appendChild(div);
    });
  }

  function selectPlan(slug) {
    currentSlug = slug;
    renderPlanList(searchEl.value);
    fetch('/api/plans/' + encodeURIComponent(slug))
      .then(r => r.json())
      .then(data => {
        content.innerHTML = renderMd(data.content || '*(empty plan)*');
        notesEl.value = data.notes || '';
        notesEl.disabled = false;
      });
  }

  function loadPlans() {
    fetch('/api/plans')
      .then(r => r.json())
      .then(data => {
        plans = data;
        renderPlanList(searchEl.value);
      });
  }

  // Search
  searchEl.addEventListener('input', () => renderPlanList(searchEl.value));

  // Notes auto-save
  notesEl.addEventListener('input', () => {
    if (!currentSlug) return;
    saveIndicator.textContent = '';
    saveIndicator.className = 'save-indicator';
    clearTimeout(saveTimeout);
    const slug = currentSlug;
    const text = notesEl.value;
    saveTimeout = setTimeout(() => {
      fetch('/api/notes/' + encodeURIComponent(slug), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: text}),
      }).then(() => {
        saveIndicator.textContent = 'saved';
        saveIndicator.className = 'save-indicator saved';
        setTimeout(() => { saveIndicator.textContent = ''; }, 2000);
      });
    }, 500);
  });

  // SSE for live updates
  const es = new EventSource('/events');
  es.addEventListener('plan_changed', (e) => {
    const data = JSON.parse(e.data);
    // Refresh plan list
    loadPlans();
    // If viewing this plan, update content
    if (data.slug === currentSlug && data.content != null) {
      content.innerHTML = renderMd(data.content);
    }
  });

  // Initial load
  loadPlans();
  notesEl.disabled = true;
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

@app.command()
def serve(
    port: int = typer.Option(8787, help="Port to serve on"),
    plans_dir: Path = typer.Option(None, help="Plans directory override"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser on start"),
) -> None:
    """Start the plan viewer server."""
    global PLANS_DIR, plan_index

    if plans_dir:
        PLANS_DIR = plans_dir

    if not PLANS_DIR.exists():
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Created plans directory: {PLANS_DIR}")

    typer.echo("Building plan index...")
    plan_index = build_plan_index()
    typer.echo(f"Indexed {len(plan_index)} plan(s)")

    # Start file watcher
    watcher = threading.Thread(target=watch_plans, daemon=True)
    watcher.start()

    # Start server
    server = ThreadedHTTPServer(("", port), PlanHandler)
    url = f"http://localhost:{port}"
    typer.echo(f"Plan viewer running at {url}")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("\nShutting down.")
        server.shutdown()


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
