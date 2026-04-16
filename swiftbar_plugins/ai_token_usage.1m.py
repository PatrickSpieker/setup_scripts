#!/usr/bin/env PYTHONIOENCODING=UTF-8 python3
# -*- coding: utf-8 -*-

# <xbar.title>AI Token Leaderboard</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Patrick Spieker</xbar.author>
# <xbar.desc>Token usage leaderboard for Claude Code and OpenAI Codex</xbar.desc>
# <xbar.dependencies>python,node</xbar.dependencies>
# <xbar.var>string(VAR_NPX_PATH="/usr/local/bin/npx"): Path to npx binary</xbar.var>

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
NPX = os.environ.get("VAR_NPX_PATH", "/usr/local/bin/npx")
# Fallback paths to try if the configured one doesn't exist
NPX_CANDIDATES = [NPX, "/opt/homebrew/bin/npx", "/usr/local/bin/npx", "/usr/bin/npx"]

# Per-token USD pricing used when ccusage/LiteLLM returns cost=0 for a known
# model. Anthropic's public cache multipliers: cache-write = 1.25x input,
# cache-read = 0.1x input.
BACKFILL_PRICING = {
    "claude-opus-4-7": {
        "input":        5.00 / 1_000_000,
        "output":      25.00 / 1_000_000,
        "cache_create": 6.25 / 1_000_000,
        "cache_read":   0.50 / 1_000_000,
    },
}

# Colors
COLOR_CLAUDE = "#D97757"   # Anthropic orange
COLOR_CODEX  = "#10A37F"   # OpenAI green
COLOR_HEADER = "#8B8B8B"
COLOR_TOTAL  = "#FFFFFF"
COLOR_DIM    = "#666666"
FONT_MONO    = "font=MenloBold size=12"
FONT_LABEL   = "font=Menlo size=11"
FONT_SMALL   = "font=Menlo size=10"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def find_npx():
    """Find a working npx binary."""
    for path in NPX_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    # Last resort: rely on PATH
    return "npx"


