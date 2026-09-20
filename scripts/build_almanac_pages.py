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

# The one address the site gives out. Written in site.json so the privacy
# notice and the contact page cannot drift apart; check_one_contact_address()
# refuses to finish if any page offers a different one.
CONTACT = _SITE.get("contact")

# Form endpoints. A form with none is shut: forms.js disables its fields and
# says so. assets/js/config.js is written from this, so the notice and the
# form can never describe different states — the mistake analytics nearly
# made, where one file said "no analytics" while another switched it on.
FORMS = _SITE.get("forms") or {}
FORMS_OPEN = any(FORMS.values())


def analytics_tags(base):
    if not GOATCOUNTER:
        return ""
    return (
        f'\n    <script data-goatcounter="{GOATCOUNTER}"'
        " data-goatcounter-settings='{\"no_onload\":true}'"
        f' defer src="{base}assets/js/count.js"></script>'
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
    "boat": "boat",
    "exit": "exit",
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


def external(href, text, quiet=True, event=None, context=None):
    """An outward link. The old markup signalled 'new tab' with a ↗ glyph;
    the design allows no icons, so the signal is given to assistive
    technology in words instead.

    `event` names the link for GoatCounter. It is only worth setting on a
    link whose click cannot be seen any other way – an outward one. The
    attribute is inert unless analytics is switched on.

    `context` is read out but not shown — the stop a repeated label belongs
    to, so links with the same words are still telling apart."""
    cls = ' class="quiet"' if quiet else ""
    tag = f' data-goatcounter-click="{e(event)}"' if event and GOATCOUNTER else ""
    hidden = f'<span class="visually-hidden"> {e(context)}</span>' if context else ""
    return (
        f'<a{cls}{tag} href="{e(href)}" rel="noopener" target="_blank">{e(text)}{hidden}'
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
    # The three effort words are explained in the glossary, which the
    # apparatus links to from every page. Repeating the explanation under
    # every route was 23 words shown 24 times and read once.
    if lead:
        parts.append(f'<p class="corrections__scale">{scale}</p>')
    return f'<section class="corrections">{"".join(parts)}</section>'


_SITE_HEAD = None
_DISCOVERY = None


MOOD_LABELS = {
    "green": "Green & quiet",
    "riverside-canal": "Riverside / canal",
    "urban": "Urban",
    "architecture": "Architecture",
    "pub": "Pub at the end",
    "quiet": "Quiet",
}


def discovery_for(route):
    """Controlled browse/finder language, kept separate from route prose."""
    global _DISCOVERY
    if _DISCOVERY is None:
        _DISCOVERY = {item["slug"]: item for item in load("discovery.json")}
    return _DISCOVERY[route["slug"]]


def route_distance(route):
    if route["routeType"] == "day-walk":
        value = route["hike"]["distanceKm"]
        return f"{value:g} km" if isinstance(value, float) else f"{value} km"
    return re.sub(r"^Approx\.?\s*", "", route["quickFacts"]["walkingDistance"], flags=re.I)


def route_start(route):
    return route["travel"]["arrivalStation"] if route["routeType"] == "day-walk" else route["quickFacts"]["startStation"]


def route_finish(route):
    if route["routeType"] == "day-walk":
        return route["travel"]["returnStation"]
    return route["quickFacts"]["endStation"]


def route_difficulty(route):
    if route["routeType"] == "day-walk":
        return route["hike"]["difficulty"].replace("-", " ").title()
    return effort_word(route).replace("a proper walk", "Proper walk").capitalize()


def route_walked(route):
    return route["status"] in {"field-checked", "published"}


def route_status_label(route):
    return "Walked in person" if route_walked(route) else "Not yet field-walked"


def walked_first(routes):
    """Walked routes ahead of drafts, each group in data order."""
    return sorted(routes, key=lambda route: not route_walked(route))


def route_media(route, base, card=True):
    """A real route photograph where one exists, and nothing where none
    does: a card shows no media block, a route hero runs in one column.
    The drafts hold their place with words, not a hatch."""
    art = (route.get("almanac") or {}).get("plate") or {}
    short = discovery_for(route)["cardTitle"]
    classes = "route-card__media" if card else "route-head__visual"
    if not art.get("image"):
        return ""
    source = pathlib.Path(art["image"])
    src = f"{base}{source.as_posix()}"
    priority = ' loading="lazy"' if card else ' fetchpriority="high"'
    img = (
        f'<img src="{e(src)}" alt="{e(art.get("alt") or short)}" '
        f'width="1200" height="800"{priority} decoding="async">'
    )
    twin = source.with_suffix(".webp")
    if (ROOT / twin).exists():
        img = (
            f'<picture><source srcset="{e(base + twin.as_posix())}" type="image/webp">'
            f"{img}</picture>"
        )
    caption = ""
    if not card and art.get("caption"):
        caption = f'<figcaption>{e(art["caption"])}</figcaption>'
    return f'<figure class="{classes}">{img}{caption}</figure>'


def route_map(route, base, extension=False):
    """The sketch map render_maps.py drew, when it has: numbered pins in
    walking order on OpenStreetMap tiles, joined by a dashed line that is
    not the walked path. Nothing is shown for a route without one. An
    extension has its own map, from the pin where the core walk ended."""
    name = f"{route['slug']}-extension" if extension else route["slug"]
    jpg = ROOT / "assets" / "maps" / f"{name}.jpg"
    if not jpg.exists():
        return ""
    stops = route["extension"]["stops"] if extension else route["stops"]
    count = len(stops)
    alt = (
        f"Sketch map of the {'extension' if extension else 'walk'}: {count} numbered stops in order, "
        f"from {stops[0]['name']} to {stops[-1]['name']}, on an OpenStreetMap background."
    )
    src = f"{base}assets/maps/{name}"
    webp = ""
    if jpg.with_suffix(".webp").exists():
        webp = f'<source srcset="{e(src)}.webp" type="image/webp">'
    return (
        '<figure class="route-map">'
        f'<picture>{webp}<img src="{e(src)}.jpg" alt="{e(alt)}" width="1200" height="800" '
        'loading="lazy" decoding="async"></picture>'
        '<figcaption>Stops in walking order. The dashed line joins them and is not the walked '
        'path; use the live route for that. Map © OpenStreetMap contributors.</figcaption>'
        '</figure>'
    )


def route_card(route, base, heading_level=3, finder=False, hidden=False):
    """The single card used by Home, Walks, Find a walk and related walks."""
    discovery = discovery_for(route)
    title_tag = f"h{heading_level}"
    location = discovery["location"]
    location_label = "London" if location == "london" else "Outside London"
    tags = "".join(
        f'<span class="route-card__tag">{e(MOOD_LABELS[mood])}</span>'
        for mood in discovery["moods"][:3]
    )
    attrs = [
        'data-route-card',
        f'data-location="{e(location)}"',
    ]
    if finder:
        attrs += [
            'data-finder-card',
            f'data-time="{e(discovery["timeBand"])}"',
            f'data-moods="{e("|".join(discovery["moods"]))}"',
            f'data-route-slug="{e(route["slug"])}"',
        ]
    if hidden:
        attrs.append("hidden")
    return (
        f'<article class="route-card" {" ".join(attrs)}>'
        f'<a class="route-card__link" href="{base}routes/{e(route["slug"])}/" '
        f'aria-label="View walk: {e(discovery["cardTitle"])}">'
        '<div class="route-card__content">'
        f'<p class="route-card__eyebrow">{e(location_label)} <span aria-hidden="true">·</span> '
        f'<span class="route-card__status{" route-card__status--walked" if route_walked(route) else ""}">'
        f'{e(route_status_label(route))}</span></p>'
        f'<{title_tag} class="route-card__title">{e(discovery["cardTitle"])}</{title_tag}>'
        f'<p class="route-card__summary">{e(route["subtitle"])}</p>'
        f'<p class="route-card__meta">{e(route_distance(route))} <span aria-hidden="true">·</span> '
        f'{e(route["quickFacts"]["duration"])}</p>'
        f'<p class="route-card__journey"><span class="route-card__journey-label">Start</span> '
        f'{e(route_start(route))}</p>'
        f'<div class="route-card__tags">{tags}</div>'
        '</div>'
        f'{route_media(route, base, card=True)}'
        '</a></article>'
    )


def site_head(base, path):
    """Consistent, product-led navigation with a no-JavaScript mobile menu."""
    walks_current = path == "routes/" or bool(path and path.startswith("routes/"))
    find_current = path == "find-your-route/"
    about_current = path == "about/"

    def current(active):
        return ' aria-current="page"' if active else ""

    desktop = (
        f'<a{current(walks_current)} href="{base}routes/">Walks</a>'
        f'<a{current(about_current)} href="{base}about/">About</a>'
        f'<a class="site-head__cta"{current(find_current)} href="{base}find-your-route/">Find a walk</a>'
    )
    feedback_current = path == "feedback/"
    mobile = (
        f'<a{current(walks_current)} href="{base}routes/">Walks</a>'
        f'<a{current(about_current)} href="{base}about/">About</a>'
        f'<a{current(feedback_current)} href="{base}feedback/">Feedback</a>'
    )
    return (
        '<header class="site-head">'
        f'<a class="site-head__name" href="{base}">London, Slightly Elsewhere'
        '<span class="site-head__tagline">Walks with good stops</span></a>'
        f'<nav class="site-head__desktop site-head__links" aria-label="Primary">{desktop}</nav>'
        f'<a class="site-head__mobile-cta"{current(find_current)} '
        f'href="{base}find-your-route/">Find a walk</a>'
        '<details class="mobile-nav"><summary><span class="visually-hidden">Menu</span></summary>'
        f'<nav class="mobile-nav__panel" aria-label="Mobile primary">{mobile}</nav>'
        '</details></header>'
    )


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
    """Secondary navigation and a compact independent-project note."""
    groups = [
        ("The walks", [
            ("Walks", "routes/"),
            ("Find a walk", "find-your-route/"),
            ("About", "about/"),
            ("Feedback", "feedback/"),
        ]),
        ("The site", [
            ("Terms used here", "terms-used-here/"),
            ("Privacy", "privacy/"),
            ("Accessibility", "accessibility/"),
        ]),
    ]
    links = ""
    for heading, items in groups:
        group = ""
        for name, href in items:
            active = ' aria-current="page"' if href == current else ""
            group += f'<a{active} href="{base}{href}">{e(name)}</a>'
        links += f'<div class="apparatus__group"><p class="eyebrow">{e(heading)}</p>{group}</div>'
    return (
        '<footer class="apparatus">'
        '<div class="apparatus__brand"><strong>London, Slightly Elsewhere</strong>'
        '<span>Independent walks, checked at the speed of weekends.</span></div>'
        f'<nav class="apparatus__links" aria-label="Footer">{links}</nav>'
        '<p class="apparatus__note">Independent project · London · 2026</p>'
        '</footer>'
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


def section(head, *blocks, ruled=False, folded=False):
    """`folded` closes the section behind a <details>.

    A route page runs to about 1,400 words, and a third of that is the walk
    itself; the rest answers questions a reader has only sometimes — what if
    it rains, what if I want to leave, when is the best time to go. Folding
    those puts them one click away instead of eight screens down, and deletes
    nothing: <details> is in the markup, findable by the browser's own search
    and by a screen reader, and it works with no JavaScript at all.

    The heading keeps its level and its words, so the outline a screen reader
    announces is the same open or closed."""
    cls = "section-head section-head--ruled" if ruled else "section-head"
    inner = "".join(block for block in blocks if block)
    if folded:
        return (
            '<section class="route-section route-section--folded">'
            f'<details><summary><h2 class="{cls}">{e(head)}</h2></summary>'
            f'<div class="route-section__folded-body">{inner}</div></details></section>'
        )
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


def maps_route_from(origin, stops):
    """A separate route whose first numbered stop is not its origin.

    Optional extensions begin where the core walk ends. Keeping the origin
    outside the numbered list lets the extension remain visibly optional
    without dropping the walk from the finish to its first waypoint.
    """
    params = {
        "api": "1",
        "origin": origin,
        "destination": stops[-1]["mapQuery"],
        "travelmode": "walking",
    }
    waypoints = [stop["mapQuery"] for stop in stops[:-1]][:9]
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def render_stop_choices(choices):
    """Render mutually exclusive options inside one numbered route stop.

    One link per option. The stop's own directions link already leads to
    this corner; what an option needs is the venue's own page, or failing
    that a pin, not a second set of directions to the same place."""
    if not choices:
        return ""
    items = []
    for choice in choices:
        links = []
        if choice.get("officialUrl"):
            links.append(external(choice["officialUrl"], "Official information"))
        elif choice.get("mapQuery"):
            links.append(external(maps_search(choice["mapQuery"]), "Open this point"))
        items.append(
            '<li class="stop-option">'
            f'<h4 class="stop-option__title">{e(choice["name"])}</h4>'
            + (f'<p class="meta">{e(choice["meta"])}</p>' if choice.get("meta") else "")
            + paragraph(choice["description"])
            + (f'<p class="links-line">{"".join(links)}</p>' if links else "")
            + "</li>"
        )
    return f'<ul class="stop-options">{"".join(items)}</ul>'


def render_stops(stops, map_start=None, first_walking_label="Walk here from the start"):
    """One accessible stop list, reused by the core walk and extensions."""
    rendered = []
    previous_query = map_start
    has_mapped_stop = False
    for stop in stops:
        walking_url = None
        if stop.get("mapQuery") and previous_query:
            walking_url = maps_directions(previous_query, stop["mapQuery"])
        elif stop.get("mapQuery"):
            walking_url = maps_search(stop["mapQuery"])

        meta = f'{e(stop["type"])}<span class="separator"> · </span>{e(stop["duration"])}'
        if stop.get("walkingToNext"):
            meta += f'<span class="separator"> · </span>{e(stop["walkingToNext"])} to next'

        # One Google link per stop — the walking directions. The place itself
        # is named and addressed in the text, and the sketch map above shows
        # where it sits; a second link to search for it added a choice and
        # nothing else.
        # The visible label stays short; the stop's name rides along hidden,
        # so a list of links reads "…to The Duke's Head", not eight of the
        # same line.
        links = []
        if walking_url:
            label = first_walking_label if not has_mapped_stop else "Walk from the previous stop"
            links.append(external(walking_url, label, context=f"to {stop['name']}"))
        if stop.get("officialUrl"):
            links.append(external(stop["officialUrl"], "Official information", context=f"for {stop['name']}"))
        approach = ""
        if stop.get("directionFromPrevious"):
            approach_label = "From the previous stop" if has_mapped_stop else "From the start"
            approach = (
                f'<p class="stop__approach"><strong>{approach_label}</strong> '
                f'{e(stop["directionFromPrevious"])}</p>'
            )

        rendered.append(
            '<li><div class="stop__body">'
            f'<h3 class="stop__title">{e(stop["name"])}</h3>'
            f'<p class="meta">{meta}</p>'
            + (paragraph(stop.get("locationNote"), quiet=True) if stop.get("locationNote") else "")
            + approach
            + paragraph(stop["description"])
            + render_stop_choices(stop.get("choices"))
            + (f'<p class="links-line">{"".join(links)}</p>' if links else "")
            + "</div></li>"
        )
        if stop.get("mapQuery"):
            previous_query = stop["mapQuery"]
            has_mapped_stop = True
    return f'<ol class="stops">{"".join(rendered)}</ol>'


def optional_detours_section(detours):
    if not detours:
        return ""
    rows = []
    for detour in detours:
        links = []
        if detour.get("mapQuery"):
            links.append(external(maps_search(detour["mapQuery"]), "Open this point"))
        if detour.get("officialUrl"):
            links.append(external(detour["officialUrl"], "Check the current programme"))
        rows.append(
            '<div class="definition optional-detour">'
            f'<p class="eyebrow">{e(detour["eyebrow"])}</p>'
            f'<h3 class="definition__term">{e(detour["name"])}</h3>'
            f'<p class="definition__body">{e(detour["description"])}</p>'
            + (f'<p class="links-line">{"".join(links)}</p>' if links else "")
            + "</div>"
        )
    return section("Optional before you commit.", *rows)


def extension_section(route, base):
    """A second, clearly bounded walk after the core route has finished."""
    extension = route["extension"]
    mapped = [stop for stop in extension["stops"] if stop.get("mapQuery")]
    links = []
    if extension.get("mapOriginQuery") and mapped:
        links.append(external(
            maps_route_from(extension["mapOriginQuery"], mapped),
            "Open the Charlton extension",
        ))
    # Folded: it is optional, it is four more stops on a long page, and the
    # summary already says how much further it goes.
    return (
        '<section class="route-section route-section--folded route-extension">'
        '<details><summary><div>'
        f'<p class="eyebrow">{e(extension["eyebrow"])}</p>'
        f'<h2 class="section-head">{e(extension["title"])}</h2>'
        f'<p class="meta">{e(extension["distance"])}<span class="separator"> · </span>'
        f'{e(extension["duration"])}</p>'
        '</div></summary>'
        '<div class="route-section__folded-body">'
        f'<p>{e(extension["intro"])}</p>'
        + (f'<p class="links-line">{"".join(links)}</p>' if links else "")
        + route_map(route, base, extension=True)
        + render_stops(
            extension["stops"],
            extension.get("mapOriginQuery"),
            first_walking_label="Walk here from Woolwich",
        )
        + "</div></details></section>"
    )


# --- pages --------------------------------------------------------------


def write_config_js():
    """Generate assets/js/config.js from site.json.

    It used to be edited by hand, which made it the second place a fact about
    this site lived. Now there is one."""
    lines = [
        "// Generated by scripts/build_almanac_pages.py from data/site.json.",
        "// Do not edit: set forms.* there and rebuild. Null means the form is",
        "// shut, and forms.js disables its fields and says so on the page.",
        "window.SITE_CONFIG = {",
    ]
    for name in ("emailEndpoint", "feedbackEndpoint", "contactEndpoint"):
        value = FORMS.get(name)
        lines.append(f"  {name}: {json.dumps(value)},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    (ROOT / "assets" / "js" / "config.js").write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_open_forms_are_described():
    """A form may not open while the notice still has a question in it.

    The closed notice promises that the form will name the processor, the
    purpose, the retention period and the contact route. Two of those are not
    in Formspree's published policy, so the open copy carries TO CONFIRM where
    the answer belongs, and this refuses to ship it."""
    if not FORMS_OPEN:
        return
    for section in load("almanac.json")["privacy"]["sections"]:
        for text in section.get("whenFormsOpen", []):
            if "TO CONFIRM" in text:
                raise SystemExit(
                    "Build stopped. A form endpoint is set, but the privacy notice still "
                    "says TO CONFIRM:\n  " + text + "\n\nAnswer it in data/almanac.json "
                    "-> privacy, or take the endpoint back out of data/site.json."
                )


def check_no_form_opens_behind_the_notice():
    """A form is open if it can reach a processor — by either route.

    config.js is generated, so the JavaScript path cannot drift from
    site.json. The other path is an `action` on the <form> itself, which is
    how a form submits without JavaScript, and which has to be written by hand
    because the feedback page keeps its own markup. That hand-written
    attribute is a second switch, and it would open the form while site.json
    still said shut and the notice still said "not connected to a processor".

    So the two have to agree: every outward form action must be an endpoint
    site.json knows about, and it is checked against the built pages rather
    than the source."""
    known = {url for url in FORMS.values() if url}
    wrong = []
    for page in sorted(ROOT.rglob("*.html")):
        for action in re.findall(r'<form[^>]+action="(https?://[^"]+)"', page.read_text(encoding="utf-8")):
            if action.split("?")[0] not in known:
                wrong.append(f"{page.relative_to(ROOT)} posts to {action}")
    if wrong:
        raise SystemExit(
            "Build stopped. A form posts somewhere data/site.json does not list, so the "
            "privacy notice would describe a form that is shut while this one is open:\n  "
            + "\n  ".join(wrong)
        )


def contact_link(text):
    """Replace {contact} with the address from site.json, as a mailto link.

    The notice used to promise that a contact "will be added"; the address is
    a fact about the site rather than copy, so it lives with the deploy
    address and is substituted here, the way {termsLink} already is."""
    if "{contact}" not in text:
        return text
    assert CONTACT, "data/site.json needs a contact address: the privacy notice asks for one"
    return text.replace(
        "{contact}", f'<a href="mailto:{e(CONTACT)}">{e(CONTACT)}</a>'
    )


def check_one_contact_address():
    """Every address the site offers has to be the address in site.json.

    The privacy notice gets it from there, but the contact page is one of the
    pages whose markup is preserved, so its address is written by hand. Two
    copies of a fact drift; this is what stops them."""
    wrong = []
    for page in sorted(ROOT.rglob("*.html")):
        for found in re.findall(r"mailto:([^\"'?\s]+)", page.read_text(encoding="utf-8")):
            if CONTACT and found != CONTACT:
                wrong.append(f"{page.relative_to(ROOT)} offers {found}")
    if wrong:
        raise SystemExit(
            f"Build stopped. site.json says the contact address is {CONTACT}:\n  "
            + "\n  ".join(wrong)
        )


def social_tags(title, description, path, image="site-redesign.png", og_type="website"):
    """The og: and twitter: block for a page that is not a route.

    These pages had none at all, so a link to the site root — the first link
    anybody shares — expanded to nothing in a messenger. Each page brings its
    own title and description; the picture is shared between them, because a
    picture's job here is to say which publication this is, and a privacy
    notice has no facts of its own to put on a card.

    The image is named only when the file is on disk, the rule the route
    pages already follow, so a card that was never drawn is never promised.
    The shared cover is a versioned design asset rather than generated copy:
    route facts can be rebuilt deterministically, while the publication image
    changes only when the visual direction changes.
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
    <link rel="preload" href="{base}assets/fonts/newsreader-variable-latin.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="preload" href="{base}assets/fonts/work-sans-variable-latin.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="{base}assets/css/almanac-tokens.css">
    <link rel="stylesheet" href="{base}assets/css/almanac.css">
    <script defer src="{base}assets/js/site-head.js"></script>{analytics_tags(base)}
  </head>
  <body data-base-path="{base}">
    <a class="skip-link" href="#main">Skip to content</a>
    <div class="{page_class}">
      {site_head(base, path)}
{body}
    </div>
  </body>
</html>
"""


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def latest_field_walk(routes):
    """The walked route whose lastChecked names the most recent month, as
    (route, "August 2026"); None when no walked route carries a date."""
    dated = []
    for route in routes:
        if not route_walked(route):
            continue
        found = re.search(r"(" + "|".join(MONTHS) + r")\s+(\d{4})", route["editorialControl"].get("lastChecked") or "")
        if found:
            dated.append(((int(found.group(2)), MONTHS.index(found.group(1))), route, f"{found.group(1)} {found.group(2)}"))
    if not dated:
        return None
    _, route, label = max(dated, key=lambda item: item[0])
    return route, label


def home_standing(routes, base):
    """The hero's aside states where the guide stands, in numbers the data
    can back, instead of restating the lead a third time."""
    walked = [route for route in routes if route_walked(route)]
    total, count = len(routes), len(walked)
    walked_phrase = (
        "none walked in person yet" if count == 0
        else "one walked in person" if count == 1
        else f"{count} walked in person"
    )
    drafts = total - count
    drafts_phrase = (
        "" if drafts == 0
        else " The other one is a draft, and says so." if drafts == 1
        else f" The other {drafts} are drafts, and say so."
    )
    latest = latest_field_walk(routes)
    latest_line = ""
    if latest:
        route, label = latest
        latest_line = (
            f'<p>Latest field walk: <a href="{base}routes/{e(route["slug"])}/">'
            f'{e(discovery_for(route)["cardTitle"])}</a>, {e(label)}.</p>'
        )
    return (
        '<aside class="home-hero__aside" aria-label="Where the guide stands">'
        '<p class="eyebrow">Where things stand</p>'
        f'<p><strong>{total} walks, {walked_phrase}.</strong>{e(drafts_phrase)}</p>'
        f'{latest_line}'
        '</aside>'
    )


def home(routes, almanac):
    base = "./"
    by_slug = {route["slug"]: route for route in routes}
    featured = [by_slug[slug] for slug in almanac["home"]["featured"]]

    description = "Curated walks in and around London, walked in person where noted, with good stops along the way."
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

    cards = "".join(route_card(route, base, heading_level=3) for route in featured)
    moods = [
        ("Green & quiet", "green", "Parks, heaths and a little less city noise."),
        ("Canal-side", "riverside-canal", "Towpaths, rivers and somewhere to pause."),
        ("Urban", "urban", "Streets with enough character to carry the day."),
        ("Architecture", "architecture", "Old rooms, odd buildings and useful detours."),
        ("Pub at the end", "pub", "A walk that knows where it wants to finish."),
        ("Outside London", "quiet", "A train out and a proper day on foot."),
    ]
    mood_links = "".join(
        '<a class="mood-link" '
        f'href="{base}find-your-route/?'
        + ('location=outside-london' if label == "Outside London" else f'mood={e(mood)}')
        + f'"><strong>{e(label)}</strong><span>{e(copy)}</span></a>'
        for label, mood, copy in moods
    )
    parts = [
        '<section class="home-hero">'
        '<div class="home-hero__copy">'
        '<p class="home-hero__eyebrow">Independent walks in and around London</p>'
        '<h1 class="home-hero__title">Where shall we go this weekend?</h1>'
        '<p class="home-hero__lead">Curated walks in and around London, walked in person where noted, with good stops along the way.</p>'
        '<div class="button-row home-hero__actions">'
        f'<a class="button button--primary" href="{base}find-your-route/">Find a walk</a>'
        f'<span class="home-hero__or">or <a href="{base}routes/">browse all {len(routes)} walks</a></span>'
        '</div></div>'
        f'{home_standing(routes, base)}</section>',
        '<section class="discovery-section">'
        '<div class="section-heading"><div><p class="eyebrow">Three good starting points</p>'
        '<h2>Start here</h2></div>'
        f'<a href="{base}routes/">See all {len(routes)} walks</a></div>'
        f'<div class="route-grid">{cards}</div></section>',
        '<section class="discovery-section">'
        '<div class="section-heading"><div><p class="eyebrow">Start with a feeling</p>'
        '<h2>Choose by mood</h2></div><p>Pick one thing that sounds right. You can narrow it down afterwards.</p></div>'
        f'<div class="mood-grid">{mood_links}</div></section>',
        '<section class="discovery-section">'
        '<div class="trust-panel"><div><p class="eyebrow">How these walks are chosen</p>'
        '<h2>Useful first. Atmospheric second.</h2></div>'
        '<div><h3>Walked where stated</h3><p>Field-checked walks are marked clearly. Drafts stay honest about what still needs testing.</p></div>'
        '<div><h3>Independent by design</h3><p>No paid placements or algorithmic rankings: just routes with a beginning, a pause and an easy way home.</p></div>'
        '</div></section>',
    ]
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
        f'<h3 class="index-row__title"><a href="{base}routes/{e(route["slug"])}/">{e(route["title"])}</a></h3>'
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
    cards = "".join(route_card(route, base, heading_level=2) for route in walked_first(routes))

    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        '    <meta name="description" content="Browse independent walks in London and full days out by public transport.">',
        *social_tags(
            "Walks",
            "Browse independent walks in London and full days out by public transport.",
            "routes/",
        ),
        "    <title>Walks | London, Slightly Elsewhere</title>",
    ])

    body = (
        '      <main id="main">'
        '<header class="browse-head">'
        '<p class="eyebrow">Browse all walks</p>'
        '<h1>Walks</h1>'
        '<p>Neighbourhood afternoons and full days out, with the details you need to compare them quickly.</p>'
        '</header>'
        '<div class="segmented-control" data-browse-controls aria-label="Filter walks by location">'
        '<button type="button" data-location-filter="all" aria-pressed="true">All walks</button>'
        '<button type="button" data-location-filter="london" aria-pressed="false">London</button>'
        '<button type="button" data-location-filter="outside-london" aria-pressed="false">Outside London</button>'
        '</div>'
        f'<p class="quiet-line" data-browse-meta role="status">{len(routes)} walks</p>'
        f'<section class="discovery-section"><div class="route-grid" data-index>{cards}</div></section>'
        "</main>\n"
        f"      {apparatus(almanac, base, current='routes/')}\n"
        f'      <script src="{base}assets/js/condition-filter.js"></script>'
    )
    return shell(head, body, base, path="routes/")


def finder_page(routes, almanac):
    base = "../"
    cards = "".join(
        route_card(route, base, heading_level=3, finder=True, hidden=index >= 3)
        for index, route in enumerate(walked_first(routes))
    )
    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        '    <meta name="description" content="Choose a walk by time, mood and location.">',
        *social_tags("Find a walk", "Choose a walk by time, mood and location.", "find-your-route/"),
        "    <title>Find a walk | London, Slightly Elsewhere</title>",
    ])
    time_choices = [
        ("1-2-hours", "1–2 hours"),
        ("half-day", "Half day"),
        ("full-day", "Full day"),
    ]
    mood_choices = [
        ("green", "Green"),
        ("riverside-canal", "Riverside / canal"),
        ("urban", "Urban"),
        ("architecture", "Architecture"),
        ("pub", "Pub"),
        ("quiet", "Quiet"),
    ]
    location_choices = [("london", "London"), ("outside-london", "Outside London")]

    def choices(name, values):
        return "".join(
            '<label class="choice">'
            f'<input type="radio" name="{e(name)}" value="{e(value)}">'
            f'<span>{e(label)}</span></label>'
            for value, label in values
        )

    body = (
        '      <main id="main">'
        '<header class="page-intro"><p class="eyebrow">A smaller shortlist</p>'
        '<h1>Find a walk</h1><p>Three quick choices, then a few walks that fit the day you actually have.</p></header>'
        '<div class="finder-layout">'
        '<form class="finder-panel" data-finder-form>'
        '<div class="finder-group"><fieldset><legend>How long have you got?</legend>'
        f'<div class="choice-grid">{choices("time", time_choices)}</div></fieldset></div>'
        '<div class="finder-group"><fieldset><legend>What do you feel like?</legend>'
        f'<div class="choice-grid">{choices("mood", mood_choices)}</div></fieldset></div>'
        '<div class="finder-group"><fieldset><legend>Where?</legend>'
        f'<div class="choice-grid">{choices("location", location_choices)}</div></fieldset></div>'
        # Filtering is live, so there is nothing to submit. On a phone the
        # results sit below a tall panel: a jump link carries the count down.
        '<div class="button-row"><a class="button button--primary finder-jump" href="#finder-results-title" data-finder-jump>'
        'Show matching walks <span aria-hidden="true">↓</span></a>'
        '<button class="button button--secondary" type="reset">Clear choices</button></div>'
        '</form>'
        '<section class="finder-results" aria-labelledby="finder-results-title">'
        '<div class="section-heading"><div><p class="eyebrow">Your shortlist</p>'
        '<h2 id="finder-results-title" tabindex="-1">Walks to consider</h2></div></div>'
        '<p class="quiet-line" data-results-meta role="status">Three good places to start. Choose anything that matters to narrow them down.</p>'
        f'<div class="route-grid" data-finder-results>{cards}</div>'
        f'<noscript><p class="finder-empty">Filtering needs JavaScript. You can still <a href="{base}routes/">browse every walk</a>.</p></noscript>'
        '</section></div></main>\n'
        f"      {apparatus(almanac, base, current='find-your-route/')}\n"
        f'      <script src="{base}assets/js/finder.js"></script>'
    )
    return shell(head, body, base, path="find-your-route/")


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
    # The feedback form's route list is markup so it works without
    # JavaScript; forms.js refreshes it from the data at run time. Refresh
    # it here too, or the no-script list names routes by their old titles.
    if ROUTE_TITLES:
        options = '<option value="">Choose one</option>' + "".join(
            f"<option>{e(title)}</option>" for title in ROUTE_TITLES
        )
        inner = re.sub(
            r'(<select id="route" name="route" required>).*?(</select>)',
            lambda m: m.group(1) + options + m.group(2),
            inner, flags=re.S,
        )
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


