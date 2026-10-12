#!/usr/bin/env python3
"""Create an offline flame chart from a local Codex conversation deep link."""

import argparse
import os
import sys
import tempfile
import webbrowser
from pathlib import Path

from codex_trace.sources import TraceError, snapshot, thread_id


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("thread", help="codex://threads/<UUID>")
    parser.add_argument(
        "--output", type=Path, help="HTML destination (default: <thread-id>.html)"
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser(),
    )
    parser.add_argument(
        "--open", action="store_true", help="Open the completed report in your browser"
    )
    args = parser.parse_args(argv)
    temporary = None
    try:
        tid = thread_id(args.thread)
        report = snapshot(args.codex_home, tid)
        from codex_trace.render import render

        html = render(report)
        output = (args.output or Path(f"{tid}.html")).expanduser().resolve()
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=".codex-flamechart-",
            suffix=".tmp",
            delete=False,
        ) as f:
            temporary = Path(f.name)
            f.write(html)
        os.replace(temporary, output)
        temporary = None
        print(output)
        for diagnostic in report["diagnostics"]:
            print(f"warning: {diagnostic}", file=sys.stderr)
        if args.open:
            webbrowser.open(output.as_uri())
        return 0
    except ImportError as exc:
        print(
            f"Missing rendering dependency: {exc}. Install scripts/codex_trace/requirements.lock in a virtual environment.",
            file=sys.stderr,
        )
        return 1
    except (TraceError, OSError, ValueError) as exc:
        print(f"codex-flamechart: {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
