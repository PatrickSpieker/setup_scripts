#!/usr/bin/env PYTHONIOENCODING=UTF-8 python3
# -*- coding: utf-8 -*-

# <xbar.title>AI Token Leaderboard</xbar.title>
# <xbar.version>v2.0</xbar.version>
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
# Bump the major here after eyeballing a real `ccusage daily --json` and
# confirming the schema in tests/fixtures/ccusage_daily.json still matches.
CCUSAGE_PKG = "ccusage@19"

# Fields every ccusage daily record must carry. If any record is missing one,
# the schema has drifted and we render a loud error instead of silent zeros.
REQUIRED_FIELDS = ("period", "totalCost", "metadata")

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


def fetch_usage(timeout=30):
    """Run `ccusage daily --since … --json` for the last 30 days.

    Returns the list of daily records. Raises CcusageError for any failure
    mode — non-zero exit, empty stdout, non-JSON stdout (the deprecation-message
    failure mode that bit us last time lands here), or records missing
    REQUIRED_FIELDS. The caller renders an error sentinel in the menu bar.
    """
    npx = find_npx()
    env = os.environ.copy()
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    since = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    try:
        result = subprocess.run(
            [npx, "-y", CCUSAGE_PKG, "daily", "--since", since, "--json"],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise CcusageError(f"npx failed: {e}") from e

    if result.returncode != 0:
        raise CcusageError(f"ccusage exit {result.returncode}: {result.stderr.strip()[:200]}")

    stdout = result.stdout.strip()
    if not stdout:
        raise CcusageError("ccusage returned empty stdout")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CcusageError(f"ccusage stdout was not JSON: {stdout[:120]}") from e

    return parse_records(data)


def parse_records(data):
    """Validate and unwrap a parsed ccusage daily response.

    Split out from fetch_usage so tests can hit it directly with a fixture
    without shelling out to npx. Empty record lists are allowed (means "no
    usage in the last 30 days"); the schema check only fires when records
    exist but don't match what we expect.
    """
    records = data.get("daily") if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise CcusageError(f"unexpected ccusage shape: top-level was {type(data).__name__}")
    if records:
        missing = [f for f in REQUIRED_FIELDS if f not in records[0]]
        if missing:
            raise CcusageError(
                f"ccusage record missing fields {missing}; "
                f"got keys {sorted(records[0])[:8]}"
            )
    return records


def agents_of(record):
    """Return the set of agents that contributed to a daily record.

    ccusage v19 emits one record per date with `metadata.agents` listing
    every agent that ran that day. A mixed-agent day (`["claude", "codex"]`)
    has aggregated totals with no per-agent split available, so callers
    that bucket by agent need to decide what to do — see bucket_by_agent.
    """
    return set((record.get("metadata") or {}).get("agents") or [])


def bucket_by_agent(records):
    """Tag each record with every agent that contributed to it.

    Mixed-agent records land in BOTH buckets. That intentionally
    overcounts per-agent totals on mixed days (claude_today + codex_today
    can exceed total_today) — but ccusage doesn't expose a per-agent split
    for mixed days, so this is the most honest we can be. Use the full
    record list for day/month/total figures; use the buckets only for
    per-agent rows.
    """
    buckets = {"claude": [], "codex": []}
    for r in records:
        a = agents_of(r)
        for name in ("claude", "codex"):
            if name in a:
                buckets[name].append(r)
    return buckets


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

    The previous version swallowed ccusage failures and rendered $0.00, which
    was indistinguishable from "you didn't use any AI today." This makes
    upstream breakage visible at a glance.
    """
    print(f"⚡ ccusage? | color={COLOR_ERR} {FONT_MONO}")
    print("---")
    print(f"ccusage fetch failed | color={COLOR_ERR} {FONT_LABEL}")
    print(f"{err} | color={COLOR_DIM} {FONT_SMALL}")
    print("---")
    print("Refresh | refresh=true")


def _print_agent_today(emoji, name, totals, color):
    if totals["cost"] > 0:
        print(f"{emoji}  {name}: {fmt_cost(totals['cost'])} | {FONT_LABEL} color={color}")
        print(f"--Output: {fmt_tokens(totals['output'])} tokens | {FONT_SMALL} color={COLOR_DIM}")
        if totals["cache_read"] > 0 or totals["cache_create"] > 0:
            print(f"--Cache: {fmt_tokens(totals['cache_read'])} read / "
                  f"{fmt_tokens(totals['cache_create'])} created | {FONT_SMALL} color={COLOR_DIM}")
    else:
        print(f"{emoji}  {name}: {fmt_cost(0)} | {FONT_SMALL} color={COLOR_DIM}")


def render():
    try:
        records = fetch_usage()
    except CcusageError as e:
        render_error(e)
        return

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    by_agent = bucket_by_agent(records)

    # Per-agent rows can overcount on mixed days. Day/month totals always
    # come from the full record list so the menu bar number is exact.
    claude_today = extract_totals(by_agent["claude"], period_filter=today)
    codex_today  = extract_totals(by_agent["codex"],  period_filter=today)
    claude_month = extract_totals(by_agent["claude"], period_filter=month)
    codex_month  = extract_totals(by_agent["codex"],  period_filter=month)
    combined_today = extract_totals(records, period_filter=today)["cost"]
    combined_month = extract_totals(records, period_filter=month)["cost"]

    # ── Menu bar ────────────────────────────────────────────────────────
    print(f"⚡ {fmt_cost(combined_today)} | {FONT_MONO}")
    print("---")

    # ── TODAY ───────────────────────────────────────────────────────────
    print(f"📊  TODAY ({today}) | {FONT_LABEL} color={COLOR_HEADER}")
    print("---")
    _print_agent_today("🟠", "Claude Code", claude_today, COLOR_CLAUDE)
    _print_agent_today("🟢", "Codex", codex_today, COLOR_CODEX)
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
        ct = extract_totals(by_agent["claude"], period_filter=d)
        cx = extract_totals(by_agent["codex"], period_filter=d)
        day_cost = extract_totals(records, period_filter=d)["cost"]
        if day_cost > 0:
            bar_total = ct["cost"] + cx["cost"]
            c_pct = ct["cost"] / bar_total if bar_total else 0
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