def check_status_vocabularies_agree(routes):
    """A route may not be walked and unverified on the same page.

    Putney said "Personally field-checked – July 2026" in its head and
    "unverified – details not yet reconfirmed" six lines below, because
    fieldNote.verified was left false when almanac.walked was authored. Two
    vocabularies for one fact is 4.6; this is the half of it a build can
    police."""
    wrong = [
        r["slug"] for r in routes
        if (r.get("fieldNote") or {}).get("text")
        and bool((r.get("almanac") or {}).get("walked"))
        and not (r.get("fieldNote") or {}).get("verified")
    ]
    if wrong:
        raise SystemExit(
            "Build stopped. These routes are marked walked but their field note still "
            "says unverified, so the page contradicts itself:\n  " + "\n  ".join(wrong)
            + "\n\nSet fieldNote.verified in data/routes.json, or unset almanac.walked."
        )


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

    Every script the site loads is now in the repository, GoatCounter's
    count.js included: it is vendored by scripts/vendor_count_js.py with its
    two storage lines taken out, so the scan below covers it like any other
    file. The checks after the loop keep the arrangement that makes it work —
    no_onload and analytics.js together, and never the CDN copy, which still
    writes to the device from a branch no filter of ours can reach.
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

        if "assets/js/count.js" in text:
            if "no_onload" not in text:
                problems.append(
                    f"{where} loads count.js without no_onload: it would count on load, "
                    "before the filter that honours Do Not Track is in place"
                )
            if "assets/js/analytics.js" not in text:
                problems.append(
                    f"{where} loads count.js without analytics.js: nothing would install "
                    "the filter, so Do Not Track and Global Privacy Control would be ignored"
                )
        if "gc.zgo.at" in text:
            problems.append(
                f"{where} loads count.js from the CDN. The copy in assets/js is the one "
                "with the #toggle-goatcounter block taken out; the CDN copy still writes "
                "to the device. See scripts/vendor_count_js.py"
            )

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
        elif "whenFormsOpen" in section:
            paragraphs = section["whenFormsOpen" if FORMS_OPEN else "whenFormsClosed"]
        else:
            paragraphs = section["whenAnalyticsOn" if GOATCOUNTER else "whenAnalyticsOff"]
        blocks.append(f'<h2>{e(section["head"])}</h2>')
        blocks += [f"<p>{contact_link(e(text))}</p>" for text in paragraphs]

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


