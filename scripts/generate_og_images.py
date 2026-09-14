#!/usr/bin/env python3
"""Generate the Open Graph card for every route (1200x630).

No photography and no design of its own: the card is the field-guide page
seen from further away. Paper, one ink rule, the route title in Newsreader,
and the same facts in the same order as the index row, set in IBM Plex Mono.
Each card is an HTML page using the site's own self-hosted fonts, rendered
once per route by headless Chrome.

Everything is drawn at twice the site's type scale, because the card is
displayed at roughly half its pixel size in a feed. That includes the rule:
1px on the page is 2px here, so it survives being scaled back down.

The facts and the effort word come from build_almanac_pages, so a card can
never disagree with the index row it previews.

Re-run whenever a route's title, facts or walked status changes.

Usage: python3 scripts/generate_og_images.py
"""
import json
import subprocess
from pathlib import Path

import build_almanac_pages as builder

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "routes.json"
OG_DIR = ROOT / "assets" / "og"
RENDER_FILE = OG_DIR / "_render.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# The palette, from assets/css/almanac-tokens.css. Nothing outside this list.
PAPER = "#f1f0ea"
INK = "#1c1c19"
INK_TERTIARY = "#44433c"
MUTED = "#63625b"
NUMERALS = "#83827b"
RED_LEAD = "#a3341a"

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  @font-face {{
    font-family: 'Newsreader';
    font-style: normal;
    font-weight: 300 500;
    src: url('../fonts/newsreader-variable-latin.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'IBM Plex Mono';
    font-style: normal;
    font-weight: 400;
    src: url('../fonts/ibm-plex-mono-400-latin.woff2') format('woff2');
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    width: 1200px;
    height: 630px;
    background: {paper};
    overflow: hidden;
    font-family: 'Newsreader', Georgia, serif;
    font-synthesis-weight: none;
  }}
  .wrap {{
    height: 100%;
    padding: 72px;
    display: flex;
    flex-direction: column;
  }}
  .imprint {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-bottom: 20px;
    border-bottom: 2px solid {ink};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 20px;
    line-height: 1.7;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: {muted};
  }}
  .walked {{ color: {red_lead}; }}
  .title-box {{
    flex: 1;
    display: flex;
    align-items: center;
    min-height: 0;
  }}
  .title {{
    margin: 0;
    font-weight: 400;
    color: {ink};
    line-height: 1.08;
    letter-spacing: -.008em;
  }}
  .facts {{
    padding-top: 24px;
    border-top: 1px solid {numerals};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 25px;
    line-height: 1.7;
    color: {ink_tertiary};
  }}
  .sep {{ color: {numerals}; }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="imprint">
      <span>London, Slightly Elsewhere</span>
      <span class="{walked_class}">{walked_word}</span>
    </div>
    <div class="title-box"><h1 class="title" id="title">{title}</h1></div>
    <div class="facts">{facts}</div>
  </div>
  <script>
    document.fonts.ready.then(function () {{
      var el = document.getElementById('title');
      var box = el.parentElement;
      var size = 76;
      el.style.fontSize = size + 'px';
      while (el.scrollHeight > box.clientHeight && size > 34) {{
        size -= 2;
        el.style.fontSize = size + 'px';
      }}
      document.documentElement.setAttribute('data-ready', '1');
    }});
  </script>
</body>
</html>
"""


def escape(value):
    return builder.e(value)


def card_facts(route):
    """Station, time, effort, cost – the first four of the five, in the fixed
    order. Toilets are left off: thirteen routes have no toilet information,
    and a card that carries five facts for some routes and four for others
    would be a worse preview than one that always carries four."""
    facts = builder.index_facts(route)[:4]
    sep = f'<span class="sep"> · </span>'
    return sep.join(escape(fact) for fact in facts)


def render_route(route):
    walked = bool((route.get("almanac") or {}).get("walked"))
    html = TEMPLATE.format(
        paper=PAPER, ink=INK, ink_tertiary=INK_TERTIARY, muted=MUTED,
        numerals=NUMERALS, red_lead=RED_LEAD,
        walked_word="Walked" if walked else "Not walked",
        walked_class="walked" if walked else "",
        title=escape(route["title"]),
        facts=card_facts(route),
    )
    RENDER_FILE.write_text(html, encoding="utf-8")

    out_path = OG_DIR / f"{route['slug']}.png"
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--window-size=1200,630",
            "--virtual-time-budget=2000",
            f"--screenshot={out_path}",
            RENDER_FILE.as_uri(),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"  {route['slug']}.png{' · walked' if walked else ''}")


def main():
    OG_DIR.mkdir(parents=True, exist_ok=True)
    routes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Generating {len(routes)} OG cards → {OG_DIR.relative_to(ROOT)}/")
    for route in routes:
        render_route(route)
    RENDER_FILE.unlink(missing_ok=True)
    print("Done. Rebuild the pages so the eight new cards get their og:image.")


if __name__ == "__main__":
    main()
