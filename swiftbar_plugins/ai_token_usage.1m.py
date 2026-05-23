#!/usr/bin/env PYTHONIOENCODING=UTF-8 python3
# -*- coding: utf-8 -*-

# <xbar.title>AI Token Leaderboard</xbar.title>
# <xbar.version>v3.0</xbar.version>
# <xbar.author>Patrick Spieker</xbar.author>
# <xbar.desc>Token usage leaderboard for Claude Code and OpenAI Codex</xbar.desc>
# <xbar.dependencies>python,node</xbar.dependencies>
# <xbar.var>string(VAR_NPX_PATH="/usr/local/bin/npx"): Path to npx binary</xbar.var>

import json
import os
import subprocess
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
NPX = os.environ.get("VAR_NPX_PATH", "/usr/local/bin/npx")
NPX_CANDIDATES = [NPX, "/opt/homebrew/bin/npx", "/usr/local/bin/npx", "/usr/bin/npx"]

# Pinned to a major. Previous code used `@latest` for both `ccusage` and the
# now-deprecated `@ccusage/codex`; when ccusage v19 renamed `date` → `period`
# and folded the Codex CLI in, the menu bar silently rendered $0.00 for weeks.
# Bump the major here after eyeballing real `ccusage claude daily --json` /
# `ccusage codex daily --json` output and confirming the fixtures in
# tests/fixtures/ still match.
CCUSAGE_PKG = "ccusage@19"

# Per-agent ccusage subcommands. v19's *merged* `ccusage daily` collapses any
# day where both tools ran into ONE record tagged metadata.agents:[claude,codex]
# with a single combined cost and no per-agent split — so an agent-bucketing
# approach shows the full day's cost under both agents (they look identical).
# The per-agent subcommands are the only accurate source, but they disagree on
# field names, so each carries the keys needed to normalize it:
#   - cost_key:         claude → totalCost, codex → costUSD
#   - cache_read_key:   claude → cacheReadTokens, codex → cachedInputTokens
#   - cache_create_key: codex has no cache-creation concept (None → 0)
AGENTS = {
    "claude": {
        "subcmd": ["claude", "daily"],
        "cost_key": "totalCost",
        "cache_read_key": "cacheReadTokens",
        "cache_create_key": "cacheCreationTokens",
    },
    "codex": {
        "subcmd": ["codex", "daily"],
        "cost_key": "costUSD",
        "cache_read_key": "cachedInputTokens",
        "cache_create_key": None,
    },
}

# Colors
COLOR_CLAUDE = "#D97757"
COLOR_CODEX  = "#10A37F"
COLOR_HEADER = "#8B8B8B"
COLOR_TOTAL  = "#FFFFFF"
COLOR_DIM    = "#666666"
COLOR_ERR    = "#FF6B6B"
FONT_MONO    = "font=MenloBold size=12"
FONT_LABEL   = "font=Menlo size=11"
FONT_SMALL   = "font=Menlo size=10"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def find_npx():
    for path in NPX_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return "npx"


class CcusageError(Exception):
    """ccusage returned something unparseable or schema-incompatible."""


