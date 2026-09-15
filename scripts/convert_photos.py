#!/usr/bin/env python3
"""Give every photograph in assets/photos a WebP twin.

The JPEG stays. It is what browsers that cannot read WebP fall back to, and
it is what the OG cards use — some social previewers still handle WebP badly,
so generate_og_images.py is deliberately left alone.

Run after adding a photograph:

    python3 scripts/convert_photos.py

The Pillow that ships with Anaconda 3.8 is built without WebP. If this stops
with that complaint, run it from an environment that has one:

    python3 -m venv /tmp/webpenv && /tmp/webpenv/bin/pip install pillow
    /tmp/webpenv/bin/python scripts/convert_photos.py
"""

import pathlib
import sys

from PIL import Image, features

ROOT = pathlib.Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "assets" / "photos"

# 82 is the point where the difference stops being visible on these
# photographs at the size the plate shows them, checked against the JPEG at
# full width. method=6 is the slowest and smallest setting; two files a year
# is not a build cost worth optimising.
QUALITY = 82
METHOD = 6


def main():
    if not features.check("webp"):
        raise SystemExit(
            "This Pillow is built without WebP, so nothing can be written.\n"
            "  python3 -m venv /tmp/webpenv && /tmp/webpenv/bin/pip install pillow\n"
            "  /tmp/webpenv/bin/python scripts/convert_photos.py"
        )

    sources = sorted(PHOTOS.glob("*.jpg")) + sorted(PHOTOS.glob("*.jpeg"))
    if not sources:
        raise SystemExit(f"No photographs in {PHOTOS.relative_to(ROOT)}.")

    total_before = total_after = 0
    for source in sources:
        target = source.with_suffix(".webp")
        with Image.open(source) as image:
            # No exif= and no icc_profile= on purpose: the JPEGs were stripped
            # of their GPS before they were committed, and nothing should put
            # metadata back into the copy.
            image.convert("RGB").save(target, "WEBP", quality=QUALITY, method=METHOD)

        before, after = source.stat().st_size, target.stat().st_size
        total_before += before
        total_after += after
        print(
            f"{source.name} {before // 1024} KB "
            f"→ {target.name} {after // 1024} KB "
            f"({100 - after * 100 // before}% smaller)"
        )

    if len(sources) > 1:
        print(
            f"Total {total_before // 1024} KB → {total_after // 1024} KB "
            f"({100 - total_after * 100 // total_before}% smaller)"
        )


if __name__ == "__main__":
    sys.exit(main())
