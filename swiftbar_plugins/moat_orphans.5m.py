#!/usr/bin/env -S PYTHONIOENCODING=UTF-8 PYTHONDONTWRITEBYTECODE=1 python3
# -*- coding: utf-8 -*-

# <xbar.title>Moat Orphan Monitor</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Patrick Spieker</xbar.author>
# <xbar.desc>Detect stale Moat containers that weren't cleaned up</xbar.desc>
# <xbar.dependencies>python,moat</xbar.dependencies>
# <xbar.var>string(VAR_MOAT_PATH="/opt/homebrew/bin/moat"): Path to moat binary</xbar.var>
# <xbar.var>number(VAR_STALE_HOURS=2): Hours before a running container is considered stale</xbar.var>

import json
import os
import subprocess
from datetime import datetime, timezone

# --- Config -------------------------------------------------------------------
MOAT = os.environ.get("VAR_MOAT_PATH", "/opt/homebrew/bin/moat")
MOAT_CANDIDATES = [MOAT, "/opt/homebrew/bin/moat", "/usr/local/bin/moat"]
STALE_HOURS = int(os.environ.get("VAR_STALE_HOURS", "2"))

# Colors (matches ai_token_usage.1m.py palette)
COLOR_WARN = "#FF6B6B"
COLOR_OK = "#666666"
COLOR_HEADER = "#8B8B8B"
COLOR_DIM = "#666666"
COLOR_NAME = "#D97757"
FONT_MONO = "font=MenloBold size=12"
FONT_LABEL = "font=Menlo size=11"
FONT_SMALL = "font=Menlo size=10"


# --- Helpers ------------------------------------------------------------------

def find_moat():
    """Find a working moat binary."""
    for path in MOAT_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return "moat"


def run_moat_list(timeout=10):
    """Run moat list --json and return parsed JSON or None."""
    moat = find_moat()
    try:
        result = subprocess.run(
            [moat, "list", "--json"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def find_orphans(runs, threshold_hours):
    """Return running containers older than threshold_hours."""
    if not runs:
        return []
    now = datetime.now(timezone.utc)
    orphans = []
    for r in runs:
        if r.get("State") != "running":
            continue
        created_str = r.get("CreatedAt", "")
        if not created_str:
            continue
        try:
            created = datetime.fromisoformat(created_str)
            age_seconds = (now - created).total_seconds()
            if age_seconds > threshold_hours * 3600:
                orphans.append({
                    "name": r.get("Name", "unknown"),
                    "age_seconds": age_seconds,
                    "workspace": os.path.basename(r.get("Workspace", "")),
                    "agent": r.get("Agent", ""),
                })
        except (ValueError, TypeError):
            continue
    return orphans


def fmt_age(seconds):
    """Format seconds as human-readable age: '3h 42m'."""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


# --- Render -------------------------------------------------------------------

def render():
    runs = run_moat_list()

    # moat not available or no data — show dimmed status
    if runs is None:
        print(f"moat -- | {FONT_MONO} color={COLOR_DIM}")
        print("---")
        print(f"Could not reach moat | {FONT_SMALL} color={COLOR_DIM}")
        print(f"---")
        print(f"Refresh | refresh=true")
        return

    orphans = find_orphans(runs, STALE_HOURS)

    if not orphans:
        # Clean state — minimal menu bar presence
        print(f"moat ok | {FONT_MONO} color={COLOR_OK}")
        print("---")
        running = [r for r in runs if r.get("State") == "running"]
        if running:
            print(f"{len(running)} active (under {STALE_HOURS}h) | {FONT_SMALL} color={COLOR_DIM}")
        else:
            print(f"No active containers | {FONT_SMALL} color={COLOR_DIM}")
        print(f"---")
        print(f"Refresh | refresh=true")
        return

    # Orphans detected — alert
    moat = find_moat()
    count = len(orphans)
    print(f"! {count} moat | {FONT_MONO} color={COLOR_WARN}")
    print("---")
    print(f"Stale containers (>{STALE_HOURS}h) | {FONT_LABEL} color={COLOR_HEADER}")
    print("---")

    for o in orphans:
        age = fmt_age(o["age_seconds"])
        name = o["name"]
        workspace = o["workspace"]
        agent = o["agent"]
        label = f"{name}  ({age})"
        if workspace:
            label += f"  {workspace}"

        print(f"{label} | {FONT_LABEL} color={COLOR_NAME}")
        if agent:
            print(f"--Agent: {agent} | {FONT_SMALL} color={COLOR_DIM}")
        print(f"--Stop {name} | shell={moat} param1=stop param2={name} terminal=false refresh=true")

    if count > 1:
        print("---")
        # Stop all: chain moat stop commands
        stop_cmd = " && ".join(f"{moat} stop {o['name']}" for o in orphans)
        print(f"Stop all ({count}) | shell=bash param1=-c param2={stop_cmd} terminal=false refresh=true")

    print("---")
    print(f"Clean stopped runs | shell={moat} param1=clean param2=--force terminal=false refresh=true")
    print(f"---")
    print(f"Refresh | refresh=true")


if __name__ == "__main__":
    try:
        render()
    except Exception as e:
        print(f"moat err | color=red {FONT_MONO}")
        print("---")
        print(f"Error: {e} | color=red {FONT_SMALL}")
        print(f"---")
        print(f"Refresh | refresh=true")
