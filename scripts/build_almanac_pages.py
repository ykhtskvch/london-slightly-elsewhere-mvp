#!/usr/bin/env python3
"""Build the pages that have moved to the field-guide design.

The previous generator (build_route_pages.py) writes a thin shell that
route-page.js fills in from data/routes.json once it loads. The redesign
requires every page to be readable with JavaScript disabled, so the pages
listed in ALMANAC_ROUTES are written out in full here instead, and they load
neither app.js nor route-page.js.

Both generators read the same data/routes.json. A route is built by exactly
one of them: ALMANAC_ROUTES decides which. Pages still on the previous design
keep assets/css/styles.css; the redesigned pages load almanac-tokens.css and
almanac.css and never both stylesheets at once.

build_route_pages.py imports ALMANAC_ROUTES from here and skips those routes,
so the two can be run in either order.
"""

import html
import json
import pathlib
import re
from urllib.parse import quote, urlencode

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_NAME = "London, Slightly Elsewhere"
# The <title> suffix. og:site_name carries the same name for social cards,
# so an og:title never repeats it.
TITLE_SUFFIX = f" | {SITE_NAME}"

# Where the site is deployed. data/site.json is the only place this is
# written down; moving to a custom domain is an edit to that file and a
# rebuild. Nothing else in the build may hardcode the host or the prefix.
_SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
ORIGIN = _SITE["origin"].rstrip("/")
BASE_PATH = _SITE["basePath"]
assert BASE_PATH.startswith("/") and BASE_PATH.endswith("/"), \
    'site.json: basePath needs a leading and a trailing slash, e.g. "/" or "/repo-name/"'
# Absolute URL of the site root, with a trailing slash.
SITE_URL = f"{ORIGIN}{BASE_PATH}"

# GoatCounter, or nothing. It sets no cookies, and assets/js/analytics.js
# replaces its filter with one that reads no storage either, so a visit
# stores nothing and reads nothing. no_onload holds the count back until that
# filter is in place; both scripts are deferred, which runs them in document
# order, so count.js is always ready by the time ours runs.
GOATCOUNTER = (_SITE.get("analytics") or {}).get("goatcounter")


def analytics_tags(base):
    if not GOATCOUNTER:
        return ""
    return (
        f'\n    <script data-goatcounter="{GOATCOUNTER}"'
        " data-goatcounter-settings='{\"no_onload\":true}'"
        ' defer src="https://gc.zgo.at/count.js"></script>'
        f'\n    <script defer src="{base}assets/js/analytics.js"></script>'
    )

# Routes whose detail page is built to the new design. Every route is now on
# it; the tuple stays so build_route_pages.py can still tell the two apart if
# a page is ever moved back.
ALMANAC_ROUTES = None  # None means every route in the data.

FACT_ORDER = ("station", "time", "effort", "cost", "toilets")

# Kept in step with FLOW_LABELS in build_route_pages.py: the same stop types
# must read the same way on a redesigned page and on one that has not moved
# yet.
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

# The status sentence, in the author's words rather than as a badge. Wording
# is carried over verbatim from route-page.js so nothing new is claimed.
STATUS_LINE = {
    "published": "Self-guided route.",
    "field-checked": "Personally field-checked route – live details can still change.",
    "prototype": "Prototype route – not yet field-checked.",
}
PILOT_LINE = "Pilot route – walked once; verify live details before going."


HUB_NAMES = {
    "kings-cross-st-pancras": "King’s Cross St Pancras",
    "liverpool-street": "Liverpool Street",
    "london-bridge": "London Bridge",
    "metropolitan-line": "Metropolitan line",
    "other": "Another London departure point",
}


def e(value):
    return html.escape(str(value or ""), quote=True)


def format_hub(hub):
    return HUB_NAMES.get(hub) or hub.replace("-", " ").title()


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


# --- components ---------------------------------------------------------


def external(href, text, quiet=True, event=None):
    """An outward link. The old markup signalled 'new tab' with a ↗ glyph;
    the design allows no icons, so the signal is given to assistive
    technology in words instead.

    `event` names the link for GoatCounter. It is only worth setting on a
    link whose click cannot be seen any other way – an outward one. The
    attribute is inert unless analytics is switched on."""
    cls = ' class="quiet"' if quiet else ""
    tag = f' data-goatcounter-click="{e(event)}"' if event and GOATCOUNTER else ""
    return (
        f'<a{cls}{tag} href="{e(href)}" rel="noopener" target="_blank">{e(text)}'
        '<span class="visually-hidden"> (opens in a new tab)</span></a>'
    )


def fact_line_parts(route):
    """The FactLine sentence and its values. Authored per route where an
    almanac block exists; otherwise assembled from the fields the data has,
    in the same fixed order. Toilets are simply absent for the routes that
    carry no toilet information – a fact is left out rather than invented."""
    almanac = route.get("almanac")
    if almanac:
        return almanac["factLine"]["sentence"], almanac["factLine"]
    quick = route["quickFacts"]
    is_walk = route["routeType"] == "day-walk"
    values = {
        "station": route["travel"]["arrivalStation"] if is_walk else quick["startStation"],
        "time": quick["duration"],
        "effort": effort_word(route),
        "cost": quick["budget"],
    }
    toilets = (route.get("hike") or {}).get("conditions", {}).get("toilets")
    sentence = "Start at {station}, allow {time}, it is {effort}, reckon on {cost}."
    if toilets:
        # Written as a sentence in the data, so it follows the FactLine
        # rather than sitting inside it as a short phrase.
        sentence += f" {toilets}"
    return sentence, values


def fact_line(route, base, major, with_link):
    """FactLine – the facts as one sentence, always in the order station,
    time, effort, cost, toilets, with the values in ink at 500. Prose, and it
    stays prose."""
    sentence, facts = fact_line_parts(route)
    text = ""
    for chunk in re.split(r"(\{[a-z]+\})", sentence):
        key = chunk[1:-1] if chunk.startswith("{") else None
        text += f"<b>{e(facts[key])}</b>" if key else e(chunk)
    if with_link:
        link_name = (route.get("almanac") or {}).get("linkName") or "What I think it is"
        link = f'<a href="{base}routes/{e(route["slug"])}/">{e(link_name)}</a>'
        text += f" {link}."
    classes = "factline factline--major" if major else "factline"
    return f'<p class="{classes}">{text}</p>'


