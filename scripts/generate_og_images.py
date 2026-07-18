#!/usr/bin/env python3
"""Generate typographic Open Graph card PNGs (1200x630) for every route.

No photography, no build step: each card is a self-hosted-font HTML page
rendered once per route and rasterised with headless Chrome. Re-run this
script whenever a route's title, quick facts or field-checked status
changes; it regenerates every card from data/routes.json.

Usage: python3 scripts/generate_og_images.py
"""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "routes.json"
OG_DIR = ROOT / "assets" / "og"
RENDER_FILE = OG_DIR / "_render.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

WALKING_LABELS = {
    "very-low": "Very low walk",
    "gentle": "Gentle walk",
    "medium": "Medium walk",
    "urban-hike": "Urban hike",
}

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  @font-face {{
    font-family: 'Fraunces';
    font-style: normal;
    font-weight: 400 900;
    src: url('../fonts/fraunces-variable-latin.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Work Sans';
    font-style: normal;
    font-weight: 400 600;
    src: url('../fonts/work-sans-variable-latin.woff2') format('woff2');
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    width: 1200px;
    height: 630px;
    background: #151513;
    font-family: 'Work Sans', sans-serif;
    overflow: hidden;
    position: relative;
  }}
  .wrap {{
    position: absolute;
    inset: 0;
    padding: 64px 72px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .top-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .brand {{
    text-transform: uppercase;
    letter-spacing: .14em;
    color: #d4537e;
    font-weight: 600;
    font-size: 21px;
  }}
  .badge-prototype {{
    color: #8a877e;
    font-weight: 600;
    font-size: 19px;
    letter-spacing: .02em;
  }}
  .badge-walked {{
    background: #d78a9b;
    color: #2a0d15;
    font-weight: 700;
    font-size: 18px;
    letter-spacing: .01em;
    padding: 9px 20px;
    border-radius: 999px;
  }}
  .title-box {{
    flex: 1;
    display: flex;
    align-items: center;
    min-height: 0;
  }}
  .title {{
    font-family: 'Fraunces';
    font-weight: 900;
    color: #f2efe6;
    line-height: 1.08;
    letter-spacing: -.01em;
    max-width: 1040px;
    margin: 0;
  }}
  .chip-row {{
    display: flex;
    gap: 16px;
  }}
  .chip {{
    border: 1.5px solid #3a3934;
    color: #c9c6bd;
    padding: 11px 22px;
    border-radius: 999px;
    font-size: 20px;
    font-weight: 500;
    white-space: nowrap;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="top-row">
      <span class="brand">London, Slightly Elsewhere</span>
      {badge_html}
    </div>
    <div class="title-box">
      <h1 class="title" id="title">{title}</h1>
    </div>
    <div class="chip-row">
      <span class="chip">{walk_chip}</span>
      <span class="chip">{time_chip}</span>
      <span class="chip">{budget_chip}</span>
    </div>
  </div>
  <script>
    document.fonts.ready.then(function () {{
      var el = document.getElementById('title');
      var box = el.parentElement;
      var size = 70;
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


def walking_label(value):
    return WALKING_LABELS.get(value, (value or "").replace("-", " ").capitalize() + " walk")


def sentence_case(value):
    value = value or ""
    return value[:1].upper() + value[1:] if value else value


def badge_html(route):
    if route.get("status") == "prototype":
        return '<span class="badge-prototype">Prototype</span>'
    return '<span class="badge-walked">Walked \u00b7 pilot</span>'


def render_route(route):
    qf = route.get("quickFacts", {})
    html = TEMPLATE.format(
        badge_html=badge_html(route),
        title=route["title"],
        walk_chip=walking_label(qf.get("walkingLevel")),
        time_chip=sentence_case(qf.get("duration")),
        budget_chip=sentence_case(qf.get("budget")),
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
    print(f"  {route['slug']}.png")


def main():
    OG_DIR.mkdir(parents=True, exist_ok=True)
    routes = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Generating {len(routes)} OG cards \u2192 {OG_DIR.relative_to(ROOT)}/")
    for route in routes:
        render_route(route)
    RENDER_FILE.unlink(missing_ok=True)
    print("Done.")


if __name__ == "__main__":
    main()
