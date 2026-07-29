#!/usr/bin/env python3
"""Validate FHIR vendor integration inventory and evidence completeness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_ENVIRONMENTS = {"staging", "production"}
ALLOWED_STATES = {"Works", "Partial", "Blocked", "Error", "Not tested"}
EVIDENCE_KEYS = {
    "picker_screenshot",
    "result_screenshot",
    "api_call",
    "logs",
    "configuration",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level value must be an object")
    return value


def vendor_map(document: dict[str, Any], source: Path) -> dict[str, dict[str, Any]]:
    vendors = document.get("vendors")
    if not isinstance(vendors, list) or not vendors:
        raise ValueError(f"{source}: vendors must be a non-empty array")

    result: dict[str, dict[str, Any]] = {}
    for index, vendor in enumerate(vendors):
        if not isinstance(vendor, dict):
            raise ValueError(f"{source}: vendors[{index}] must be an object")
        vendor_id = vendor.get("id")
        name = vendor.get("name")
        if not isinstance(vendor_id, str) or not vendor_id.strip():
            raise ValueError(f"{source}: vendors[{index}].id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{source}: vendor {vendor_id!r} needs a non-empty name")
        if vendor_id in result:
            raise ValueError(f"{source}: duplicate vendor id {vendor_id!r}")
        result[vendor_id] = vendor
    return result


def resolve_evidence(repo_root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError(f"evidence path must be repository-relative: {relative}")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"evidence path escapes repository: {relative}") from exc
    return resolved


def validate(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    repo_root = args.repo_root.resolve()
    inventory = load_json(args.inventory)
    manifest = load_json(args.manifest)

    inventory_environment = inventory.get("environment")
    manifest_environment = manifest.get("environment")
    if inventory_environment not in ALLOWED_ENVIRONMENTS:
        errors.append(f"inventory environment must be one of {sorted(ALLOWED_ENVIRONMENTS)}")
    if manifest_environment not in ALLOWED_ENVIRONMENTS:
        errors.append(f"manifest environment must be one of {sorted(ALLOWED_ENVIRONMENTS)}")
    if inventory_environment != manifest_environment:
        errors.append(
            f"environment mismatch: inventory={inventory_environment!r}, "
            f"manifest={manifest_environment!r}"
        )

    try:
        inventory_vendors = vendor_map(inventory, args.inventory)
        manifest_vendors = vendor_map(manifest, args.manifest)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    missing = sorted(set(inventory_vendors) - set(manifest_vendors))
    extra = sorted(set(manifest_vendors) - set(inventory_vendors))
    if missing:
        errors.append(f"manifest is missing vendors: {', '.join(missing)}")
    if extra:
        errors.append(f"manifest has undiscovered vendors: {', '.join(extra)}")

    for vendor_id, vendor in manifest_vendors.items():
        state = vendor.get("state")
        if state not in ALLOWED_STATES:
            errors.append(
                f"{vendor_id}: state must be one of {sorted(ALLOWED_STATES)}, got {state!r}"
            )
        description = vendor.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{vendor_id}: description must be a non-empty string")

        evidence = vendor.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{vendor_id}: evidence must be an object")
            continue

        absent = sorted(EVIDENCE_KEYS - set(evidence))
        unknown = sorted(set(evidence) - EVIDENCE_KEYS)
        if absent:
            errors.append(f"{vendor_id}: missing evidence keys: {', '.join(absent)}")
        if unknown:
            errors.append(f"{vendor_id}: unknown evidence keys: {', '.join(unknown)}")

        for key in sorted(EVIDENCE_KEYS & set(evidence)):
            relative = evidence[key]
            if not isinstance(relative, str) or not relative.strip():
                errors.append(f"{vendor_id}: evidence.{key} must be a non-empty path")
                continue
            try:
                path = resolve_evidence(repo_root, relative)
            except ValueError as exc:
                errors.append(f"{vendor_id}: {exc}")
                continue
            if not path.is_file():
                errors.append(f"{vendor_id}: evidence.{key} does not exist: {relative}")
            elif path.stat().st_size == 0:
                errors.append(f"{vendor_id}: evidence.{key} is empty: {relative}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        errors = validate(args)
    except ValueError as exc:
        errors = [str(exc)]

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    manifest = load_json(args.manifest)
    print(
        f"Validated {len(manifest['vendors'])} vendors "
        f"for {manifest['environment']} with complete evidence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
