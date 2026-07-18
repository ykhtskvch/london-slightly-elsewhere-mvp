#!/usr/bin/env python3
"""Insert Open Graph / Twitter Card meta tags into every route page's <head>.

Idempotent: routes that already have an og:type tag are left untouched, so
this can be re-run safely after adding a new route.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "routes.json"
SITE_BASE = "https://ykhtskvch.github.io/london-slightly-elsewhere-mvp"

DESC_RE = re.compile(r'<meta name="description" content="([^"]*)">')


def og_block(route, description):
    title = route["title"]
    slug = route["slug"]
    return (
        '\n    <meta property="og:type" content="article">'
        f'\n    <meta property="og:title" content="{title} | London, Slightly Elsewhere">'
        f'\n    <meta property="og:description" content="{description}">'
        f'\n    <meta property="og:image" content="{SITE_BASE}/assets/og/{slug}.png">'
        '\n    <meta property="og:image:width" content="1200">'
        '\n    <meta property="og:image:height" content="630">'
        '\n    <meta name="twitter:card" content="summary_large_image">'
    )


def main():
    routes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    updated, skipped = [], []

    for route in routes:
        page = ROOT / "routes" / route["slug"] / "index.html"
        html = page.read_text(encoding="utf-8")

        if "og:type" in html:
            skipped.append(route["slug"])
            continue

        match = DESC_RE.search(html)
        description = match.group(1) if match else route.get("seo", {}).get("description", "")

        # Insert right after the description meta tag (before <title>).
        insertion_point = match.end() if match else html.index("<title>")
        html = html[:insertion_point] + og_block(route, description) + html[insertion_point:]
        page.write_text(html, encoding="utf-8")
        updated.append(route["slug"])

    print(f"Updated {len(updated)}: {', '.join(updated)}")
    if skipped:
        print(f"Skipped (already had og tags) {len(skipped)}: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