def plate(route, base, lazy=True):
    """Photograph at 2:1 (3:2 below 768px), first-person caption naming the
    time of day and the month. Walked routes only."""
    art = route["almanac"]["plate"]
    if art.get("image"):
        # The caption says when the photograph was taken; the alt says what is
        # in it, for somebody who cannot see it. They are not the same
        # sentence, so a photograph without its own alt stops the build.
        assert art.get("alt"), f'{route["slug"]}: almanac.plate needs an alt beside the image'
        local = not art["image"].startswith(("http", "/"))
        src = f'{base}{art["image"]}' if local else art["image"]
        # The first photograph on a page is inside the opening screen, so it
        # is fetched straight away; the rest wait until they are scrolled to.
        loading = ' loading="lazy"' if lazy else ""
        img = (
            f'<img src="{e(src)}" alt="{e(art["alt"])}"'
            f' width="1200" height="800"{loading} decoding="async">'
        )
        # The WebP twin is offered only when it is actually on disk, so the
        # markup can never point at a file nobody made. The JPEG stays: it is
        # the fallback, and it is what the OG cards use, because some social
        # previewers still handle WebP badly. scripts/convert_photos.py makes
        # the twins; the build says at the end if one is missing.
        twin = pathlib.Path(art["image"]).with_suffix(".webp") if local else None
        if twin and (ROOT / twin).exists():
            img = (
                f'<picture><source srcset="{e(base + twin.as_posix())}"'
                f' type="image/webp">{img}</picture>'
            )
        frame = f'<div class="plate__frame">{img}</div>'
    else:
        frame = (
            '<div class="plate__frame plate__frame--empty">'
            f'<span class="plate__placeholder">[ {e(art["placeholder"])} ]</span></div>'
        )
    return f'<figure class="plate">{frame}<figcaption>{e(art["caption"])}</figcaption></figure>'


def entry(route, base, lazy=True):
    """RouteEntry.walked – roughly three times the length of an unwalked
    entry. The inequality is the content."""
    a = route["almanac"]
    body = "".join(f'<p class="entry__body">{e(p)}</p>' for p in a.get("body", []))
    return (
        '<article class="entry">'
        f'<h2 class="entry__title">{e(route["title"])}</h2>'
        f'<p class="entry__lead">{e(route["subtitle"])}</p>'
        f"{plate(route, base, lazy)}"
        f"{body}"
        f"{fact_line(route, base, major=True, with_link=True)}"
        "</article>"
    )


def entry_quiet(route, base):
    """RouteEntry.unwalked – an AbsenceMark where the photograph would be,
    carrying a sentence written for this route."""
    a = route["almanac"]
    return (
        '<article class="entry entry--quiet">'
        f'<h3 class="entry__title">{e(route["title"])}</h3>'
        f'<p class="entry__lead">{e(route["subtitle"])}</p>'
        f'<p class="absence">{e(a["absence"])}</p>'
        f'<p class="entry__caveat">{e(a["caveat"])}</p>'
        f"{fact_line(route, base, major=False, with_link=True)}"
        "</article>"
    )


def corrections(almanac, base, head=None, lead=True, body=None):
    """CorrectionsBand – prose and an address, never a form."""
    terms = f'<a href="{base}terms-used-here/">{e(almanac["corrections"]["termsLinkName"])}</a>'
    scale = e(almanac["corrections"]["scale"]).replace("{termsLink}", terms)
    parts = [f'<h2 class="section-head">{e(head)}</h2>'] if head else []
    if lead:
        parts.append(f'<p class="corrections__lead">{e(almanac["corrections"]["lead"])}</p>')
    for line in body or [almanac["corrections"]["body"]]:
        parts.append(line if line.startswith("<") else f'<p class="corrections__body">{e(line)}</p>')
    parts.append(f'<p class="corrections__scale">{scale}</p>')
    return f'<section class="corrections">{"".join(parts)}</section>'


def running_head(almanac, base):
    """A running head, in the sense a book means it: the publication on the
    left, where you are in it on the right, small and quiet above a rule.

    Route pages only. Rule 06 of the handoff forbids anything above the
    editor's note, and the editor's note exists only on the homepage; a route
    page has none. It is set in the same mono as the apparatus at the foot of
    the page, so the two read as the same piece of furniture, and it does not
    stick to the viewport — rule 05 rules out panels that follow the reader.
    """
    links = "".join(
        f'<a class="quiet" href="{base}{e(item["href"])}">{e(item["name"])}</a>'
        for item in almanac["runningHead"]
    )
    return f'<nav class="running-head" aria-label="Primary">{links}</nav>'


def route_return(almanac, base):
    """The way out, at the end of the reading rather than the end of the
    document. The apparatus is the only other navigation on the site, and on
    a full day out it sits ten screens down; somebody who has just finished a
    route should not have to go looking for the next one.

    A sentence, like every other link between pages here."""
    spec = almanac["routeReturn"]
    link = f'<a href="{base}{e(spec["href"])}">{e(spec["linkName"])}</a>'
    return f'<p class="route-return">{e(spec["sentence"]).replace("{link}", link)}</p>'


def apparatus(almanac, base, current=None):
    """Apparatus – one serif line and the service links in mono."""
    line = almanac["apparatus"]["line"]
    sentence = (
        f'{e(line["before"])}<a href="{base}{e(line["href"])}">{e(line["linkName"])}</a>'
        f'{e(line["after"])}'
    )
    here = ' aria-current="page"'
    links = "".join(
        f'<a{here if item["href"] == current else ""}'
        f' href="{base}{e(item["href"])}">{e(item["name"])}</a>'
        for item in almanac["apparatus"]["links"]
    )
    return (
        '<footer class="apparatus">'
        f'<span class="apparatus__line">{sentence}</span>'
        f'<nav class="apparatus__links" aria-label="Footer">{links}</nav>'
        "</footer>"
    )


def definition(term, body, meta=None, glossary=False):
    """A ruled row: the list idiom of the design system, and what every card,
    panel and chip row on the route page becomes.

    On the glossary the rows are a real description list, which is what they
    are and which keeps the page from running h1 straight into h3."""
    tail = f'<p class="meta">{e(meta)}</p>' if meta else ""
    if glossary:
        return (
            '<div class="definition">'
            f'<dt class="definition__term">{e(term)}</dt>'
            f'<dd class="definition__body">{e(body)}</dd>'
            f"{tail}</div>"
        )
    return (
        '<div class="definition">'
        f'<h3 class="definition__term">{e(term)}</h3>'
        f'<p class="definition__body">{e(body)}</p>'
        f"{tail}</div>"
    )


def ruled_list(values):
    items = "".join(f"<li>{e(value)}</li>" for value in values)
    return f'<ul class="ruled-list">{items}</ul>'


def section(head, *blocks, ruled=False):
    cls = "section-head section-head--ruled" if ruled else "section-head"
    inner = "".join(block for block in blocks if block)
    return f'<section class="route-section"><h2 class="{cls}">{e(head)}</h2>{inner}</section>'