def run_ccusage(tool_args, timeout=30):
    """Run a ccusage command and return parsed JSON or None."""
    npx = find_npx()
    env = os.environ.copy()
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    try:
        result = subprocess.run(
            [npx] + tool_args + ["--json"],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def fmt_tokens(n):
    """Format token count: 1234567 -> 1.2M, 12345 -> 12.3K."""
    if n is None or n == 0:
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_cost(c):
    """Format cost in USD."""
    if c is None or c == 0:
        return "$0.00"
    if c >= 100:
        return f"${c:,.0f}"
    if c >= 1:
        return f"${c:.2f}"
    return f"${c:.3f}"


def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")


def get_month_str():
    return datetime.now().strftime("%Y-%m")


# ─── Data fetching ────────────────────────────────────────────────────────────

def normalize_date(d):
    """Convert Codex date format '%b %d, %Y' (e.g. 'Apr 03, 2026') to ISO 8601 'YYYY-MM-DD'."""
    try:
        return datetime.strptime(d, "%b %d, %Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return d


def fetch_daily(tool_args):
    """Fetch daily usage from a ccusage tool. Returns list of daily records."""
    since = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    data = run_ccusage(tool_args + ["daily", "--since", since])
    if not data:
        return []
    # ccusage response format varies: Claude wraps as {"daily": [...], "totals": {...}},
    # while some versions may return a bare list of daily records.
    if isinstance(data, dict) and "daily" in data:
        records = data["daily"]
    elif isinstance(data, list):
        records = data
    else:
        return []
    # Normalize date formats (Codex uses "Mon DD, YYYY", Claude uses "YYYY-MM-DD")
    for r in records:
        if "date" in r:
            r["date"] = normalize_date(r["date"])
    return records


def fetch_claude_daily():
    return fetch_daily(["ccusage@latest"])


def fetch_codex_daily():
    return fetch_daily(["@ccusage/codex@latest"])


def _parse_cost(c):
    if isinstance(c, str):
        return float(c.replace("$", "").replace(",", "").strip() or "0")
    return float(c or 0)


def _breakdown_cost(mb):
    """Breakdown cost, backfilled from BACKFILL_PRICING when ccusage reports 0."""
    cost = _parse_cost(mb.get("cost", 0))
    if cost > 0:
        return cost
    rates = BACKFILL_PRICING.get(mb.get("modelName", ""))
    if not rates:
        return cost
    return (
        int(mb.get("inputTokens", 0) or 0) * rates["input"]
        + int(mb.get("outputTokens", 0) or 0) * rates["output"]
        + int(mb.get("cacheCreationTokens", 0) or 0) * rates["cache_create"]
        + int(mb.get("cacheReadTokens", 0) or 0) * rates["cache_read"]
    )


def _record_cost(r):
    breakdowns = r.get("modelBreakdowns") or []
    if breakdowns:
        return sum(_breakdown_cost(mb) for mb in breakdowns)
    return _parse_cost(r.get("totalCost", r.get("costUSD", r.get("cost", 0))))


def extract_totals(records, date_filter=None):
    """Sum up tokens and cost from a list of daily records.

    Actual ccusage JSON fields (camelCase):
      date, inputTokens, outputTokens, cacheCreationTokens,
      cacheReadTokens, totalTokens, totalCost
    """
    total_tokens = 0
    total_cost = 0.0
    input_tokens = 0
    output_tokens = 0
    cache_create = 0
    cache_read = 0

    for r in records:
        date = r.get("date", "")
        if date_filter and not date.startswith(date_filter):
            continue

        total_tokens += int(r.get("totalTokens", 0) or 0)
        input_tokens += int(r.get("inputTokens", 0) or 0)
        output_tokens += int(r.get("outputTokens", 0) or 0)
        cache_create += int(r.get("cacheCreationTokens", 0) or 0)
        cache_read += int(r.get("cacheReadTokens", 0) or 0)

        total_cost += _record_cost(r)

    return {
        "total": total_tokens,
        "input": input_tokens,
        "output": output_tokens,
        "cache_create": cache_create,
        "cache_read": cache_read,
        "cost": total_cost,
    }


# ─── Render ───────────────────────────────────────────────────────────────────

def render():
    today = get_today_str()
    month = get_month_str()

    # Fetch data
    claude_records = fetch_claude_daily()
    codex_records = fetch_codex_daily()

    # Today's numbers
    claude_today = extract_totals(claude_records, date_filter=today)
    codex_today = extract_totals(codex_records, date_filter=today)

    # This month's numbers
    claude_month = extract_totals(claude_records, date_filter=month)
    codex_month = extract_totals(codex_records, date_filter=month)

    # Combined today
    combined_cost_today = claude_today["cost"] + codex_today["cost"]

    # ── Menu bar: total cost today ───────────────────────────────────────
    print(f"⚡ {fmt_cost(combined_cost_today)} | {FONT_MONO}")
    print("---")

    # ── TODAY section ─────────────────────────────────────────────────────
    print(f"📊  TODAY ({today}) | {FONT_LABEL} color={COLOR_HEADER}")
    print(f"---")

    # Claude Code
    ct = claude_today
    if ct["cost"] > 0:
        print(f"🟠  Claude Code: {fmt_cost(ct['cost'])} | {FONT_LABEL} color={COLOR_CLAUDE}")
        print(f"--Output: {fmt_tokens(ct['output'])} tokens | {FONT_SMALL} color={COLOR_DIM}")
        print(f"--Cache: {fmt_tokens(ct['cache_read'])} read / {fmt_tokens(ct['cache_create'])} created | {FONT_SMALL} color={COLOR_DIM}")
        if ct.get("modelBreakdowns"):
            for mb in ct["modelBreakdowns"]:
                print(f"--{mb['modelName']}: {fmt_cost(mb['cost'])} | {FONT_SMALL} color={COLOR_DIM}")
    else:
        print(f"🟠  Claude Code: {fmt_cost(0)} | {FONT_SMALL} color={COLOR_DIM}")

    # Codex
    cx = codex_today
    if cx["cost"] > 0:
        print(f"🟢  Codex: {fmt_cost(cx['cost'])} | {FONT_LABEL} color={COLOR_CODEX}")
        print(f"--Output: {fmt_tokens(cx['output'])} tokens | {FONT_SMALL} color={COLOR_DIM}")
        if cx["cache_read"] > 0 or cx["cache_create"] > 0:
            print(f"--Cache: {fmt_tokens(cx['cache_read'])} read / {fmt_tokens(cx['cache_create'])} created | {FONT_SMALL} color={COLOR_DIM}")
    else:
        print(f"🟢  Codex: {fmt_cost(0)} | {FONT_SMALL} color={COLOR_DIM}")

    # Today total
    print(f"---")
    print(f"Today: {fmt_cost(combined_cost_today)} | {FONT_LABEL} color={COLOR_TOTAL}")

    # ── THIS MONTH ────────────────────────────────────────────────────────
    print(f"---")
    combined_cost_month = claude_month["cost"] + codex_month["cost"]
    print(f"📅  THIS MONTH | {FONT_LABEL} color={COLOR_HEADER}")
    print(f"---")

    # Rank by cost
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
        print(f"---")
        print(f"Month total: {fmt_cost(combined_cost_month)} | {FONT_LABEL} color={COLOR_TOTAL}")
    else:
        print(f"No usage data this month | {FONT_SMALL} color={COLOR_DIM}")

    # ── DAILY BREAKDOWN (last 7 days) ────────────────────────────────────
    print(f"---")
    print(f"📊  LAST 7 DAYS | {FONT_LABEL} color={COLOR_HEADER}")

    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        d_short = (datetime.now() - timedelta(days=i)).strftime("%a %m/%d")
        ct = extract_totals(claude_records, date_filter=d)
        cx = extract_totals(codex_records, date_filter=d)
        day_cost = ct["cost"] + cx["cost"]

        if day_cost > 0:
            # Mini bar proportional to cost split
            total_c = ct["cost"] + cx["cost"]
            c_pct = ct["cost"] / total_c if total_c else 0
            c_bar = "🟠" * max(1, round(c_pct * 8)) if ct["cost"] > 0 else ""
            x_bar = "🟢" * max(1, round((1 - c_pct) * 8)) if cx["cost"] > 0 else ""
            print(f"--{d_short}  {fmt_cost(day_cost):>7s}  {c_bar}{x_bar} | {FONT_SMALL}")
        else:
            print(f"--{d_short}  {'—':>7s} | {FONT_SMALL} color={COLOR_DIM}")

    # ── ACTIONS ───────────────────────────────────────────────────────────
    print(f"---")
    npx = find_npx()
    print(f"Open Claude Code report… | shell={npx} param1=ccusage@latest terminal=true")
    print(f"Open Codex report… | shell={npx} param1=@ccusage/codex@latest terminal=true")
    print(f"---")
    print(f"Refresh | refresh=true")


if __name__ == "__main__":
    try:
        render()
    except Exception as e:
        # Graceful fallback if anything fails
        print(f"⚡ err | color=red {FONT_MONO}")
        print("---")
        print(f"Error: {e} | color=red {FONT_SMALL}")
        print(f"---")
        print(f"Refresh | refresh=true")