def thanks_page(almanac):
    """Where the feedback form lands a reader who has no JavaScript.

    The form posts straight to Formspree, and `_next` sends the reader back
    here rather than to a page with somebody else's name on it. With
    JavaScript the page is never reached: forms.js posts in the background
    and writes the same news into the page itself.

    Not in the sitemap, and noindex: it is a destination, not something to
    find."""
    spec = almanac["thanks"]
    base = "../../"
    head = "\n".join([
        '    <meta charset="utf-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1">',
        f'    <meta name="description" content="{e(spec["intro"])}">',
        '    <meta name="robots" content="noindex">',
        f'    <title>{e(spec["pageTitle"])}{TITLE_SUFFIX}</title>',
    ])
    body = (
        '      <main id="main">'
        '<section class="page-intro">'
        f'<p class="eyebrow">{e(spec["eyebrow"])}</p>'
        f'<h1>{e(spec["title"])}</h1>'
        f'<p>{e(spec["intro"])}</p>'
        f'<p class="links-line"><a href="{base}{e(spec["href"])}">{e(spec["linkName"])}</a></p>'
        "</section></main>\n"
        f"      {apparatus(almanac, base)}"
    )
    return shell(head, body, base, path="feedback/thank-you/")


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


def related_routes(route, routes):
    here = discovery_for(route)
    here_moods = set(here["moods"])
    candidates = []
    for order, candidate in enumerate(routes):
        if candidate["slug"] == route["slug"]:
            continue
        discovery = discovery_for(candidate)
        overlap = len(here_moods & set(discovery["moods"]))
        same_location = discovery["location"] == here["location"]
        candidates.append((overlap, same_location, -order, candidate))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[3] for item in candidates[:3]]


