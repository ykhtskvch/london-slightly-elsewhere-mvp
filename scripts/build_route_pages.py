#!/usr/bin/env python3
"""Regenerate routes/<slug>/index.html from data/routes.json.

Every route page is a shell: the head metadata plus a no-JS fallback that
route-page.js replaces once the data loads. Both used to be hand-written, so
renaming a route in the data left the title, meta description, JSON-LD and
fallback prose behind. This script makes routes.json the only place a route is
described.

The fallback markup below deliberately mirrors renderRoute() in
assets/js/route-page.js — the status labels, quick-fact selection and the
at-a-glance flow labels must stay in step with it, or a visitor without JS sees
different facts from one with.
"""

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_BASE = "https://ykhtskvch.github.io/london-slightly-elsewhere-mvp"
TITLE_SUFFIX = " | London, Slightly Elsewhere"

STATUS = {
    "published": ("Published route", "Self-guided route", "Published route."),
    "field-checked": (
        "Field-checked route",
        "Personally field-checked route · live details can still change",
        "Field-checked route.",
    ),
    "prototype": ("Prototype route", "Prototype route — not yet field-checked", "Prototype."),
}
PILOT = ("Pilot route", "Pilot route — walked once; verify live details before going", "Pilot edition.")

FLOW_LABELS = {
    "start": "start",
    "walk": "walk",
    "pub": "pub",
    "live-music": "optional gig",
    "bookshop": "bookshop",
    "museum": "indoor stop",
    "cafe-or-pub": "warm finish",
    "garden": "free gardens",
    "view": "view",
}


def e(value):
    return html.escape(str(value), quote=True)


def quick_facts(route):
    if route["routeType"] == "day-walk":
        hike, travel = route["hike"], route["travel"]
        shape = hike["routeShape"]
        return [
            ("Start", travel["arrivalStation"]),
            ("Finish", travel["returnStation"]),
            ("Distance", f"{hike['distanceKm']} km"),
            ("Walking time", hike.get("walkingTime") or route["quickFacts"]["duration"]),
            ("Difficulty", hike["difficulty"]),
            ("Route shape", "Station to station" if shape == "point-to-point" else shape),
            ("Travel from London", f"About {travel['typicalMinutes']} min"),
            ("Shorter fallback", "Available" if hike["shortenable"] else "Not planned"),
        ]
    facts = route["quickFacts"]
    rows = [("Start", facts["startStation"]), ("Time", facts["duration"])]
    if facts.get("startBy"):
        rows.append(("Start by", facts["startBy"]))
    rows.append(("Walk", facts["walkingLevel"]))
    rows.append(("Budget", facts["budget"]))
    rows.append(("Easy exit", "Built in" if route["filters"]["easyExit"] == "must-have" else "Possible"))
    return rows


def head(route):
    seo = route["seo"]
    social = seo.get("socialDescription", seo["description"])
    image = ROOT / "assets" / "og" / f"{route['slug']}.png"
    lines = [
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'    <meta name="description" content="{e(seo["description"])}">',
        '    <meta property="og:type" content="article">',
        f'    <meta property="og:title" content="{e(seo["title"] + TITLE_SUFFIX)}">',
        f'    <meta property="og:description" content="{e(social)}">',
    ]
    if image.exists():
        lines += [
            f'    <meta property="og:image" content="{SITE_BASE}/assets/og/{route["slug"]}.png">',
            '    <meta property="og:image:width" content="1200">',
            '    <meta property="og:image:height" content="630">',
            '    <meta name="twitter:card" content="summary_large_image">',
        ]
    else:
        lines.append('    <meta name="twitter:card" content="summary">')

    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": seo["title"],
        "description": seo["description"],
        "inLanguage": "en-GB",
    }
    if seo.get("contentLocation"):
        ld["contentLocation"] = {"@type": "Place", "name": seo["contentLocation"]}

    lines += [
        f'    <title>{e(seo["shortTitle"] + TITLE_SUFFIX)}</title>',
        '    <link rel="stylesheet" href="../../assets/css/styles.css">',
        '    <script src="../../assets/js/theme.js"></script>',
        '    <script type="application/ld+json">'
        + json.dumps(ld, ensure_ascii=False, separators=(",", ":"))
        + "</script>",
    ]
    return "\n".join(lines)


