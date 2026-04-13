"""Xcode MCP Proxy — routes parallel Moat agents to per-worktree builds and simulators."""

import atexit
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("xcode-proxy")

# Branch -> {"udid": str, "device_name": str}
SIMULATORS: dict[str, dict[str, str]] = {}

REPO_ROOT = os.environ.get("XCODE_PROXY_REPO", "")
OUTPUT_LIMIT = 4000
XCODEBUILD_TIMEOUT = 300


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """Keep the last *limit* characters — the tail is where errors appear."""
    if len(text) <= limit:
        return text
    return f"...[truncated {len(text) - limit} characters]...\n" + text[-limit:]


def _sanitize_branch(branch: str) -> str:
    """Turn a branch name into a safe simulator device name component."""
    return re.sub(r"[^A-Za-z0-9_-]", "-", branch)


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    timeout: int = XCODEBUILD_TIMEOUT,
) -> dict:
    """Run a subprocess and return a structured result with truncated output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "output": _truncate(output),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "output": f"Command timed out after {timeout}s: {' '.join(cmd)}",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "exit_code": -1,
            "output": f"Command not found: {cmd[0]}",
        }


def resolve_worktree(branch: str) -> Path:
    """Map a branch name to its worktree path on the host filesystem."""
    if not REPO_ROOT:
        raise ValueError("XCODE_PROXY_REPO is not set — start the proxy with xproxy start")

    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
    except (FileNotFoundError, OSError) as e:
        raise ValueError(f"Cannot access repo at {REPO_ROOT}: {e}") from e
    if result.returncode != 0:
        raise ValueError(f"git worktree list failed: {result.stderr.strip()}")

    for block in result.stdout.strip().split("\n\n"):
        wt_path = None
        wt_branch = None
        for line in block.split("\n"):
            if line.startswith("worktree "):
                wt_path = line[len("worktree "):]
            if line.startswith("branch refs/heads/"):
                wt_branch = line[len("branch refs/heads/"):]
        if wt_branch == branch and wt_path:
            return Path(wt_path)

    raise ValueError(f"No worktree found for branch: {branch}")


def _require_simulator(branch: str) -> dict[str, str]:
    """Return the simulator entry for *branch*, or raise."""
    sim = SIMULATORS.get(branch)
    if not sim:
        raise ValueError(
            f"No simulator for branch '{branch}' — call simulator(branch, 'boot') first"
        )
    return sim


def _detect_runtime_and_device() -> tuple[str, str]:
    """Find the latest iOS simulator runtime and a suitable iPhone device type."""
    rt = subprocess.run(
        ["xcrun", "simctl", "list", "runtimes", "--json"],
        capture_output=True, text=True,
    )
    runtimes = json.loads(rt.stdout).get("runtimes", [])
    ios_runtimes = [
        r for r in runtimes
        if r.get("isAvailable") and r.get("platform") == "iOS"
    ]
    if not ios_runtimes:
        raise ValueError("No available iOS simulator runtimes found")
    runtime_id = ios_runtimes[-1]["identifier"]

    dt = subprocess.run(
        ["xcrun", "simctl", "list", "devicetypes", "--json"],
        capture_output=True, text=True,
    )
    device_types = json.loads(dt.stdout).get("devicetypes", [])
    # Prefer iPhone 16, fall back to latest iPhone
    iphones = [d for d in device_types if "iPhone" in d.get("name", "")]
    chosen = next((d for d in iphones if "iPhone 16" in d["name"]), None)
    if not chosen:
        chosen = iphones[-1] if iphones else None
    if not chosen:
        raise ValueError("No iPhone device types found")

    return runtime_id, chosen["identifier"]


def _find_existing_simulator(device_name: str) -> str | None:
    """Check if a simulator with this name already exists and return its UDID."""
    result = subprocess.run(
        ["xcrun", "simctl", "list", "devices", "--json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    devices = json.loads(result.stdout).get("devices", {})
    for runtime_devices in devices.values():
        for dev in runtime_devices:
            if dev.get("name") == device_name and dev.get("isAvailable"):
                return dev["udid"]
    return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def xcodebuild(
    branch: str,
    action: str,
    scheme: str,
    configuration: str = "Debug",
    extra_args: list[str] | None = None,
) -> str:
    """Run xcodebuild (build/test/clean) in the worktree for the given branch.

    Args:
        branch: Git branch name — used to locate the worktree.
        action: One of "build", "test", or "clean".
        scheme: Xcode scheme to build.
        configuration: Build configuration (default: Debug).
        extra_args: Additional xcodebuild arguments, e.g. ["CODE_SIGNING_ALLOWED=NO"].
    """
    if action not in ("build", "test", "clean"):
        return json.dumps({"success": False, "output": f"Invalid action: {action}"})

    try:
        worktree = resolve_worktree(branch)
    except ValueError as e:
        return json.dumps({"success": False, "output": str(e)})

    derived = worktree / "DerivedData"
    cmd = [
        "xcodebuild", action,
        "-scheme", scheme,
        "-configuration", configuration,
        "-derivedDataPath", str(derived),
    ]

    if action in ("build", "test"):
        sim = SIMULATORS.get(branch)
        if sim:
            cmd += ["-destination", f"platform=iOS Simulator,id={sim['udid']}"]

    if extra_args:
        cmd += extra_args

    result = _run_cmd(cmd, cwd=worktree)
    return json.dumps(result)


@mcp.tool()
def simulator(branch: str, action: str) -> str:
    """Manage a dedicated iOS simulator for the given branch.

    Args:
        branch: Git branch name.
        action: One of "boot", "shutdown", or "status".
    """
    if action == "boot":
        device_name = f"Moat-{_sanitize_branch(branch)}"

        # Reuse existing simulator if present (proxy restart recovery)
        existing_udid = _find_existing_simulator(device_name)
        if existing_udid:
            udid = existing_udid
        else:
            try:
                runtime_id, device_type = _detect_runtime_and_device()
            except ValueError as e:
                return json.dumps({"success": False, "output": str(e)})

            result = subprocess.run(
                ["xcrun", "simctl", "create", device_name, device_type, runtime_id],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                return json.dumps({
                    "success": False,
                    "output": f"Failed to create simulator: {result.stderr.strip()}",
                })
            udid = result.stdout.strip()

        boot = subprocess.run(
            ["xcrun", "simctl", "boot", udid],
            capture_output=True, text=True,
        )
        # "Unable to boot device in current state: Booted" is fine
        if boot.returncode != 0 and "Booted" not in boot.stderr:
            return json.dumps({
                "success": False,
                "output": f"Failed to boot simulator: {boot.stderr.strip()}",
            })

        SIMULATORS[branch] = {"udid": udid, "device_name": device_name}
        return json.dumps({
            "success": True,
            "udid": udid,
            "device_name": device_name,
            "output": f"Simulator {device_name} ({udid}) booted.",
        })

    elif action == "shutdown":
        sim = SIMULATORS.get(branch)
        if not sim:
            return json.dumps({"success": True, "output": "No simulator to shut down."})

        subprocess.run(
            ["xcrun", "simctl", "shutdown", sim["udid"]],
            capture_output=True, text=True,
        )
        subprocess.run(
            ["xcrun", "simctl", "delete", sim["udid"]],
            capture_output=True, text=True,
        )
        del SIMULATORS[branch]
        return json.dumps({
            "success": True,
            "output": f"Simulator {sim['device_name']} shut down and deleted.",
        })

    elif action == "status":
        sim = SIMULATORS.get(branch)
        if not sim:
            return json.dumps({"success": True, "output": "No simulator assigned to this branch."})

        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return json.dumps({"success": False, "output": "Failed to query simulators."})

        devices = json.loads(result.stdout).get("devices", {})
        for runtime_devices in devices.values():
            for dev in runtime_devices:
                if dev.get("udid") == sim["udid"]:
                    return json.dumps({
                        "success": True,
                        "udid": sim["udid"],
                        "device_name": sim["device_name"],
                        "state": dev.get("state", "Unknown"),
                    })
        return json.dumps({"success": False, "output": "Simulator not found in simctl."})

    else:
        return json.dumps({"success": False, "output": f"Invalid action: {action}"})


@mcp.tool()
def install_and_launch(
    branch: str,
    app_path: str,
    bundle_id: str = "",
) -> str:
    """Install and launch an app on the branch's simulator.

    Args:
        branch: Git branch name.
        app_path: Path to .app relative to worktree root (e.g. DerivedData/Build/Products/Debug-iphonesimulator/MyApp.app).
        bundle_id: Optional CFBundleIdentifier. Extracted from Info.plist if omitted.
    """
    try:
        worktree = resolve_worktree(branch)
        sim = _require_simulator(branch)
    except ValueError as e:
        return json.dumps({"success": False, "output": str(e)})

    abs_app = worktree / app_path
    if not abs_app.is_dir():
        return json.dumps({
            "success": False,
            "output": f"App not found: {abs_app}",
        })

    if not bundle_id:
        plist = abs_app / "Info.plist"
        if not plist.exists():
            return json.dumps({
                "success": False,
                "output": f"Info.plist not found at {plist} — provide bundle_id explicitly",
            })
        bid = subprocess.run(
            ["plutil", "-extract", "CFBundleIdentifier", "raw", str(plist)],
            capture_output=True, text=True,
        )
        if bid.returncode != 0:
            return json.dumps({
                "success": False,
                "output": f"Failed to extract bundle ID: {bid.stderr.strip()}",
            })
        bundle_id = bid.stdout.strip()

    install = _run_cmd(
        ["xcrun", "simctl", "install", sim["udid"], str(abs_app)],
        cwd=worktree,
    )
    if not install["success"]:
        return json.dumps(install)

    launch = _run_cmd(
        ["xcrun", "simctl", "launch", sim["udid"], bundle_id],
        cwd=worktree,
    )
    if not launch["success"]:
        return json.dumps(launch)

    return json.dumps({
        "success": True,
        "bundle_id": bundle_id,
        "output": f"Installed and launched {bundle_id} on {sim['device_name']}.",
    })


@mcp.tool()
def screenshot(branch: str, filename: str = "screenshot.png") -> str:
    """Take a screenshot of the branch's simulator and save to the worktree root.

    Args:
        branch: Git branch name.
        filename: Output filename (default: screenshot.png). Saved to worktree root.
    """
    try:
        worktree = resolve_worktree(branch)
        sim = _require_simulator(branch)
    except ValueError as e:
        return json.dumps({"success": False, "output": str(e)})

    out_path = worktree / filename
    result = _run_cmd(
        ["xcrun", "simctl", "io", sim["udid"], "screenshot", str(out_path)],
        cwd=worktree,
    )
    if not result["success"]:
        return json.dumps(result)

    return json.dumps({
        "success": True,
        "path": str(out_path),
        "output": f"Screenshot saved to {out_path}",
    })


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _cleanup_simulators() -> None:
    """Shut down and delete all managed simulators."""
    for branch, sim in list(SIMULATORS.items()):
        subprocess.run(
            ["xcrun", "simctl", "shutdown", sim["udid"]],
            capture_output=True, text=True,
        )
        subprocess.run(
            ["xcrun", "simctl", "delete", sim["udid"]],
            capture_output=True, text=True,
        )
    SIMULATORS.clear()


def _signal_handler(signum, frame):
    _cleanup_simulators()
    sys.exit(0)


atexit.register(_cleanup_simulators)
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9400)
