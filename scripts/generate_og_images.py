#!/usr/bin/env python3
"""Generate the Open Graph card for every route (1200 × 630).

The cards use the current warm-canvas / deep-green design system and the same
route facts as the site. They are rendered directly to PNG so the build never
needs to open (or interfere with) a desktop browser.

Requires Pillow: ``python3 -m pip install Pillow``.
Usage: ``python3 scripts/generate_og_images.py``.
"""

import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as error:
    raise SystemExit(
        "Pillow is required to generate OG cards. Install it with "
        "`python3 -m pip install Pillow`."
    ) from error

import build_almanac_pages as builder


ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "routes.json"
OG_DIR = ROOT / "assets" / "og"

WIDTH = 1200
HEIGHT = 630
PADDING = 72

# Keep these in step with assets/css/almanac-tokens.css.
CANVAS = "#f3efe6"
INK = "#17251f"
TEXT = "#263a31"
MUTED = "#5d6c64"
BORDER = "#74847a"
ACCENT = "#176b5b"

# The previous renderer was already macOS-specific (it called Google Chrome
# by its /Applications path). These installed faces give Pillow a dependable
# editorial serif and a quiet UI sans without shipping duplicate font files.
SERIF_CANDIDATES = (
    Path("/System/Library/Fonts/NewYork.ttf"),
    Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
)
SANS_CANDIDATES = (
    Path("/System/Library/Fonts/Avenir Next.ttc"),
    Path("/System/Library/Fonts/HelveticaNeue.ttc"),
)


def installed_font(candidates):
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(f"No suitable local font found: {', '.join(map(str, candidates))}")


SERIF = installed_font(SERIF_CANDIDATES)
SANS = installed_font(SANS_CANDIDATES)


def font(path, size):
    return ImageFont.truetype(str(path), size=size)


def wrap_words(draw, text, selected_font, max_width):
    lines = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=selected_font) > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def title_layout(draw, title):
    """Return a readable title font and lines that fit the central panel."""
    max_width = WIDTH - (PADDING * 2)
    max_height = 300
    for size in range(76, 33, -2):
        selected = font(SERIF, size)
        lines = wrap_words(draw, title, selected, max_width)
        spacing = max(4, round(size * 0.04))
        box = draw.multiline_textbbox(
            (0, 0), "\n".join(lines), font=selected, spacing=spacing
        )
        if len(lines) <= 3 and box[3] - box[1] <= max_height:
            return selected, lines, spacing, box
    selected = font(SERIF, 34)
    lines = wrap_words(draw, title, selected, max_width)
    box = draw.multiline_textbbox((0, 0), "\n".join(lines), font=selected, spacing=4)
    return selected, lines, 4, box


def fact_line(draw, route):
    facts = builder.index_facts(route)[:4]
    text = "  ·  ".join(facts)
    max_width = WIDTH - (PADDING * 2)
    for size in range(25, 15, -1):
        selected = font(SANS, size)
        if draw.textlength(text, font=selected) <= max_width:
            return text, selected
    return text, font(SANS, 16)


def render_route(route):
    image = Image.new("RGB", (WIDTH, HEIGHT), CANVAS)
    draw = ImageDraw.Draw(image)

    label_font = font(SANS, 20)
    brand = "LONDON, SLIGHTLY ELSEWHERE"
    walked = bool((route.get("almanac") or {}).get("walked"))
    status = "WALKED IN PERSON" if walked else "NOT YET FIELD-WALKED"

    draw.text((PADDING, 78), brand, font=label_font, fill=MUTED)
    status_width = draw.textlength(status, font=label_font)
    draw.text((WIDTH - PADDING - status_width, 78), status, font=label_font, fill=ACCENT)
    draw.line((PADDING, 126, WIDTH - PADDING, 126), fill=INK, width=2)

    title_font, lines, spacing, title_box = title_layout(draw, route["title"])
    title_text = "\n".join(lines)
    title_height = title_box[3] - title_box[1]
    title_y = 158 + ((300 - title_height) / 2) - title_box[1]
    draw.multiline_text(
        (PADDING, title_y),
        title_text,
        font=title_font,
        fill=INK,
        spacing=spacing,
    )

    draw.line((PADDING, 500, WIDTH - PADDING, 500), fill=BORDER, width=1)
    facts, facts_font = fact_line(draw, route)
    draw.text((PADDING, 534), facts, font=facts_font, fill=TEXT)

    target = OG_DIR / f"{route['slug']}.png"
    staged = target.with_name(f".{target.stem}-new.png")
    image.save(staged, format="PNG", optimize=True)
    staged.replace(target)
    print(f"  {target.name}{' · walked' if walked else ''}")


def main():
    OG_DIR.mkdir(parents=True, exist_ok=True)
    routes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Generating {len(routes)} route OG cards → {OG_DIR.relative_to(ROOT)}/")
    for route in routes:
        render_route(route)
    print("Done. The shared site-redesign.png cover is maintained separately.")


if __name__ == "__main__":
    main()