def fallback(route, detail):
    facts = "".join(
        f"<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>" for label, value in quick_facts(route)
    )
    flow = "".join(
        f"<span>{e(FLOW_LABELS.get(stop['type'], stop['type']))}</span>" for stop in route["stops"]
    )
    parts = [
        f'<section class="route-hero"><p class="eyebrow">{e(detail)}</p>'
        f'<h1>{e(route["title"])}</h1>'
        f'<p class="route-subtitle">{e(route["subtitle"])}</p>'
        f'<dl class="quick-facts">{facts}</dl>'
        f'<div class="route-at-glance" aria-label="Route at a glance">{flow}</div></section>'
    ]
    note = route.get("fieldNote")
    if note and note.get("text"):
        flag = "" if note.get("verified") else '<span class="verify-flag">unverified — details not yet reconfirmed</span>'
        parts.append(
            f'<aside class="field-note"><p class="eyebrow">Last walked{flag}</p><p>{e(note["text"])}</p></aside>'
        )
    editorial = route["editorial"]
    summary = [
        '<section class="section prose fallback-summary"><h2>The useful version</h2>',
        f'<p>{e(editorial["vibeSummary"])}</p>',
    ]
    if editorial.get("whatNotToExpect"):
        summary.append(f'<h3>What not to expect</h3><p class="warning">{e(editorial["whatNotToExpect"])}</p>')
    summary.append("</section>")
    parts.append("".join(summary))
    return "\n      ".join(parts)


def page(route):
    label, detail, footer_status = STATUS.get(route["status"], PILOT)
    return f"""<!doctype html>
<html lang="en">
  <head>
{head(route)}
  </head>
  <body data-base-path="../../" data-route-id="{e(route["id"])}">
    <a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header"><div class="site-shell header-row">
      <a class="brand" href="../../">London, Slightly Elsewhere<small>Routes by mood, not algorithm</small></a>
      <div class="header-actions"><nav class="site-nav" aria-label="Primary navigation"><a href="../../find-your-route/">Find a route</a><a aria-current="page" href="../">Browse routes</a></nav><button class="theme-toggle" type="button" data-theme-toggle aria-label="Use dark theme">◐</button></div>
    </div></header>
    <main id="main" class="site-shell" data-route-page>
      {fallback(route, detail)}
    </main>
    <footer class="site-footer"><div class="site-shell footer-row"><span>Independent routes for days in and out of London · {e(footer_status)}</span><span class="footer-note">Walked by a person. Wrong by the time you read it, in small ways. Tell us which.</span><nav class="footer-links" aria-label="Footer"><a href="../../feedback/">Give route feedback</a><a href="../../about/">About</a><a href="../../terms-used-here/">Terms used here</a><a href="../../privacy/">Privacy</a><a href="../../accessibility/">Accessibility</a></nav></div></footer>
    <script src="../../assets/js/app.js"></script>
    <script src="../../assets/js/route-page.js"></script>
  </body>
</html>
"""


def main():
    routes = json.loads((ROOT / "data" / "routes.json").read_text(encoding="utf-8"))
    for route in routes:
        target = ROOT / "routes" / route["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(route), encoding="utf-8")
    print(f"Wrote {len(routes)} route pages.")

    missing = [r["slug"] for r in routes if not r["seo"].get("contentLocation")]
    if missing:
        print("No seo.contentLocation (JSON-LD will omit it): " + ", ".join(missing))


if __name__ == "__main__":
    main()
