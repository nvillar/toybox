# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
"""Tile images into a labelled contact sheet for quick review by a human or an agent.

Usage:
  uv run scripts/gen/contact_sheet.py out/concept/example/*.png --out out/concept/example/_sheet.jpg \
      [--cols 4] [--thumb 480] [--title "Concepts v1"]

Labels are file stems. Output is a JPEG (small enough to view inline).
Tested 2026-09-23 with uv + Pillow on macOS.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (24, 24, 24)
FG = (230, 230, 230)


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("/System/Library/Fonts/Helvetica.ttc", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--thumb", type=int, default=480, help="thumbnail width in px")
    p.add_argument("--title")
    a = p.parse_args()

    paths = sorted(x for x in a.images if x.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and x.resolve() != a.out.resolve())
    if not paths:
        raise SystemExit("no images")
    thumbs = []
    for path in paths:
        im = Image.open(path).convert("RGB")
        im.thumbnail((a.thumb, a.thumb * 4))
        thumbs.append((path.stem, im))

    cols = min(a.cols, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    cell_h = max(im.height for _, im in thumbs)
    label_h, pad = 26, 8
    title_h = 44 if a.title else 0
    sheet = Image.new("RGB", (cols * (a.thumb + pad) + pad, title_h + rows * (cell_h + label_h + pad) + pad), BG)
    draw = ImageDraw.Draw(sheet)
    if a.title:
        draw.text((pad, 10), a.title, fill=FG, font=load_font(26))
    font = load_font(16)
    for i, (label, im) in enumerate(thumbs):
        x = pad + (i % cols) * (a.thumb + pad)
        y = title_h + pad + (i // cols) * (cell_h + label_h + pad)
        sheet.paste(im, (x, y))
        draw.text((x + 2, y + im.height + 4), label, fill=FG, font=font)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out, quality=88)
    print(f"wrote {a.out} ({len(thumbs)} images, {sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
