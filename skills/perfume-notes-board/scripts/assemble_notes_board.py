#!/usr/bin/env python3
"""Assemble a white-background perfume notes board from a JSON spec."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


SECTION_NAMES = ["Top Notes", "Middle Notes", "Base Notes"]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    regular = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    bolds = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in (bolds if bold else regular):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if text_width(draw, trial, font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = (0, 0, 0),
    line_gap: int = 5,
) -> int:
    for line in wrap_text(draw, text, font, max_width):
        w = text_width(draw, line, font)
        draw.text((x + (max_width - w) / 2, y), line, font=font, fill=fill)
        y += text_height(draw, line, font) + line_gap
    return y


def cover_crop(img: Image.Image, target_w: int, target_h: int, focal: list[float] | tuple[float, float]) -> Image.Image:
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    fx = max(0.0, min(1.0, float(focal[0])))
    fy = max(0.0, min(1.0, float(focal[1])))

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = int((src_w - new_w) * fx)
        left = max(0, min(src_w - new_w, left))
        box = (left, 0, left + new_w, src_h)
    else:
        new_h = int(src_w / target_ratio)
        top = int((src_h - new_h) * fy)
        top = max(0, min(src_h - new_h, top))
        box = (0, top, src_w, top + new_h)

    return img.crop(box).resize((target_w, target_h), Image.Resampling.LANCZOS)


def validate_spec(spec: dict[str, Any], base_dir: Path) -> None:
    sections = spec.get("sections")
    if not isinstance(sections, list) or len(sections) != 3:
        raise ValueError("spec.sections must contain exactly three sections")

    names = [section.get("name") for section in sections]
    if names != SECTION_NAMES:
        raise ValueError(f"section names must be exactly: {', '.join(SECTION_NAMES)}")

    total = 0
    for section in sections:
        items = section.get("items")
        if not isinstance(items, list) or not 3 <= len(items) <= 4:
            raise ValueError("each section must contain 3 or 4 items")
        total += len(items)
        for item in items:
            for field in ["label", "caption", "image"]:
                if not item.get(field):
                    raise ValueError(f"item missing required field: {field}")
            path = Path(item["image"])
            if not path.is_absolute():
                path = base_dir / path
            if not path.exists():
                raise ValueError(f"image not found: {path}")
            focal = item.get("focal", [0.5, 0.5])
            if not isinstance(focal, list) or len(focal) != 2:
                raise ValueError("item.focal must be a two-number list when provided")

    if total != 12:
        raise ValueError("default board must contain exactly 12 items total")


def render(spec: dict[str, Any], spec_path: Path, output_arg: str | None, width: int) -> Path:
    base_dir = spec_path.parent
    validate_spec(spec, base_dir)

    output = Path(output_arg or spec.get("output") or "perfume-notes-board.png")
    if not output.is_absolute():
        output = base_dir / output

    margin_x = int(width * 0.06)
    col_gap = int(width * 0.025)
    cols = 4
    cell_w = (width - margin_x * 2 - col_gap * (cols - 1)) // cols
    img_w = int(cell_w * 0.92)
    img_h = int(img_w * 0.82)

    title_font = load_font(max(42, int(width * 0.052)), True)
    subtitle_font = load_font(max(22, int(width * 0.021)), False)
    section_font = load_font(max(30, int(width * 0.033)), True)
    label_font = load_font(max(24, int(width * 0.026)), True)
    caption_font = load_font(max(18, int(width * 0.018)), False)

    scratch = Image.new("RGB", (width, 200), "white")
    draw = ImageDraw.Draw(scratch)
    caption_lines = 3
    caption_h = text_height(draw, "Ag", caption_font) * caption_lines + 28
    label_h = text_height(draw, "Ag", label_font) * 2 + 16
    row_header_h = text_height(draw, "Top Notes", section_font) + 24
    row_h = row_header_h + img_h + label_h + caption_h + 28
    header_h = text_height(draw, "Ag", title_font) + text_height(draw, "Ag", subtitle_font) + 70
    row_gap = int(width * 0.05)
    height = header_h + row_h * 3 + row_gap * 2 + 50

    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    title = spec.get("title", "Me if I was a perfume")
    subtitle = spec.get("subtitle", "top notes / middle notes / base notes")
    draw_centered(draw, title, 0, 38, width, title_font)
    draw_centered(draw, subtitle, 0, 38 + text_height(draw, "Ag", title_font) + 8, width, subtitle_font, (40, 40, 40))

    y = header_h
    for section in spec["sections"]:
        draw.text((margin_x, y), section["name"], font=section_font, fill=(0, 0, 0))
        item_y = y + row_header_h
        for idx, item in enumerate(section["items"]):
            cell_x = margin_x + idx * (cell_w + col_gap)
            img_x = cell_x + (cell_w - img_w) // 2
            image_path = Path(item["image"])
            if not image_path.is_absolute():
                image_path = base_dir / image_path
            img = Image.open(image_path).convert("RGB")
            tile = cover_crop(img, img_w, img_h, item.get("focal", [0.5, 0.5]))
            canvas.paste(tile, (img_x, item_y))

            label_y = item_y + img_h + 15
            end_y = draw_centered(draw, item["label"], cell_x, label_y, cell_w, label_font)
            draw_centered(draw, item["caption"], cell_x + 4, end_y + 4, cell_w - 8, caption_font)

        y += row_h + row_gap

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a perfume notes board from JSON.")
    parser.add_argument("spec", help="Path to a JSON board spec")
    parser.add_argument("--output", help="Override output path")
    parser.add_argument("--width", type=int, default=1600, help="Output width in pixels")
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text())
    try:
        output = render(spec, spec_path, args.output, args.width)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
