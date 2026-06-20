#!/usr/bin/env python3
"""Extract named XCTAttachment PNGs from an xcresult bundle.

The screenshot tour names attachments ``NN-kebab-case``. xcresulttool may put
that name either in ``suggestedHumanReadableName`` or in an exported filename
with an index/UUID suffix. This script accepts both forms, rejects duplicates,
and downsizes the resulting PNGs with macOS ``sips``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn


ATTACHMENT_NAME = re.compile(r"^(?P<name>\d{2}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)$")
EXPORTED_NAME = re.compile(
    r"^(?P<name>\d{2}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
    r"(?:_\d+_[0-9A-Fa-f-]+)?\.png$"
)


def die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        die(f"required command not found: {command[0]}")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or "unknown failure"
        die(f"{command[0]} failed: {detail}")


def canonical_name(suggested: str, exported: str) -> str | None:
    suggested_stem = Path(suggested).stem
    match = ATTACHMENT_NAME.fullmatch(suggested_stem)
    if match:
        return match.group("name")

    for candidate in (suggested, exported):
        match = EXPORTED_NAME.fullmatch(Path(candidate).name)
        if match:
            return match.group("name")
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract NN-kebab-case screenshot attachments from an xcresult bundle."
    )
    parser.add_argument("xcresult", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument(
        "--max-dim",
        type=int,
        default=1000,
        help="maximum width or height in pixels (default: 1000)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove existing PNGs from out-dir before extraction",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.xcresult.exists():
        die(f"xcresult bundle not found: {args.xcresult}")
    if args.max_dim <= 0:
        die("--max-dim must be greater than zero")

    with tempfile.TemporaryDirectory(prefix="pr-ios-screenshots-") as scratch:
        scratch_path = Path(scratch)
        export_path = scratch_path / "export"
        processed_path = scratch_path / "processed"
        export_path.mkdir()
        processed_path.mkdir()
        run(
            [
                "xcrun",
                "xcresulttool",
                "export",
                "attachments",
                "--path",
                str(args.xcresult),
                "--output-path",
                str(export_path),
            ]
        )

        manifest = export_path / "manifest.json"
        if not manifest.exists():
            die("xcresulttool did not produce manifest.json")

        try:
            data = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError) as error:
            die(f"could not read xcresult attachment manifest: {error}")

        if not isinstance(data, list):
            die("unexpected xcresult attachment manifest shape")

        extracted: dict[str, Path] = {}
        for test in data:
            if not isinstance(test, dict):
                continue
            for attachment in test.get("attachments", []):
                if not isinstance(attachment, dict):
                    continue
                exported = attachment.get("exportedFileName")
                suggested = attachment.get("suggestedHumanReadableName") or ""
                if not isinstance(exported, str):
                    continue
                name = canonical_name(str(suggested), exported)
                if name is None:
                    continue
                if name in extracted:
                    die(f"duplicate screenshot attachment name: {name}")

                source = export_path / exported
                if not source.is_file():
                    die(f"exported attachment is missing: {exported}")
                destination = processed_path / f"{name}.png"
                shutil.copy2(source, destination)
                extracted[name] = destination

        if not extracted:
            die(
                'no NN-kebab-case attachments found; name tour captures like "01-login"'
            )

        for png in extracted.values():
            run(["sips", "-Z", str(args.max_dim), str(png), "--out", str(png)])

        args.out_dir.mkdir(parents=True, exist_ok=True)
        if args.clean:
            for png in args.out_dir.glob("*.png"):
                if png.is_file():
                    png.unlink()
        for png in extracted.values():
            shutil.copy2(png, args.out_dir / png.name)

    print(f"extracted {len(extracted)} screenshot(s) to {args.out_dir}")


if __name__ == "__main__":
    main()