def paragraph(text, quiet=False):
    if not text:
        return ""
    cls = ' class="quiet-line"' if quiet else ""
    return f"<p{cls}>{e(text)}</p>"


# --- maps ---------------------------------------------------------------


def maps_search(query):
    return "https://www.google.com/maps/search/?" + urlencode({"api": "1", "query": query})


def maps_directions(origin, destination, travelmode="walking"):
    params = {"api": "1", "destination": destination, "travelmode": travelmode}
    if origin:
        params["origin"] = origin
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def maps_route(stops):
    params = {
        "api": "1",
        "origin": stops[0]["mapQuery"],
        "destination": stops[-1]["mapQuery"],
        "travelmode": "walking",
    }
    waypoints = [stop["mapQuery"] for stop in stops[1:-1]][:9]
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    return "https://www.google.com/maps/dir/?" + urlencode(params)


# --- pages --------------------------------------------------------------


def social_tags(title, description, path, image="site.png", og_type="website"):
    """The og: and twitter: block for a page that is not a route.

    These pages had none at all, so a link to the site root — the first link
    anybody shares — expanded to nothing in a messenger. Each page brings its
    own title and description; the picture is shared between them, because a
    picture's job here is to say which publication this is, and a privacy
    notice has no facts of its own to put on a card.

    The image is named only when the file is on disk, the rule the route
    pages already follow, so a card that was never drawn is never promised.
    """
    lines = [
        f'    <meta property="og:type" content="{og_type}">',
        f'    <meta property="og:title" content="{e(title)}">',
        f'    <meta property="og:description" content="{e(description)}">',
        f'    <meta property="og:url" content="{SITE_URL}{path}">',
        f'    <meta property="og:site_name" content="{e(SITE_NAME)}">',
        '    <meta property="og:locale" content="en_GB">',
    ]
    if (ROOT / "assets" / "og" / image).exists():
        lines += [
            f'    <meta property="og:image" content="{SITE_URL}assets/og/{image}">',
            '    <meta property="og:image:width" content="1200">',
            '    <meta property="og:image:height" content="630">',
            '    <meta name="twitter:card" content="summary_large_image">',
        ]
    else:
        lines.append('    <meta name="twitter:card" content="summary">')
    return lines


