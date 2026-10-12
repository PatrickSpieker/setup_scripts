#!/usr/bin/env python3
"""Resolve the installed skill symlink and invoke the deterministic renderer."""

import os
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
python = Path(
    os.environ.get(
        "CODEX_FLAMECHART_PYTHON",
        str(Path.home() / ".local/share/codex-flamechart/venv/bin/python"),
    )
)
if not python.is_file():
    print(
        "Install the isolated environment first; see "
        + str(repo / "scripts/codex_trace/README.md"),
        file=sys.stderr,
    )
    sys.exit(1)
os.execv(
    str(python), [str(python), str(repo / "scripts/codex_flamechart.py"), *sys.argv[1:]]
)