def fetch_agent(agent, timeout=30):
    """Run `ccusage <agent> daily --since … --json` for the last 30 days.

    Returns that agent's daily records, normalized to the canonical shape (see
    normalize). Raises CcusageError for any failure mode — non-zero exit, empty
    stdout, non-JSON stdout (the deprecation-message failure mode that bit us
    last time lands here), or records missing the agent's required raw fields.
    The caller renders an error sentinel in the menu bar.
    """
    spec = AGENTS[agent]
    npx = find_npx()
    env = os.environ.copy()
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    since = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    try:
        result = subprocess.run(
            [npx, "-y", CCUSAGE_PKG, *spec["subcmd"], "--since", since, "--json"],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise CcusageError(f"npx failed ({agent}): {e}") from e

    if result.returncode != 0:
        raise CcusageError(f"ccusage {agent} exit {result.returncode}: {result.stderr.strip()[:200]}")

    stdout = result.stdout.strip()
    if not stdout:
        raise CcusageError(f"ccusage {agent} returned empty stdout")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CcusageError(f"ccusage {agent} stdout was not JSON: {stdout[:120]}") from e

    raw = parse_records(data, required=("date", spec["cost_key"]))
    return normalize(raw, agent)


def parse_records(data, required=("date", "totalCost")):
    """Validate and unwrap a parsed ccusage per-agent daily response.

    Split out from fetch_agent so tests can hit it directly with a fixture
    without shelling out to npx. Empty record lists are allowed (means "no
    usage in the last 30 days"); the schema check only fires when records
    exist but don't carry the agent's `required` raw fields.
    """
    records = data.get("daily") if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise CcusageError(f"unexpected ccusage shape: top-level was {type(data).__name__}")
    if records:
        missing = [f for f in required if f not in records[0]]
        if missing:
            raise CcusageError(
                f"ccusage record missing fields {missing}; "
                f"got keys {sorted(records[0])[:8]}"
            )
    return records


def normalize(records, agent):
    """Map an agent's raw ccusage records to one canonical shape.

    The per-agent subcommands disagree on field names — `claude daily` uses
    totalCost / cacheReadTokens / cacheCreationTokens; `codex daily` uses
    costUSD / cachedInputTokens and has no cache-creation concept. Translate
    both to claude-style keys so extract_totals stays agent-agnostic. The
    canonical `period` key (vs the raw `date`) keeps period_filter prefixing
    identical to the rest of the plugin.
    """
    spec = AGENTS[agent]
    out = []
    for r in records:
        out.append({
            "period":              r.get("date", ""),
            "totalCost":           float(r.get(spec["cost_key"]) or 0),
            "inputTokens":         int(r.get("inputTokens") or 0),
            "outputTokens":        int(r.get("outputTokens") or 0),
            "cacheReadTokens":     int(r.get(spec["cache_read_key"]) or 0),
            "cacheCreationTokens": int(r.get(spec["cache_create_key"]) or 0),
            "totalTokens":         int(r.get("totalTokens") or 0),
        })
    return out


def extract_totals(records, period_filter=None):
    """Sum cost + tokens across records whose `period` matches the prefix.

    `period_filter` is a string prefix:
      "2026-05"    → whole month
      "2026-05-19" → single day
      None         → all records
    """
    out = {"cost": 0.0, "input": 0, "output": 0,
           "cache_read": 0, "cache_create": 0, "total": 0}
    for r in records:
        period = r.get("period", "")
        if period_filter and not period.startswith(period_filter):
            continue
        out["cost"]         += float(r.get("totalCost") or 0)
        out["input"]        += int(r.get("inputTokens") or 0)
        out["output"]       += int(r.get("outputTokens") or 0)
        out["cache_create"] += int(r.get("cacheCreationTokens") or 0)
        out["cache_read"]   += int(r.get("cacheReadTokens") or 0)
        out["total"]        += int(r.get("totalTokens") or 0)
    return out


def fmt_tokens(n):
    if n is None or n == 0:
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_cost(c):
    if c is None or c == 0:
        return "$0.00"
    if c >= 1:
        return f"${c:,.2f}"
    return f"${c:.3f}"


# ─── Render ───────────────────────────────────────────────────────────────────

def render_error(err):
    """Distinct error state — never let ccusage failure look like a quiet day.

    A previous version swallowed ccusage failures and rendered $0.00, which
    was indistinguishable from "you didn't use any AI today." This makes
    upstream breakage visible at a glance.
    """
    print(f"⚡ ccusage? | color={COLOR_ERR} {FONT_MONO}")
    print("---")
    print(f"ccusage fetch failed | color={COLOR_ERR} {FONT_LABEL}")
    print(f"{err} | color={COLOR_DIM} {FONT_SMALL}")
    print("---")
    print("Refresh | refresh=true")


def _print_agent_today(emoji, name, totals, color, show_cache_create=True):
    if totals["cost"] > 0:
        print(f"{emoji}  {name}: {fmt_cost(totals['cost'])} | {FONT_LABEL} color={color}")
        print(f"--Output: {fmt_tokens(totals['output'])} tokens | {FONT_SMALL} color={COLOR_DIM}")
        # Codex's ccusage record exposes only cache reads (cachedInputTokens);
        # it has no cache-creation metric, so suppress the "/ N created" half
        # rather than render a misleading "/ 0 created".
        if totals["cache_read"] > 0 or (show_cache_create and totals["cache_create"] > 0):
            cache = f"{fmt_tokens(totals['cache_read'])} read"
            if show_cache_create:
                cache += f" / {fmt_tokens(totals['cache_create'])} created"
            print(f"--Cache: {cache} | {FONT_SMALL} color={COLOR_DIM}")
    else:
        print(f"{emoji}  {name}: {fmt_cost(0)} | {FONT_SMALL} color={COLOR_DIM}")


def render():
    try:
        claude_records = fetch_agent("claude")
        codex_records  = fetch_agent("codex")
    except CcusageError as e:
        render_error(e)
        return

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # Each agent's records come from its own subcommand, so per-agent figures
    # are exact and combined totals are simply their sum — no mixed-day
    # double counting.
    claude_today = extract_totals(claude_records, period_filter=today)
    codex_today  = extract_totals(codex_records,  period_filter=today)
    claude_month = extract_totals(claude_records, period_filter=month)
    codex_month  = extract_totals(codex_records,  period_filter=month)
    combined_today = claude_today["cost"] + codex_today["cost"]
    combined_month = claude_month["cost"] + codex_month["cost"]

    # ── Menu bar ────────────────────────────────────────────────────────
    print(f"⚡ {fmt_cost(combined_today)} | {FONT_MONO}")
    print("---")

    # ── TODAY ───────────────────────────────────────────────────────────
    print(f"📊  TODAY ({today}) | {FONT_LABEL} color={COLOR_HEADER}")
    print("---")
    _print_agent_today("🟠", "Claude Code", claude_today, COLOR_CLAUDE,
                       show_cache_create=AGENTS["claude"]["cache_create_key"] is not None)
    _print_agent_today("🟢", "Codex", codex_today, COLOR_CODEX,
                       show_cache_create=AGENTS["codex"]["cache_create_key"] is not None)
    print("---")
    print(f"Today: {fmt_cost(combined_today)} | {FONT_LABEL} color={COLOR_TOTAL}")

    # ── THIS MONTH ──────────────────────────────────────────────────────
    print("---")
    print(f"📅  THIS MONTH | {FONT_LABEL} color={COLOR_HEADER}")
    print("---")
    entries = []
    if claude_month["cost"] > 0:
        entries.append(("Claude Code", claude_month, COLOR_CLAUDE))
    if codex_month["cost"] > 0:
        entries.append(("Codex", codex_month, COLOR_CODEX))
    entries.sort(key=lambda e: e[1]["cost"], reverse=True)
    if entries:
        for rank, (name, stats, color) in enumerate(entries, 1):
            medal = {1: "🥇", 2: "🥈"}.get(rank, f"#{rank}")
            print(f"{medal}  {name}: {fmt_cost(stats['cost'])} | {FONT_LABEL} color={color}")
            print(f"--Output: {fmt_tokens(stats['output'])} tokens | {FONT_SMALL} color={COLOR_DIM}")
        print("---")
        print(f"Month total: {fmt_cost(combined_month)} | {FONT_LABEL} color={COLOR_TOTAL}")
    else:
        print(f"No usage data this month | {FONT_SMALL} color={COLOR_DIM}")

    # ── LAST 7 DAYS ─────────────────────────────────────────────────────
    print("---")
    print(f"📊  LAST 7 DAYS | {FONT_LABEL} color={COLOR_HEADER}")
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        d_short = (datetime.now() - timedelta(days=i)).strftime("%a %m/%d")
        ct = extract_totals(claude_records, period_filter=d)
        cx = extract_totals(codex_records, period_filter=d)
        day_cost = ct["cost"] + cx["cost"]
        if day_cost > 0:
            c_pct = ct["cost"] / day_cost if day_cost else 0
            c_bar = "🟠" * max(1, round(c_pct * 8)) if ct["cost"] > 0 else ""
            x_bar = "🟢" * max(1, round((1 - c_pct) * 8)) if cx["cost"] > 0 else ""
            print(f"--{d_short}  {fmt_cost(day_cost):>7s}  {c_bar}{x_bar} | {FONT_SMALL}")
        else:
            print(f"--{d_short}  {'—':>7s} | {FONT_SMALL} color={COLOR_DIM}")

    # ── ACTIONS ─────────────────────────────────────────────────────────
    print("---")
    npx = find_npx()
    print(f"Open ccusage report… | shell={npx} param1=-y param2={CCUSAGE_PKG} terminal=true")
    print("---")
    print("Refresh | refresh=true")


if __name__ == "__main__":
    try:
        render()
    except Exception as e:
        # Last-resort fallback if render_error itself blew up. Should not
        # happen in normal operation.
        print(f"⚡ err | color={COLOR_ERR} {FONT_MONO}")
        print("---")
        print(f"Unhandled: {e} | color={COLOR_ERR} {FONT_SMALL}")
        print("---")
        print("Refresh | refresh=true")
