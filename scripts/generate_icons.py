#!/usr/bin/env python3
"""Draw the site icon at every size a browser asks for.

The mark is the design system reduced to what survives at 16 pixels: paper,
one ink rule, and a single accent mark sitting on it. A route, and one place
on it worth stopping at. No letterform, because a favicon cannot load the
site's typeface; no ornament, because the design does not allow any.

Writes assets/icon.svg (what modern browsers use), assets/icon-180.png (iOS
home screen, which will not take an SVG) and favicon.ico (asked for at the
server root by older browsers, and reachable only once the site has a domain
of its own).

Run after changing the palette; the colours below are the tokens.
"""

import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent

PAPER = "#f1f0ea"
INK = "#1c1c19"
ACCENT = "#1e3d6b"  # the site's one accent, from almanac-tokens.css

# Geometry on a 32-unit grid, so one unit is one pixel at the smallest size
# the icon is used at.
GRID = 32
RULE_Y = 19          # the rule sits below centre, as it does under a heading
RULE_X1, RULE_X2 = 5, 27
RULE_H = 2           # 1px at 16, 2px at 32
DOT_X, DOT_Y = 21, 20
DOT_R = 4


def svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}">
  <rect width="{GRID}" height="{GRID}" fill="{PAPER}"/>
  <rect x="{RULE_X1}" y="{RULE_Y}" width="{RULE_X2 - RULE_X1}" height="{RULE_H}" fill="{INK}"/>
  <circle cx="{DOT_X}" cy="{DOT_Y}" r="{DOT_R}" fill="{ACCENT}"/>
</svg>
"""


def raster(size):
    """Draw at 8x and downsample, so the circle has clean edges at any size."""
    scale = 8
    px = size * scale
    unit = px / GRID
    image = Image.new("RGB", (px, px), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [RULE_X1 * unit, RULE_Y * unit, RULE_X2 * unit, (RULE_Y + RULE_H) * unit],
        fill=INK,
    )
    draw.ellipse(
        [(DOT_X - DOT_R) * unit, (DOT_Y - DOT_R) * unit,
         (DOT_X + DOT_R) * unit, (DOT_Y + DOT_R) * unit],
        fill=ACCENT,
    )
    return image.resize((size, size), Image.LANCZOS)


def main():
    (ROOT / "assets" / "icon.svg").write_text(svg(), encoding="utf-8")
    print("Wrote assets/icon.svg")

    raster(180).save(ROOT / "assets" / "icon-180.png")
    print("Wrote assets/icon-180.png")

    # One file carrying the sizes Windows and older browsers pick between.
    raster(64).save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("Wrote favicon.ico")


if __name__ == "__main__":
    main()
