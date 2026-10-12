#!/usr/bin/env python3
"""Resolve the skill symlink, prepare its environment, and invoke the renderer."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).resolve().parents[3]
    arguments = sys.argv[1:]
    custom_python = os.environ.get("CODEX_FLAMECHART_PYTHON")
    environment = Path.home() / ".local/share/codex-flamechart/venv"
    python = (
        Path(custom_python).expanduser()
        if custom_python
        else environment / "bin/python"
    )
    try:
        if not arguments or "--help" in arguments or "-h" in arguments:
            python = Path(sys.executable)
        elif custom_python:
            if not python.is_file():
                raise OSError(f"CODEX_FLAMECHART_PYTHON does not exist: {python}")
        else:
            lock = repo / "scripts/codex_trace/requirements.lock"
            fingerprint = hashlib.sha256(lock.read_bytes()).hexdigest()
            stamp = environment / ".requirements.sha256"
            if not python.is_file():
                subprocess.run(
                    [sys.executable, "-m", "venv", str(environment)], check=True
                )
                stamp.unlink(missing_ok=True)
            if not stamp.is_file() or stamp.read_text() != fingerprint:
                print("Installing Codex flame chart dependencies…", file=sys.stderr)
                subprocess.run(
                    [str(python), "-m", "pip", "install", "-r", str(lock)],
                    check=True,
                    stdout=sys.stderr,
                )
                stamp.write_text(fingerprint)
        os.execv(
            str(python),
            [str(python), str(repo / "scripts/codex_flamechart.py"), *arguments],
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"codex-flamechart: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