def route_page(route, routes, almanac, venue_timing):
    base = "../../"
    a = route.get("almanac") or {}
    is_day_walk = route["routeType"] == "day-walk"
    facts = route["quickFacts"]
    navigation = route.get("navigation")
    editorial = route["editorial"]
    copy = route["copy"]
    feedback = e(f"{base}feedback/?route={quote(route['title'], safe='')}")

    last_checked = route["editorialControl"].get("lastChecked") or "Not yet field-checked"
    flow = '<span class="separator"> · </span>'.join(
        e(FLOW_LABELS.get(stop["type"], stop["type"])) for stop in route["stops"]
    )

    status = route_status_label(route)
    if route["status"] not in {"field-checked", "published"}:
        status += " · verify live details"
    map_url = None
    if navigation:
        map_url = maps_directions(None, navigation["arrival"]["pinQuery"], "transit")
    map_event = (
        f' data-goatcounter-click="maps/{e(route["slug"])}"' if GOATCOUNTER else ""
    )
    walked = route_walked(route)
    # One "start" action for the page. A walked route earns the primary
    # button and, on a phone, a floating copy that follows the reader; a
    # draft gets directions as a secondary action under a kicker that
    # already says to verify the details.
    map_cta = ""
    if map_url:
        map_cta = (
            f'<a class="button {"button--primary primary-map" if walked else "button--secondary"}"'
            f'{map_event} href="{e(map_url)}" rel="noopener" target="_blank">'
            f'{"Start in Google Maps" if walked else "Directions to the start"}'
            '<span class="visually-hidden"> (opens in a new tab)</span></a>'
        )
    visual = route_media(route, base, card=False)
    head_block = (
        f'<header class="route-head{" route-head--with-visual" if visual else ""}">'
        '<div class="route-head__content">'
        f'<p class="route-head__kicker">{e(status)}</p>'
        f'<h1 class="route-head__title">{e(route["title"])}</h1>'
        f'<p class="route-head__lead">{e(route["subtitle"])}</p>'
        '</div>'
        f'{visual}'
        '</header>'
    )

    # The essentials live once, in a rail: beside the route on a wide
    # screen and sticky there, between the title and the route on a phone.
    # Terrain notes for a day walk stay in their own section below.
    facts_list = [
        ("Distance", route_distance(route)),
        ("Time", facts["duration"]),
        ("Effort", route_difficulty(route)),
    ]
    if is_day_walk:
        # A full day out has a few more facts worth deciding on, and they
        # belong here with the others, not in a second table further down.
        hike, travel = route["hike"], route["travel"]
        if hike.get("walkingTime"):
            facts_list.append(("Walking time", hike["walkingTime"]))
        if hike.get("elevationGainM") is not None:
            facts_list.append(("Elevation", f'{hike["elevationGainM"]} m gain'))
        shape = "Station to station" if hike["routeShape"] == "point-to-point" else hike["routeShape"].capitalize()
        facts_list.append(("Route shape", shape))
        facts_list.append(("Shorter version", "Available" if hike["shortenable"] else "Not planned"))
        journey = "one change" if travel["journeyComplexity"] == "one-change" else "direct"
        facts_list.append((
            "Leave from",
            f'{" / ".join(format_hub(hub) for hub in travel["departureHubs"])} · '
            f'about {travel["typicalMinutes"]} min, {journey}',
        ))
    facts_list += [
        ("Start", route_start(route)),
        ("Finish", route_finish(route)),
        ("Best time", facts["bestTime"]),
    ]
    facts_html = "".join(
        f'<div class="route-rail__fact"><dt>{e(term)}</dt><dd>{e(value)}</dd></div>'
        for term, value in facts_list
    )
    rail = (
        '<aside class="route-rail" aria-labelledby="essentials-title">'
        '<div class="route-rail__inner">'
        '<p class="eyebrow">Before you decide</p>'
        '<h2 id="essentials-title" class="route-rail__title">Walk essentials</h2>'
        f'<dl class="route-rail__facts">{facts_html}</dl>'
        f'<p class="meta"><span class="visually-hidden">Route at a glance: </span>{flow}</p>'
        f'<div class="route-actions">{map_cta}<a class="quiet" href="{base}routes/">All walks</a></div>'
        f'<p class="quiet-line">Last checked: {e(last_checked)}. Verify opening hours and access before going.</p>'
        '</div></aside>'
    )
    startbar = ""
    if map_cta and walked:
        startbar = (
            '<div class="route-startbar">'
            f'<a class="button button--primary primary-map"{map_event} href="{e(map_url)}" '
            'rel="noopener" target="_blank">Start in Google Maps'
            '<span class="visually-hidden"> (opens in a new tab)</span></a></div>'
        )

    warnings = ruled_list(editorial["practicalWarnings"])
    sections = [
        section("Good to know.", warnings),
    ]

    note = route.get("fieldNote")
    if note and note.get("text"):
        flag = "" if note.get("verified") else paragraph(
            "Desk-checked or awaiting another field walk – details not yet reconfirmed.", quiet=True
        )
        note_head = "Last walked." if note.get("verified") else "Desk-checked note."
        sections.append(section(note_head, flag, paragraph(note["text"])))

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
            "Reports are reviewed; only my own walk marks a route walked."
        )
    else:
        community_head = None
    if community_head:
        sections.append(section(
            community_head,
            paragraph(community_body),
            f'<p class="links-line"><a href="{feedback}">Share a field note</a></p>',
        ))
    else:
        # Nobody has written in yet. That is a line under the last section
        # with a voice in it — the field note, or failing that "Good to
        # know" — not a heading of its own on every page.
        sections[-1] = sections[-1].replace(
            "</section>",
            f'<p class="quiet-line">No field notes from readers yet — '
            f'<a href="{feedback}">share one</a> if you walk it.</p></section>',
        )

    if is_day_walk:
        # The journey facts are in the rail; what remains is the advice about
        # the service and where to check it, which no table can hold.
        travel = route["travel"]
        blocks = [paragraph(travel["serviceNote"])]
        if travel.get("officialSourceUrl"):
            blocks.append(
                '<p class="links-line">'
                + external(travel["officialSourceUrl"], "Check operator information")
                + "</p>"
            )
        sections.append(section("Start with the train, not a car.", *blocks))

    if navigation:
        arrival = navigation["arrival"]
        mapped = [stop for stop in route["stops"] if stop.get("mapQuery")]
        whole_walk = (
            maps_route(mapped)
            if route["routeType"] != "day-walk" and arrival.get("station") and 0 < len(mapped) <= 10
            else None
        )
        links = []
        if whole_walk:
            links.append(external(whole_walk, "Open the whole walk"))
        if navigation.get("externalRouteUrl"):
            links.append(external(navigation["externalRouteUrl"], "Open detailed route"))
        if navigation.get("gpxUrl"):
            links.append(external(navigation["gpxUrl"], "Download GPX"))
        sections.append(section(
            "Start without guessing.",
            definition("Suggested arrival", f'{arrival["station"]} – {arrival["stationExit"]}'),
            # pinQuery is the string sent to Google Maps. It was printed
            # under the pin as if it were content; it belongs in the link.
            definition("Set your first pin", arrival["pinLabel"]),
            f'<p class="links-line">{"".join(links)}</p>' if links else "",
            paragraph(navigation["disclaimer"], quiet=True),
            paragraph("We never ask for your location.", quiet=True),
        ))

    sections.append(section(editorial["vibeSummary"], paragraph(route["routeNarrative"])))

    # Who it suits. Was three sections — Best for, Not ideal for, What not to
    # expect — with the audience notes another six screens down under "Notes
    # before you go". All four answer one question, and split apart they said
    # the same things twice: "a second or third date" appeared in both the
    # list and the note.
    sections.append(section(
        "Who it suits, and who it does not.",
        ruled_list(editorial["bestFor"]),
        '<h3 class="subhead">Not ideal for</h3>',
        ruled_list(editorial["notIdealFor"]),
        paragraph(editorial["whatNotToExpect"], quiet=True),
        definition("On a date", copy["dateNotes"]),
        definition("With friends", copy["friendGroupNotes"]),
        definition("Alone", copy["soloNotes"]),
    ))

    map_start = (navigation or {}).get("arrival", {}).get("mapOriginQuery") or (
        navigation or {}
    ).get("arrival", {}).get("station")
    detours = optional_detours_section(route.get("optionalDetours"))
    if detours:
        sections.append(detours)
    sections.append(section(
        "The route.",
        route_map(route, base),
        render_stops(route["stops"], map_start, first_walking_label="Walk here from the station"),
    ))

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
        access_label = finish.get("accessLabel") or "Nearest practical station"
        access_value = finish.get("accessValue") or finish["nearestStation"]
        blocks = [
            definition(finish["label"], f'{access_label}: {access_value}'),
            paragraph(finish["exitNote"]),
        ]
        early = (route.get("hike") or {}).get("earlyExit") if is_day_walk else None
        if early:
            note = f' – {early["note"]}' if early.get("note") else ""
            blocks.append(paragraph(f'Earlier exit: {early["label"]}{note}'))
        if finish.get("mapQuery"):
            finish_links = [external(maps_search(finish["mapQuery"]), finish.get("mapLinkLabel") or "Open exit station")]
        else:
            # "Putney Bridge Underground or Putney rail" is two stations; a
            # search for the whole phrase finds neither. One link each.
            stations = [name.strip() for name in re.split(r"\s+or\s+|\s+/\s+", finish["nearestStation"]) if name.strip()]
            def station_query(name):
                return name if re.search(r"station|pier|bus", name, re.I) else f"{name} station"
            if len(stations) == 1:
                finish_links = [external(maps_search(station_query(stations[0])), finish.get("mapLinkLabel") or "Open exit station")]
            else:
                finish_links = [external(maps_search(station_query(name)), f"Open {name}") for name in stations]
        if finish.get("officialUrl"):
            finish_links.append(external(finish["officialUrl"], "Check the current service"))
        blocks.append(f'<p class="links-line">{"".join(finish_links)}</p>')
        sections.append(section("Finish and easy exit.", *blocks))

    if route.get("extension"):
        sections.append(extension_section(route, base))

    timing = venue_timing.get(route.get("valueTimingVenueId")) if route.get("valueTimingVenueId") else None
    if timing:
        sections.append(section(
            timing["title"],
            paragraph(timing["detail"]),
            f'<p class="links-line">{external(timing["sourceUrl"], timing["sourceLabel"])}</p>',
            f'<p class="meta">{e(timing["label"])}<span class="separator"> · </span>'
            f'checked {e(timing["checked"])}</p>',
            folded=True,
        ))

    # Before you go: the two facts you check while deciding when.
    sections.append(section(
        "Before you go.",
        definition("Best time", facts["bestTime"]),
        definition("Food and drink", copy["foodDrinkNotes"]),
        folded=True,
    ))

    # How the day can change. Was two sections — the versions, and the three
    # contingencies — plus the practical warnings stranded at the bottom of
    # "What not to expect", which is not what that section was about.
    sections.append(section(
        "How the day can change.",
        *[
            definition(
                version["label"],
                version["description"],
                meta=f'{version["duration"]} · {version["budget"]}'
                + (" · ticket check required" if version.get("requiresTicketCheck") else ""),
            )
            for version in route["versions"]
        ],
        definition("If it rains", copy["rainyDayBackup"]),
        definition("If it goes well", copy["continueIfGoingWell"]),
        definition("If you want to leave early", copy["exitEarly"]),
        folded=True,
    ))

    final = []
    if route.get("soundtrack"):
        final.append(
            f'<p class="quiet-line">This day sounds like: {e(route["soundtrack"]["artist"])} – '
            f'<em>{e(route["soundtrack"]["track"])}</em></p>'
        )
    # A closing note only earns a section when it has something of its own to
    # say: on Putney it restated the shape of the day a fourth time. The five
    # routes with a soundtrack keep the section either way, since the
    # soundtrack line lives in it.
    if copy["finalEditorialNote"] or final:
        sections.append(section(copy["finalEditorialNote"] or "One more thing.", *final))

    related = "".join(
        route_card(candidate, base, heading_level=3)
        for candidate in related_routes(route, routes)
    )
    related_block = (
        '<section class="discovery-section related-walks">'
        '<div class="section-heading"><div><p class="eyebrow">Keep walking</p>'
        '<h2>If you liked this walk…</h2></div></div>'
        f'<div class="route-grid">{related}</div></section>'
    )
    closing = (
        '<section class="discovery-section"><div class="trust-panel">'
        '<div><p class="eyebrow">Help keep it useful</p><h2>What changed?</h2></div>'
        '<div><p>Closed gates, changed hours and the point where you bailed are more useful than polite applause.</p>'
        f'<p><a class="button button--secondary" href="{feedback}">Give feedback on this walk</a></p></div>'
        '</div></section>'
    )

    body = (
        f'      <main id="main">'
        f'{head_block}<div class="route-layout">{rail}'
        f'<div class="route-content">{"".join(sections)}</div></div>'
        f'{related_block}{closing}{startbar}</main>\n'
        f"      {apparatus(almanac, base, current='routes/')}"
    )
    return shell(route_head_meta(route), body, base, path=f'routes/{route["slug"]}/')


