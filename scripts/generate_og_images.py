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


def shoot(out_path):
    """Render whatever is in RENDER_FILE to a 1200x630 png."""
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


def site_facts(routes):
    """The tally, spelled out the way the index spells it.

    condition-filter.js writes the same sentence under the filter. The words
    for the numbers are repeated here rather than shared, because the only
    other way to reach them from Python would be to parse the JavaScript.
    Both counts come from routes.json, so the two can disagree about wording
    but never about the facts."""
    words = (
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
        "twenty-one twenty-two twenty-three twenty-four"
    ).split()
    spell = lambda n: words[n] if n < len(words) else str(n)
    walked = sum(1 for route in routes if (route.get("almanac") or {}).get("walked"))
    return (
        f"{spell(len(routes)).capitalize()} routes, "
        f"and {spell(walked)} of them I have walked."
    )


def render_site(routes):
    """One card for everything that is not a route: the homepage, the index,
    the glossary, privacy and the pages the handoff never designed.

    They had no og: tags at all, so a link to the site root — the first link
    anybody shares — expanded to nothing. Each page keeps its own og:title and
    og:description; what they share is the picture, because the picture's job
    is to say which publication this is. A route earns its own card by having
    its own facts; a privacy notice does not.

    The line under the rule is the index's own title, and the tally is the
    sentence the index already carries. Neither is written for the card."""
    almanac = json.loads((ROOT / "data" / "almanac.json").read_text(encoding="utf-8"))
    html = TEMPLATE.format(
        paper=PAPER, ink=INK, ink_tertiary=INK_TERTIARY, muted=MUTED,
        numerals=NUMERALS, red_lead=RED_LEAD,
        # The imprint carries the address, the way a printed one does. It comes
        # from site.json, so moving the site moves the card with it.
        walked_word=escape(builder.ORIGIN.split("//", 1)[-1]),
        walked_class="",
        title=escape(almanac["index"]["title"]),
        facts=escape(site_facts(routes)),
    )
    RENDER_FILE.write_text(html, encoding="utf-8")
    shoot(OG_DIR / "site.png")
    print("  site.png · the homepage, the index, and every page without facts")


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
    shoot(OG_DIR / f"{route['slug']}.png")
    print(f"  {route['slug']}.png{' · walked' if walked else ''}")


def main():
    OG_DIR.mkdir(parents=True, exist_ok=True)
    routes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Generating {len(routes) + 1} OG cards → {OG_DIR.relative_to(ROOT)}/")
    for route in routes:
        render_route(route)
    render_site(routes)
    RENDER_FILE.unlink(missing_ok=True)
    print("Done. Rebuild the pages so the cards reach their og:image tags.")


if __name__ == "__main__":
    main()