def shell(head, body, base, narrow=False, path=None):
    """`path` is where this page sits under the site root, with a trailing
    slash and no leading one: "" for the homepage, "routes/putney/" for a
    route. It becomes the canonical URL. The 404 passes None: it stands for
    every address that does not exist, so it canonicalises to nothing."""
    page_class = "page page--narrow" if narrow else "page"
    canonical = (
        f'\n    <link rel="canonical" href="{SITE_URL}{path}">' if path is not None else ""
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
{head}{canonical}
    <link rel="icon" href="{base}favicon.ico" sizes="32x32">
    <link rel="icon" href="{base}assets/icon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="{base}assets/icon-180.png">
    <link rel="stylesheet" href="{base}assets/css/almanac-tokens.css">
    <link rel="stylesheet" href="{base}assets/css/almanac.css">{analytics_tags(base)}
  </head>
  <body data-base-path="{base}">
    <a class="skip-link" href="#main">Skip to content</a>
    <div class="{page_class}">
{body}
    </div>
  </body>
</html>
"""


def home(routes, almanac):
    base = "./"
    by_slug = {route["slug"]: route for route in routes}
    featured = [by_slug[slug] for slug in almanac["home"]["featured"]]
    walked = [route for route in featured if route["almanac"]["walked"]]
    unwalked = [route for route in featured if not route["almanac"]["walked"]]

    description = (
        "Independent routes for neighbourhood days, green escapes and full "
        "days out by public transport – by mood, not by algorithm."
    )
    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'    <meta name="description" content="{description}">',
        *social_tags("London, Slightly Elsewhere", description, ""),
        "    <title>London, Slightly Elsewhere</title>",
        "    <script type=\"application/ld+json\">"
        + json.dumps({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "London, Slightly Elsewhere",
            "description": "Independent routes for neighbourhood days, green escapes and full days out by public transport.",
            "url": SITE_URL,
            "inLanguage": "en-GB",
            "areaServed": {"@type": "City", "name": "London"},
        }, ensure_ascii=False, separators=(",", ":"))
        + "</script>",
    ])

    # The h1 is hidden rather than absent: the design puts the editor's note
    # first and allows nothing above it, but the page still needs a level-one
    # heading for assistive technology and for search.
    parts = [
        '<h1 class="visually-hidden">London, Slightly Elsewhere</h1>',
        '<section class="editor-note">'
        f'<p class="editor-note__body">{e(almanac["home"]["editorNote"])}</p>'
        f'<p class="editor-note__colophon">{e(almanac["home"]["colophon"])}</p>'
        "</section>",
    ]
    # The first photograph is inside the opening screen, so it is not lazy.
    parts += [entry(route, base, lazy=i > 0) for i, route in enumerate(walked)]
    if unwalked:
        quiet = "".join(entry_quiet(route, base) for route in unwalked)
        parts.append(
            '<section class="entry-group">'
            f'<h2 class="section-head section-head--ruled">{e(almanac["home"]["unwalkedHead"])}</h2>'
            f"{quiet}</section>"
        )

    parts.append(route_return(almanac, base))
    parts.append(corrections(almanac, base))
    body = (
        f'      <main id="main">{"".join(parts)}</main>\n'
        f"      {apparatus(almanac, base)}"
    )
    return shell(head, body, base, path="")


# --- derived index values ------------------------------------------------
#
# The index lists every route, but only the routes with an `almanac` block
# carry authored copy. Everything below is derived from fields the data
# already has, so no claim is made that the data does not support. Where a
# fact is missing it is left out rather than guessed at – see
# DESIGN-CONFLICTS.md.

# One effort scale of three words, mapped from the three scales the data
# still uses. Every full day out is a proper walk: they run 15–22 km.
EFFORT_FROM_LEVEL = {
    "very-low": "flat",
    "gentle": "gentle",
    "medium": "a proper walk",
    "urban-hike": "a proper walk",
}


def effort_word(route):
    almanac = route.get("almanac")
    if almanac:
        return almanac["effort"]
    if route["routeType"] == "day-walk":
        return "a proper walk"
    return EFFORT_FROM_LEVEL.get(route["quickFacts"].get("walkingLevel"), "a proper walk")


def condition_tags(route):
    """The words this route can be filtered by. A route is tagged only where
    the data answers the question; an untagged route does not match, rather
    than being assumed to."""
    tags = [effort_word(route)]

    if route["routeType"] == "day-walk":
        tags.append("most of a day")
    else:
        duration = set(route["filters"].get("duration") or [])
        if duration & {"1-2h", "3-4h"}:
            tags.append("an afternoon")
        if duration & {"half-day", "4h-plus"}:
            tags.append("most of a day")

    # No cost band for the full days out: their budgets are written as "train
    # fare + pub lunch" and the travel is the part that moves.
    budget = route["filters"].get("budget")
    if budget == "free-ish":
        tags.append("next to nothing")
    elif budget == "under-30":
        tags.append("under £30")

    weather = set(route["quickFacts"].get("weather") or [])
    if "rainy" in weather:
        tags.append("after rain")
    if "cold" in weather:
        tags.append("in the cold")
    return tags


def index_facts(route):
    """The five facts in the fixed order station, time, effort, cost,
    toilets. Toilets exist as a short phrase only on the routes with an
    almanac block, so the other rows carry four."""
    almanac = route.get("almanac")
    if almanac:
        facts = almanac["factLine"]
        return [facts[key] for key in FACT_ORDER[:4]] + [f"toilets at {facts['toilets']}"]
    quick = route["quickFacts"]
    start = route["travel"]["arrivalStation"] if route["routeType"] == "day-walk" else quick["startStation"]
    return [start, quick["duration"], effort_word(route), quick["budget"]]


def index_row(route, number, base):
    almanac = route.get("almanac") or {}
    walked = bool(almanac.get("walked"))
    link_name = almanac.get("linkName") or "What I think it is"
    link = f'<a href="{base}routes/{e(route["slug"])}/">{e(link_name)}</a>'
    confidence = f'{e(almanac["indexNote"])} {link}.' if almanac.get("indexNote") else f"{link}."
    facts = '<span class="separator"> · </span>'.join(e(fact) for fact in index_facts(route))
    return (
        f'<div class="index-row{" index-row--walked" if walked else ""}" data-row'
        f' data-walked="{"true" if walked else "false"}"'
        f' data-tags="{e("|".join(condition_tags(route)))}">'
        f'<span class="index-row__number" aria-hidden="true">{number:02d}</span>'
        '<div class="index-row__body">'
        f'<h3 class="index-row__title">{e(route["title"])}</h3>'
        f'<p class="index-row__summary">{e(route["subtitle"])}</p>'
        f'<p class="meta">{facts}</p>'
        f'<p class="index-row__confidence">{confidence}</p>'
        "</div></div>"
    )


def condition_filter(almanac):
    spec = almanac["index"]["filter"]
    parts = [e(spec["lead"])]
    for group in spec["groups"]:
        words = []
        for word in group["words"]:
            words.append(
                f'<button class="filter__word" type="button" aria-pressed="false"'
                f' data-word="{e(word)}" data-axis="{e(group["axis"])}">{e(word)}</button>'
            )
        parts.append('<span class="filter__sep"> / </span>'.join(words))
        parts.append(e(group["after"]))
    return (
        '<section class="filter" data-condition-filter hidden aria-label="Filter the index">'
        f'<p class="filter__sentence">{"".join(parts)}</p>'
        '<div class="filter__result">'
        '<p class="filter__count" data-result role="status"></p>'
        f'<button class="filter__clear" type="button" data-clear hidden>{e(spec["clear"])}</button>'
        "</div></section>"
    )


def index_page(routes, almanac):
    base = "../"
    spec = almanac["index"]
    walked = [route for route in routes if (route.get("almanac") or {}).get("walked")]
    unwalked = [route for route in routes if not (route.get("almanac") or {}).get("walked")]

    number = 0
    groups = []
    for head, note, members in (
        (spec["walkedHead"], None, walked),
        (spec["unwalkedHead"], spec["unwalkedNote"], unwalked),
    ):
        if not members:
            continue
        rows = []
        for route in members:
            number += 1
            rows.append(index_row(route, number, base))
        note_html = f'<p class="section-note">{e(note)}</p>' if note else ""
        groups.append(
            '<section class="index-group" data-group>'
            f'<h2 class="section-head">{e(head)}</h2>{note_html}{"".join(rows)}'
            "</section>"
        )

    terms = f'<a href="{base}terms-used-here/">{e(almanac["corrections"]["termsLinkName"])}</a>'
    scale = e(spec["scale"]).replace("{termsLink}", terms)

    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        '    <meta name="description" content="Browse independent London days and full days out by public transport.">',
        *social_tags(
            spec["title"],
            "Browse independent London days and full days out by public transport.",
            "routes/",
        ),
        "    <title>Browse routes | London, Slightly Elsewhere</title>",
    ])

    body = (
        '      <main id="main">'
        '<header class="index-head">'
        f'<p class="eyebrow">{e(spec["eyebrow"])}</p>'
        f'<h1 class="index-head__title">{e(spec["title"])}</h1>'
        f'<p class="index-head__intro">{e(spec["intro"])}</p>'
        "</header>"
        f'{condition_filter(almanac)}'
        f'<div data-index>{"".join(groups)}</div>'
        f'<p class="index-scale">{scale}</p>'
        "</main>\n"
        f"      {apparatus(almanac, base, current='routes/')}\n"
        f'      <script src="{base}assets/js/condition-filter.js"></script>'
    )
    return shell(head, body, base, path="routes/")


def terms_page(almanac):
    base = "../"
    spec = almanac["terms"]
    rows = "".join(definition(item["term"], item["body"], glossary=True) for item in spec["definitions"])
    legacy = "".join(definition(item["term"], item["body"], glossary=True) for item in spec["legacy"])

    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        '    <meta name="description" content="Definitions for the words this site uses on purpose, and what each one is trying to protect you from.">',
        *social_tags(
            spec["title"],
            "Definitions for the words this site uses on purpose, and what "
            "each one is trying to protect you from.",
            "terms-used-here/",
        ),
        "    <title>Terms used here | London, Slightly Elsewhere</title>",
    ])

    body = (
        '      <main id="main">'
        '<header class="terms-head">'
        f'<h1 class="terms-head__title">{e(spec["title"])}</h1>'
        f'<p class="terms-head__intro">{e(spec["intro"])}</p>'
        "</header>"
        f'<section class="terms-group"><dl>{rows}</dl></section>'
        '<section class="terms-group">'
        f'<h2 class="terms-group__head">{e(spec["legacyHead"])}</h2>'
        f'<p class="terms-group__note">{e(spec["legacyNote"])}</p>'
        f"<dl>{legacy}</dl></section>"
        f'<p class="terms-close">{e(spec["closing"])}</p>'
        "</main>\n"
        f"      {apparatus(almanac, base, current='terms-used-here/')}"
    )
    return shell(head, body, base, narrow=True, path="terms-used-here/")


# --- the pages the handoff never designed -------------------------------
#
# About, Feedback, Privacy, Accessibility, the finder, the 404 and the
# future-guides page have content but no design. Rather than rewrite their
# markup – which would mean re-typing two long forms and the six-filter
# finder, and risking the JavaScript that drives them – the converter lifts
# each page's <main> unchanged and drops it into the new shell. The old class
# names those pages and assets/js/finder.js and forms.js use are restyled in
# almanac.css instead. Running it twice is safe: it re-reads the same <main>.

LEGACY_PAGES = {
    "about/index.html": ("../", "about/"),
    "accessibility/index.html": ("../", "accessibility/"),
    "feedback/index.html": ("../", "feedback/"),
    "contact/index.html": ("../", None),
    "future-guides/index.html": ("../", "future-guides/"),
    "find-your-route/index.html": ("../", "find-your-route/"),
}


def legacy_page(path, base, current, almanac, site_path):
    source = path.read_text(encoding="utf-8")

    head_lines = ['    <meta charset="utf-8">',
                  '    <meta name="viewport" content="width=device-width, initial-scale=1">']
    description = re.search(r'<meta name="description"[^>]*>', source)
    if description:
        head_lines.append(f"    {description.group(0)}")
    title = re.search(r"<title>(.*?)</title>", source, re.S)
    # Generated every time rather than lifted from the source, even though
    # these pages keep their own <main>. This file is its own input: any og:
    # tag found here was written by the previous run, so lifting one would
    # freeze whatever the build first happened to emit and quietly ignore
    # every later change. None of the six sources ever carried any.
    summary = re.search(r'<meta name="description" content="([^"]*)"', source)
    head_lines += social_tags(
        html.unescape(title.group(1)).replace(TITLE_SUFFIX, ""),
        html.unescape(summary.group(1)) if summary else "",
        site_path or "",
    )
    head_lines.append(f"    <title>{title.group(1)}</title>")
    for ld in re.findall(r'<script type="application/ld\+json">.*?</script>', source, re.S):
        head_lines.append(f"    {ld}")

    main = re.search(r"<main\b[^>]*>(.*?)</main>", source, re.S)
    assert main, f"{path}: no <main> to convert"
    inner = main.group(1)
    # A lifted <main> is build output as well as source, so an absolute
    # in-site link inside one would survive a change of deploy path. None of
    # these pages has one – the 404, which needs absolute links, is generated
    # instead – and this keeps it that way.
    assert 'href="/' not in inner, (
        f"{path}: absolute in-site link in a page whose markup is preserved. "
        "Make it relative, or generate the page so it can use BASE_PATH."
    )

    body_scripts = source.split("</main>", 1)[1]
    scripts = [
        f'      <script src="{src}"></script>'
        for src in re.findall(r'<script src="([^"]+)"></script>', body_scripts)
        # The theme toggle is gone: the design has one palette.
        if "theme.js" not in src
    ]

    body = (
        f'      <main id="main">{inner.rstrip()}\n      </main>\n'
        f"      {apparatus(almanac, base, current=current)}"
    )
    if scripts:
        body += "\n" + "\n".join(scripts)
    return shell("\n".join(head_lines), body, base, path=site_path)


def sitemap(routes):
    """Every page worth finding, in reading order.

    /routes/seventeen/ is left out. It is linked from the apparatus on every
    page, so a crawler reaches it anyway; listing it in a machine-readable
    index of the whole site is the one place the joke would not survive.
    The 404 is left out because it is not a page."""
    paths = [""]
    paths += [f'routes/{route["slug"]}/' for route in routes]
    paths += ["routes/", "terms-used-here/", "find-your-route/", "about/",
              "feedback/", "contact/", "future-guides/", "privacy/",
              "accessibility/"]
    locs = "\n".join(f"  <url><loc>{SITE_URL}{path}</loc></url>" for path in paths)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{locs}\n</urlset>\n"
    )


def robots():
    """Nothing is disallowed. Naming the unlisted route here would publish it
    more loudly than leaving it alone: robots.txt is the first file a curious
    person opens."""
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n"


# Anything that would put something on the visitor's device, or read it back.
# Matched as a member access, so the words can still appear in a comment.
STORAGE_USE = re.compile(
    r"\b(?:localStorage|sessionStorage)\s*[.\[]"
    r"|\bdocument\s*\.\s*cookie"
    r"|\bindexedDB\s*[.\[]"
)


def report_photographs_without_a_webp(routes):
    """Say which photographs are still served as JPEG alone.

    This prints rather than stops: a missing twin costs weight, not function,
    because the JPEG is the fallback and plate() only offers a WebP that is
    on disk. Stopping the build over it would punish adding a photograph.
    """
    missing = [
        image
        for route in routes
        for image in [route.get("almanac", {}).get("plate", {}).get("image")]
        if image
        and not image.startswith(("http", "/"))
        and not (ROOT / pathlib.Path(image).with_suffix(".webp")).exists()
    ]
    if missing:
        line = (
            "photograph has no WebP beside it" if len(missing) == 1
            else "photographs have no WebP beside them"
        )
        print(f"\n{len(missing)} {line} — run scripts/convert_photos.py:")
        for image in missing:
            print(f"  {image}")


def check_leading_comes_from_tokens():
    """Leading drifted three times because it was written as a number next to
    the rule that needed it, so the same role ended up with two values: the
    plate caption at 1.55 where the spec says 1.6, a subhead at 1.25 beside a
    stop title at 1.2, an index title at 1.1 beside a route title at 1.08.
    Each was invisible on its own page.

    Every line-height in almanac.css now names a token, so two roles can only
    disagree by disagreeing in the token file, where they sit next to each
    other and the difference is legible.
    """
    css = (ROOT / "assets" / "css" / "almanac.css").read_text(encoding="utf-8")
    # Filtered in Python rather than with a lookahead: \s* backtracks, so
    # "(?!var\()" after it happily matches at the space before var(.
    values = [v.strip() for v in re.findall(r"line-height:\s*([^;}]+)", css)]
    literals = [v for v in values if not v.startswith("var(")]
    if literals:
        raise SystemExit(
            "Build stopped. almanac.css sets leading as a number rather than a token:\n  "
            + "\n  ".join(value.strip() for value in literals)
            + "\n\nAdd a --lh-* token in almanac-tokens.css and use it, so the same "
            "role cannot end up with two values."
        )


def check_nothing_is_stored():
    """The privacy notice says nothing is stored on the visitor's device and
    nothing is read from it, on any page. That is a claim about every script
    the site loads, so the build proves it instead of trusting it.

    This is how theme.js went unnoticed: it stored a light/dark choice, and
    the notice said otherwise for as long as one page still loaded it.

    The only script from elsewhere is GoatCounter's count.js, which does read
    localStorage in its own filter. analytics.js replaces that filter and
    no_onload keeps the original from ever running, so the second check below
    makes sure those two are never separated.
    """
    problems = []

    def resolve(page, src):
        if src.startswith(("http://", "https://", "//")):
            return None  # not ours; covered by the count.js check
        if src.startswith(BASE_PATH):
            return ROOT / src[len(BASE_PATH):]
        if src.startswith("/"):
            return ROOT / src.lstrip("/")
        return (page.parent / src).resolve()

    for page in sorted(ROOT.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        where = page.relative_to(ROOT)

        for src in re.findall(r'<script[^>]+src="([^"]+)"', text):
            path = resolve(page, src)
            if path is None:
                continue
            if not path.exists():
                problems.append(f"{where} loads {src}, which is not in the repository")
                continue
            found = STORAGE_USE.findall(path.read_text(encoding="utf-8"))
            if found:
                problems.append(
                    f"{where} loads {src}, which uses {', '.join(sorted(set(found)))} – "
                    "the privacy notice says no page stores or reads anything on the device"
                )

        if "gc.zgo.at/count.js" in text:
            if "no_onload" not in text:
                problems.append(f"{where} loads count.js without no_onload: its own filter would read localStorage")
            if "assets/js/analytics.js" not in text:
                problems.append(f"{where} loads count.js without analytics.js: nothing replaces the filter that reads localStorage")

    if problems:
        raise SystemExit(
            "Build stopped. The site would store or read something on a visitor's device:\n  "
            + "\n  ".join(problems)
            + "\n\nEither undo that, or rewrite data/almanac.json -> privacy first."
        )


def privacy_page(almanac):
    """The privacy notice is generated rather than lifted, because what it
    has to say depends on a build value: whether analytics.goatcounter is
    set. A page describing a state the site is not in is the one kind of
    drift this notice cannot afford, so the build decides, not a human
    remembering to edit two files at once."""
    spec = almanac["privacy"]
    blocks = []
    for section in spec["sections"]:
        if "body" in section:
            paragraphs = section["body"]
        else:
            paragraphs = section["whenAnalyticsOn" if GOATCOUNTER else "whenAnalyticsOff"]
        blocks.append(f'<h2>{e(section["head"])}</h2>')
        blocks += [f"<p>{e(text)}</p>" for text in paragraphs]

    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        '    <meta name="description" content="What London, Slightly Elsewhere stores, counts and links to.">',
        *social_tags(
            spec["title"],
            "What London, Slightly Elsewhere stores, counts and links to.",
            "privacy/",
        ),
        f"    <title>Privacy{TITLE_SUFFIX}</title>",
    ])
    body = (
        '      <main id="main">'
        '<section class="page-intro">'
        f'<p class="eyebrow">{e(spec["updated"])}</p>'
        f'<h1>{e(spec["title"])}</h1>'
        f'<p>{e(spec["intro"])}</p>'
        "</section>"
        f'<article class="section prose">{"".join(blocks)}</article>'
        "</main>\n"
        f"      {apparatus(almanac, '../', current='privacy/')}"
    )
    return shell(head, body, "../", path="privacy/")


def not_found_page(almanac):
    """The 404 is served at whatever depth the missing URL had, so it is the
    one page that cannot use relative paths. That makes it the one page whose
    markup has to be generated rather than lifted: every address on it comes
    from BASE_PATH."""
    spec = almanac["notFound"]
    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'    <meta name="description" content="{e(spec["description"])}">',
        f'    <title>{e(spec["pageTitle"])}{TITLE_SUFFIX}</title>',
    ])
    body = (
        '      <main id="main">'
        '<section class="page-intro">'
        f'<p class="eyebrow">{e(spec["eyebrow"])}</p>'
        f'<h1>{e(spec["title"])}</h1>'
        f'<p>{e(spec["intro"])}</p>'
        f'<p class="links-line"><a href="{BASE_PATH}{e(spec["href"])}">{e(spec["linkName"])}</a></p>'
        "</section></main>\n"
        f"      {apparatus(almanac, BASE_PATH)}"
    )
    return shell(head, body, BASE_PATH)


def route_head_meta(route):
    seo = route["seo"]
    social = seo.get("socialDescription", seo["description"])
    image = ROOT / "assets" / "og" / f"{route['slug']}.png"
    lines = [
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'    <meta name="description" content="{e(seo["description"])}">',
        '    <meta property="og:type" content="article">',
        f'    <meta property="og:title" content="{e(seo["title"])}">',
        f'    <meta property="og:description" content="{e(social)}">',
        f'    <meta property="og:url" content="{SITE_URL}routes/{route["slug"]}/">',
        f'    <meta property="og:site_name" content="{e(SITE_NAME)}">',
        '    <meta property="og:locale" content="en_GB">',
    ]
    if image.exists():
        lines += [
            f'    <meta property="og:image" content="{SITE_URL}assets/og/{route["slug"]}.png">',
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
        "url": f'{SITE_URL}routes/{route["slug"]}/',
        "inLanguage": "en-GB",
    }
    if seo.get("contentLocation"):
        ld["contentLocation"] = {"@type": "Place", "name": seo["contentLocation"]}
    lines += [
        f'    <title>{e(seo["shortTitle"] + TITLE_SUFFIX)}</title>',
        '    <script type="application/ld+json">'
        + json.dumps(ld, ensure_ascii=False, separators=(",", ":"))
        + "</script>",
    ]
    return "\n".join(lines)


def route_page(route, almanac, venue_timing):
    base = "../../"
    a = route.get("almanac") or {}
    is_day_walk = route["routeType"] == "day-walk"
    facts = route["quickFacts"]
    navigation = route.get("navigation")
    editorial = route["editorial"]
    copy = route["copy"]
    feedback = e(f"{base}feedback/?route={quote(route['title'], safe='')}")

    status = STATUS_LINE.get(route["status"], PILOT_LINE)
    last_checked = route["editorialControl"].get("lastChecked") or "Not yet field-checked"
    flow = '<span class="separator"> · </span>'.join(
        e(FLOW_LABELS.get(stop["type"], stop["type"])) for stop in route["stops"]
    )

    head_block = [
        f'<h1 class="route-head__title">{e(route["title"])}</h1>',
        f'<p class="route-head__lead">{e(route["subtitle"])}</p>',
        f'<p class="quiet-line">{e(status)}</p>',
        f'<p class="quiet-line">Last checked: {e(last_checked)}. '
        "Verify opening hours and access before going.</p>",
    ]
    # A photograph only where the route has been walked; the AbsenceMark only
    # where a sentence has been written for this route. A shared template
    # would turn the admission into a widget, so a route without one shows
    # neither – the status line above already says where it stands.
    if a.get("walked"):
        head_block.append(plate(route, base, lazy=False))
    elif a.get("absence"):
        head_block.append(f'<p class="absence">{e(a["absence"])}</p>')
    head_block.append(fact_line(route, base, major=True, with_link=False))
    head_block.append(
        '<p class="meta"><span class="visually-hidden">Route at a glance: </span>'
        f"{flow}</p>"
    )

    sections = []

    note = route.get("fieldNote")
    if note and note.get("text"):
        flag = "" if note.get("verified") else paragraph(
            "unverified – details not yet reconfirmed", quiet=True
        )
        sections.append(section("Last walked.", flag, paragraph(note["text"])))

    community = route.get("community") or {}
    count = int(community.get("reportCount") or 0)
    needs_review = community.get("status") == "needs-review"
    if needs_review:
        community_head = "A walker flagged something worth checking."
        community_body = "Treat route details as provisional until the issue has been reviewed."
    elif count:
        community_head = f"{count} {'walker has' if count == 1 else 'walkers have'} reported this route."
        community_body = (
            f"Most recent report: {community.get('lastReported') or 'date not yet recorded'}. "
            "Community reports are reviewed; they do not change the Field-checked label."
        )
    else:
        community_head = "No community walks reported yet."
        community_body = (
            "Walked it? A concise field note helps keep the route current. Community "
            "reports never change the Field-checked label automatically."
        )
    sections.append(section(
        community_head,
        paragraph(community_body),
        f'<p class="links-line"><a href="{feedback}">Share a field note</a></p>',
    ))

    if is_day_walk:
        travel = route["travel"]
        hike = route["hike"]
        journey = "one change" if travel["journeyComplexity"] == "one-change" else "direct"
        shape = "Station to station" if hike["routeShape"] == "point-to-point" else hike["routeShape"]
        blocks = [
            definition("Leave from", " / ".join(format_hub(hub) for hub in travel["departureHubs"])),
            definition("Typical journey", f'About {travel["typicalMinutes"]} min · {journey}'),
            definition("Arrive at", travel["arrivalStation"]),
            definition("Return from", travel["returnStation"]),
            definition("Mode", travel["transportMode"].replace("-", " and ")),
            paragraph(travel["serviceNote"], quiet=True),
        ]
        if travel.get("officialSourceUrl"):
            blocks.append(
                '<p class="links-line">'
                + external(travel["officialSourceUrl"], "Check operator information")
                + "</p>"
            )
        sections.append(section("Start with the train, not a car.", *blocks))

        walk_rows = [
            definition("Distance", f'{hike["distanceKm"]} km'),
            definition("Walking time", hike.get("walkingTime") or facts["duration"]),
            definition("Difficulty", hike["difficulty"]),
            definition("Route shape", shape),
            definition("Shorter fallback", "Available" if hike["shortenable"] else "Not planned"),
        ]
        if hike.get("elevationGainM") is not None:
            walk_rows.append(definition("Elevation", f'{hike["elevationGainM"]} m gain'))
        sections.append(section("The walk itself.", *walk_rows))

    if navigation:
        arrival = navigation["arrival"]
        mapped = [stop for stop in route["stops"] if stop.get("mapQuery")]
        whole_walk = (
            maps_route(mapped)
            if route["routeType"] != "day-walk" and arrival.get("station") and 0 < len(mapped) <= 10
            else None
        )
        # The one click on the site that no pageview can stand in for:
        # somebody opening navigation for this route is the closest thing to
        # evidence that they went.
        links = [external(
            maps_directions(None, arrival["pinQuery"], "transit"),
            "Start in Google Maps",
            event=f'maps/{route["slug"]}',
        )]
        if whole_walk:
            links.append(external(whole_walk, "Open the whole walk"))
        if navigation.get("externalRouteUrl"):
            links.append(external(navigation["externalRouteUrl"], "Open detailed route"))
        if navigation.get("gpxUrl"):
            links.append(external(navigation["gpxUrl"], "Download GPX"))
        sections.append(section(
            "Start without guessing.",
            definition("Suggested arrival", f'{arrival["station"]} – {arrival["stationExit"]}'),
            definition("Set your first pin", arrival["pinLabel"], meta=arrival["pinQuery"]),
            definition("Once you arrive", arrival["firstMove"]),
            f'<p class="links-line">{"".join(links)}</p>',
            paragraph(navigation["disclaimer"], quiet=True),
            paragraph(
                "We never request your location. Google Maps can use it privately, if you "
                "have already given Maps permission.",
                quiet=True,
            ),
        ))

    sections.append(section(editorial["vibeSummary"], paragraph(route["routeNarrative"])))
    sections.append(section("Best for.", ruled_list(editorial["bestFor"])))
    sections.append(section("Not ideal for.", ruled_list(editorial["notIdealFor"])))

    stops_html = []
    map_start = (navigation or {}).get("arrival", {}).get("mapOriginQuery") or (
        navigation or {}
    ).get("arrival", {}).get("station")
    for index, stop in enumerate(route["stops"]):
        previous = map_start if index == 0 else route["stops"][index - 1].get("mapQuery")
        walking_url = None
        if stop.get("mapQuery") and previous:
            walking_url = maps_directions(previous, stop["mapQuery"])
        elif stop.get("mapQuery"):
            walking_url = maps_search(stop["mapQuery"])
        meta = f'{e(stop["type"])}<span class="separator"> · </span>{e(stop["duration"])}'
        if stop.get("walkingToNext"):
            meta += f'<span class="separator"> · </span>{e(stop["walkingToNext"])} to next'
        links = []
        if walking_url:
            label = "Walk here from the station" if index == 0 else "Walk from the previous stop"
            links.append(external(walking_url, label))
        if stop.get("mapQuery"):
            links.append(external(maps_search(stop["mapQuery"]), "Open this point"))
        if stop.get("officialUrl"):
            links.append(external(stop["officialUrl"], "Official information"))
        stops_html.append(
            "<li><div class=\"stop__body\">"
            f'<h3 class="stop__title">{e(stop["name"])}</h3>'
            f'<p class="meta">{meta}</p>'
            + (paragraph(stop.get("locationNote"), quiet=True) if stop.get("locationNote") else "")
            + (
                paragraph(f'From the previous point: {stop["directionFromPrevious"]}', quiet=True)
                if stop.get("directionFromPrevious")
                else ""
            )
            + paragraph(stop["description"])
            + (f'<p class="links-line">{"".join(links)}</p>' if links else "")
            + "</div></li>"
        )
    sections.append(section("The route.", f'<ol class="stops">{"".join(stops_html)}</ol>'))

    if is_day_walk:
        hike = route["hike"]
        conditions = hike.get("conditions") or {}
        terrain = [("Terrain", hike.get("terrainNotes"))] + [
            ("Mud and drainage", conditions.get("mudOrDrainage")),
            ("Exposed sections", conditions.get("exposedSections")),
            ("Road sections", conditions.get("roadSections")),
            ("Stiles", conditions.get("stiles")),
            ("Food and water", conditions.get("foodWater")),
            ("Toilets", conditions.get("toilets")),
            ("Mobile signal", conditions.get("mobileSignal")),
            ("Pub timing", conditions.get("pubTiming")),
            ("Shortening", hike.get("shorteningNote")),
        ]
        rows = [definition(label, value) for label, value in terrain if value]
        if rows:
            sections.append(section("Read this before the platform.", *rows))

    if navigation:
        finish = navigation["finish"]
        blocks = [
            definition(finish["label"], f'Nearest practical station: {finish["nearestStation"]}'),
            paragraph(finish["exitNote"]),
        ]
        early = (route.get("hike") or {}).get("earlyExit") if is_day_walk else None
        if early:
            note = f' – {early["note"]}' if early.get("note") else ""
            blocks.append(paragraph(f'Earlier exit: {early["label"]}{note}'))
        blocks.append(
            f'<p class="links-line">{external(maps_search(finish["nearestStation"]), "Open exit station")}</p>'
        )
        sections.append(section("Finish and easy exit.", *blocks))

    timing = venue_timing.get(route.get("valueTimingVenueId")) if route.get("valueTimingVenueId") else None
    if timing:
        sections.append(section(
            timing["title"],
            paragraph(timing["detail"]),
            f'<p class="links-line">{external(timing["sourceUrl"], timing["sourceLabel"])}</p>',
            f'<p class="meta">{e(timing["label"])}<span class="separator"> · </span>'
            f'checked {e(timing["checked"])}</p>',
        ))

    sections.append(section(
        "Choose the shape of the day.",
        *[
            definition(
                version["label"],
                version["description"],
                meta=f'{version["duration"]} · {version["budget"]}'
                + (" · ticket check required" if version.get("requiresTicketCheck") else ""),
            )
            for version in route["versions"]
        ],
    ))

    sections.append(section(
        "Notes before you go.",
        definition("Best time", facts["bestTime"]),
        definition("Date notes", copy["dateNotes"]),
        definition("Friends", copy["friendGroupNotes"]),
        definition("Solo", copy["soloNotes"]),
        definition("Food and drink", copy["foodDrinkNotes"]),
    ))

    sections.append(section(
        "When the plan changes.",
        definition("If it rains", copy["rainyDayBackup"]),
        definition("If it goes well", copy["continueIfGoingWell"]),
        definition("If you want to leave early", copy["exitEarly"]),
    ))

    sections.append(section(
        "What not to expect.",
        paragraph(editorial["whatNotToExpect"]),
        '<h3 class="subhead">Practical warnings</h3>',
        ruled_list(editorial["practicalWarnings"]),
    ))

    final = []
    if route.get("soundtrack"):
        final.append(
            f'<p class="quiet-line">This day sounds like: {e(route["soundtrack"]["artist"])} – '
            f'<em>{e(route["soundtrack"]["track"])}</em></p>'
        )
    sections.append(section(copy["finalEditorialNote"], *final))

    closing = corrections(
        almanac,
        base,
        head="Two things help most.",
        lead=False,
        body=[
            '<p class="corrections__body">What was closed, and where you bailed – more useful '
            f'than a compliment. <a href="{feedback}">Give feedback on this route</a>.</p>',
            "Walked by a person. Wrong by the time you read it, in small ways. Tell us which.",
        ],
    )

    body = (
        f'      {running_head(almanac, base)}\n'
        f'      <main id="main">'
        f'<header class="route-head">{"".join(head_block)}</header>'
        f'{"".join(sections)}{route_return(almanac, base)}{closing}</main>\n'
        f"      {apparatus(almanac, base)}"
    )
    return shell(route_head_meta(route), body, base, path=f'routes/{route["slug"]}/')


def main():
    routes = load("routes.json")
    almanac = load("almanac.json")
    venue_timing = load("venue-timing.json")
    by_slug = {route["slug"]: route for route in routes}

    (ROOT / "index.html").write_text(home(routes, almanac), encoding="utf-8")
    print("Wrote index.html.")

    (ROOT / "routes" / "index.html").write_text(index_page(routes, almanac), encoding="utf-8")
    print(f"Wrote routes/index.html with {len(routes)} rows.")

    (ROOT / "terms-used-here" / "index.html").write_text(terms_page(almanac), encoding="utf-8")
    print("Wrote terms-used-here/index.html.")

    for relative, (base, current) in LEGACY_PAGES.items():
        target = ROOT / relative
        site_path = relative[: -len("index.html")]
        target.write_text(
            legacy_page(target, base, current, almanac, site_path), encoding="utf-8"
        )
    print(f"Converted {len(LEGACY_PAGES)} pages that were never designed.")

    (ROOT / "privacy" / "index.html").write_text(privacy_page(almanac), encoding="utf-8")
    print(f"Wrote privacy/index.html (analytics {'described' if GOATCOUNTER else 'absent'})")

    (ROOT / "404.html").write_text(not_found_page(almanac), encoding="utf-8")
    print(f"Wrote 404.html, anchored at {BASE_PATH}")

    (ROOT / "sitemap.xml").write_text(sitemap(routes), encoding="utf-8")
    (ROOT / "robots.txt").write_text(robots(), encoding="utf-8")
    print(f"Wrote sitemap.xml ({len(routes) + 10} urls) and robots.txt for {SITE_URL}")

    slugs = list(by_slug) if ALMANAC_ROUTES is None else list(ALMANAC_ROUTES)
    for slug in slugs:
        route = by_slug[slug]
        target = ROOT / "routes" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(route_page(route, almanac, venue_timing), encoding="utf-8")
    print(f"Wrote {len(slugs)} route pages.")

    # Which routes still need copy written for them, rather than derived.
    needs = [
        (route["slug"], sorted(
            field for field, missing in (
                ("effort", not (route.get("almanac") or {}).get("effort")),
                ("factLine", not (route.get("almanac") or {}).get("factLine")),
                ("absence", not (route.get("almanac") or {}).get("walked")
                 and not (route.get("almanac") or {}).get("absence")),
                ("indexNote", not (route.get("almanac") or {}).get("indexNote")),
            ) if missing
        ))
        for route in routes
    ]
    outstanding = [(slug, fields) for slug, fields in needs if fields]
    if outstanding:
        print(f"\n{len(outstanding)} routes still need copy written by hand:")
        for slug, fields in outstanding:
            print(f"  {slug}: {', '.join(fields)}")

    report_photographs_without_a_webp(routes)
    check_leading_comes_from_tokens()
    check_nothing_is_stored()
    print("Checked: no page stores or reads anything on a visitor's device.")


if __name__ == "__main__":
    main()