ROUTE_TITLES = []


def main():
    # Before anything is written: a failed build must not leave a form open
    # with the notice still carrying a question.
    check_open_forms_are_described()
    routes = load("routes.json")
    ROUTE_TITLES[:] = [route["title"] for route in routes]
    almanac = load("almanac.json")
    venue_timing = load("venue-timing.json")
    by_slug = {route["slug"]: route for route in routes}

    (ROOT / "index.html").write_text(home(routes, almanac), encoding="utf-8")
    print("Wrote index.html.")

    (ROOT / "routes" / "index.html").write_text(index_page(routes, almanac), encoding="utf-8")
    print(f"Wrote routes/index.html with {len(routes)} cards.")

    (ROOT / "find-your-route" / "index.html").write_text(
        finder_page(routes, almanac), encoding="utf-8"
    )
    print("Wrote find-your-route/index.html.")

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

    thanks = ROOT / "feedback" / "thank-you"
    thanks.mkdir(parents=True, exist_ok=True)
    (thanks / "index.html").write_text(thanks_page(almanac), encoding="utf-8")
    print("Wrote feedback/thank-you/index.html (where a form posts without JavaScript).")

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
        target.write_text(route_page(route, routes, almanac, venue_timing), encoding="utf-8")
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

    write_config_js()
    print('Wrote assets/js/config.js (' + ('forms open: ' + ', '.join(
        name for name, url in FORMS.items() if url) if FORMS_OPEN else 'every form shut') + ').')

    check_status_vocabularies_agree(routes)
    check_one_contact_address()
    check_no_form_opens_behind_the_notice()
    report_photographs_without_a_webp(routes)
    check_leading_comes_from_tokens()
    check_nothing_is_stored()
    print("Checked: no page stores or reads anything on a visitor's device.")


if __name__ == "__main__":
    main()
