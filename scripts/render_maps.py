#!/usr/bin/env python3
"""Draw one sketch map per route: OpenStreetMap tiles, the stops as numbered
pins in walking order, a dashed line joining them.

The line joins the stops; it is not the walked path, and the caption on the
page says so. The numbers match the numbered list under "The route.".

Run after adding or moving a stop:

    /tmp/webpenv/bin/python scripts/render_maps.py            # every route
    /tmp/webpenv/bin/python scripts/render_maps.py putney     # one route

Needs Pillow with WebP (see convert_photos.py for the venv) and the network,
twice: Nominatim to place a stop from its mapQuery, and tile.openstreetmap.org
for the background. Both answers are cached so the second run is offline:

  data/stop-coordinates.json   one record per mapQuery. Hand-edit lat/lon
                               when a pin is wrong and run again; the record's
                               "source" then reads "hand".
  .map-tiles/                  tiles, ignored by git.

A route is skipped, loudly, when a stop cannot be placed or lands more than
MAX_SPREAD_KM from the others — a map with a wrong pin is worse than none.
The build reads assets/maps/<slug>.jpg and shows nothing when it is absent.
"""

import json
import math
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROUTES = ROOT / "data" / "routes.json"
COORDS = ROOT / "data" / "stop-coordinates.json"
MAPS = ROOT / "assets" / "maps"
TILES = ROOT / ".map-tiles"

# Both services ask for a way to reach whoever is calling.
USER_AGENT = "slightlyelsewhere.co.uk map build (hello@slightlyelsewhere.co.uk)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

WIDTH, HEIGHT = 1200, 800   # shown at 704px wide on a desk and ~340px on a phone;
                            # pins are sized to still read at the phone scale
PADDING = 110                # px kept clear around the outermost pin
TIGHT_PADDING = 60           # accepted rather than dropping a zoom level
MIN_ZOOM, MAX_ZOOM = 11, 17
MAX_SPREAD_KM = {"london-day": 4.0, "day-walk": 14.0}

INK = (23, 37, 31)
ACCENT = (23, 107, 91)
PAPER = (255, 253, 248)
FONT = "/System/Library/Fonts/Helvetica.ttc"

POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b")
HOUSE_NUMBER = re.compile(r"\b\d+[A-Za-z]?(?:-\d+)?\b")


# --- placing stops ---------------------------------------------------------


OUTWARD = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\b$")


def query_variants(query, london):
    """Nominatim reads addresses, not venue names: 'The Duke's Head 8 Lower
    Richmond Road SW15 1JN' finds nothing, '8 Lower Richmond Road SW15 1JN'
    finds the pub. Try the full text first, then progressively plainer: the
    address from its house number, the postcode alone, then the place name
    losing a word at a time from the end ('Putney Bridge south side' →
    'Putney Bridge')."""
    variants = [query]
    number = HOUSE_NUMBER.search(query)
    if number and number.start() > 0:
        variants.append(query[number.start():])
    postcode = POSTCODE.search(query)
    if postcode:
        variants.append(postcode.group(0))
    name = POSTCODE.sub("", query).strip(" ,")
    name = OUTWARD.sub("", name).strip(" ,")
    words = [w for w in name.split() if w != "London"]
    suffix = ", London" if london else ""
    for end in range(len(words), 1, -1):
        variants.append(" ".join(words[:end]) + suffix)
    seen, out = set(), []
    for v in variants:
        v = v.strip(" ,")
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def nominatim(text):
    params = urllib.parse.urlencode({
        "format": "jsonv2", "limit": 1, "countrycodes": "gb", "q": text,
    })
    request = urllib.request.Request(f"{NOMINATIM}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        results = json.load(response)
    time.sleep(1.1)  # Nominatim's usage policy: at most one request a second
    return results[0] if results else None


def place(query, cache, london):
    if query in cache and cache[query]["lat"] is not None:
        return cache[query]
    for attempt, text in enumerate(query_variants(query, london)):
        hit = nominatim(text)
        if hit:
            cache[query] = {
                "lat": float(hit["lat"]),
                "lon": float(hit["lon"]),
                "source": f"nominatim:{attempt}",
                "matched": text,
                "displayName": hit.get("display_name", ""),
            }
            return cache[query]
    cache[query] = {"lat": None, "lon": None, "source": "none", "matched": None, "displayName": ""}
    return cache[query]


def km_between(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


# --- tiles -----------------------------------------------------------------


def to_world(lat, lon, zoom):
    """Web Mercator, in pixels at this zoom."""
    n = 256 * 2 ** zoom
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def choose_zoom(points):
    """The closest zoom that keeps every pin PADDING clear of the edge —
    or, before giving up a level, one that keeps them TIGHT_PADDING clear.
    Hampstead sat at 14 for the sake of 40px of margin at 15."""
    def fits(zoom, padding):
        xs, ys = zip(*(to_world(lat, lon, zoom) for lat, lon in points))
        return max(xs) - min(xs) <= WIDTH - 2 * padding and max(ys) - min(ys) <= HEIGHT - 2 * padding
    for zoom in range(MAX_ZOOM, MIN_ZOOM - 1, -1):
        if fits(zoom, PADDING) or fits(zoom, TIGHT_PADDING):
            return zoom
    return MIN_ZOOM


def tile(z, x, y):
    path = TILES / str(z) / str(x) / f"{y}.png"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(TILE_URL.format(z=z, x=x, y=y), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            path.write_bytes(response.read())
        time.sleep(0.2)
    return Image.open(path).convert("RGB")


def background(centre_x, centre_y, zoom):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    left, top = centre_x - WIDTH / 2, centre_y - HEIGHT / 2
    for tx in range(int(left // 256), int((left + WIDTH) // 256) + 1):
        for ty in range(int(top // 256), int((top + HEIGHT) // 256) + 1):
            if not (0 <= ty < 2 ** zoom):
                continue
            canvas.paste(tile(zoom, tx % (2 ** zoom), ty), (round(tx * 256 - left), round(ty * 256 - top)))
    return canvas


# --- drawing ---------------------------------------------------------------


def soften(image):
    """Standard tiles are loud next to the site's palette; pull the colour
    back so the pins read first."""
    grey = image.convert("L").convert("RGB")
    return Image.blend(grey, image, 0.55)


def spread_pins(pixels, radius):
    """Two stops on the same corner would draw one pin over the other; nudge
    the later one until both numbers can be read. The line still runs from
    the true positions, so the nudge shows as a short offset, not a move."""
    placed = []
    for x, y in pixels:
        for _ in range(12):
            crowded = [(px, py) for px, py in placed if math.hypot(x - px, y - py) < radius * 2 + 6]
            if not crowded:
                break
            px, py = crowded[0]
            dx, dy = x - px, y - py
            length = math.hypot(dx, dy) or 1
            step = radius * 2 + 8 - length
            x, y = x + dx / length * step + (0 if dx else radius), y + dy / length * step
        placed.append((x, y))
    return placed


def draw_route(canvas, pixels, origin=None):
    """`origin` is a pin the numbering does not count — where an extension
    begins, at the end of the core walk — drawn hollow."""
    draw = ImageDraw.Draw(canvas)
    if origin:
        (ox, oy), (x1, y1) = origin, pixels[0]
        length = math.hypot(x1 - ox, y1 - oy)
        dash, gap, pos = 18, 12, 0
        while pos < length:
            end = min(pos + dash, length)
            t1, t2 = pos / length, end / length
            draw.line([(ox + (x1 - ox) * t1, oy + (y1 - oy) * t1), (ox + (x1 - ox) * t2, oy + (y1 - oy) * t2)], fill=ACCENT, width=7)
            pos += dash + gap
    # Dashed line between consecutive stops.
    for (x1, y1), (x2, y2) in zip(pixels, pixels[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            continue
        dash, gap, pos = 18, 12, 0
        while pos < length:
            end = min(pos + dash, length)
            t1, t2 = pos / length, end / length
            draw.line(
                [(x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1), (x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2)],
                fill=ACCENT, width=7,
            )
            pos += dash + gap
    font = ImageFont.truetype(FONT, 40)
    radius = 36
    for index, (x, y) in enumerate(spread_pins(pixels, radius), start=1):
        draw.ellipse([x - radius - 4, y - radius - 4, x + radius + 4, y + radius + 4], fill=PAPER)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=ACCENT)
        draw.text((x, y - 1), str(index), fill=PAPER, font=font, anchor="mm")
    if origin:
        ox, oy = origin
        draw.ellipse([ox - radius - 4, oy - radius - 4, ox + radius + 4, oy + radius + 4], fill=PAPER)
        draw.ellipse([ox - radius, oy - radius, ox + radius, oy + radius], fill=PAPER, outline=ACCENT, width=5)
        draw.ellipse([ox - 8, oy - 8, ox + 8, oy + 8], fill=ACCENT)
    # Attribution belongs on the image itself, whatever surrounds it later.
    small = ImageFont.truetype(FONT, 24)
    text = "© OpenStreetMap contributors"
    box = draw.textbbox((0, 0), text, font=small)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.rectangle([WIDTH - w - 28, HEIGHT - h - 22, WIDTH, HEIGHT], fill=PAPER)
    draw.text((WIDTH - w - 14, HEIGHT - h - 10), text, fill=INK, font=small)


def place_all(queries, slug, cache, london, limit):
    """Every query placed, or None with the reason printed."""
    placed = []
    for query in queries:
        record = place(query, cache, london)
        if record["lat"] is None:
            print(f"  !! {slug}: cannot place '{query}' — map skipped")
            return None
        placed.append((record["lat"], record["lon"]))
    centre = (sum(p[0] for p in placed) / len(placed), sum(p[1] for p in placed) / len(placed))
    for query, point in zip(queries, placed):
        spread = km_between(centre, point)
        if spread > limit:
            print(
                f"  !! {slug}: '{query}' is {spread:.1f} km from the "
                f"others ({cache[query]['displayName'][:60]}) — map skipped"
            )
            return None
    return placed


def draw_map(points, name, origin_index=None):
    """Points in order; the one at origin_index, if any, is the hollow start."""
    zoom = choose_zoom(points)
    world = [to_world(lat, lon, zoom) for lat, lon in points]
    xs, ys = zip(*world)
    centre_x, centre_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    canvas = soften(background(centre_x, centre_y, zoom))
    pixels = [(x - centre_x + WIDTH / 2, y - centre_y + HEIGHT / 2) for x, y in world]
    origin = None
    if origin_index is not None:
        origin = pixels.pop(origin_index)
    draw_route(canvas, pixels, origin)

    MAPS.mkdir(parents=True, exist_ok=True)
    jpg = MAPS / f"{name}.jpg"
    canvas.save(jpg, "JPEG", quality=74, optimize=True, progressive=True)
    canvas.save(jpg.with_suffix(".webp"), "WEBP", quality=70, method=6)
    return zoom


def render(route, cache):
    london = route["routeType"] == "london-day"
    limit = MAX_SPREAD_KM[route["routeType"]]
    placed = place_all([stop["mapQuery"] for stop in route["stops"]], route["slug"], cache, london, limit)
    if placed is None:
        return None
    zoom = draw_map(placed, route["slug"])

    # An optional extension gets a map of its own, from the pin where the
    # core walk ended, so the core map keeps its zoom.
    extension = route.get("extension")
    if extension:
        queries = [extension["mapOriginQuery"]] + [stop["mapQuery"] for stop in extension["stops"]]
        ext = place_all(queries, f"{route['slug']}-extension", cache, london, limit)
        if ext is not None:
            ext_zoom = draw_map(ext, f"{route['slug']}-extension", origin_index=0)
            print(f"{route['slug']}-extension: {len(extension['stops'])} stops at zoom {ext_zoom}")
    return zoom


def main(argv):
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    wanted = set(argv)
    if wanted:
        routes = [route for route in routes if route["slug"] in wanted]
        missing = wanted - {route["slug"] for route in routes}
        if missing:
            raise SystemExit(f"No such route: {', '.join(sorted(missing))}")

    cache = json.loads(COORDS.read_text(encoding="utf-8")) if COORDS.exists() else {}
    drawn = skipped = 0
    try:
        for route in routes:
            zoom = render(route, cache)
            if zoom is None:
                skipped += 1
                continue
            drawn += 1
            print(f"{route['slug']}: {len(route['stops'])} stops at zoom {zoom}")
    finally:
        COORDS.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    guessed = [q for q, r in cache.items() if r["source"] not in {"nominatim:0", "hand"} and r["lat"] is not None]
    print(f"\nDrew {drawn} maps, skipped {skipped}. {len(cache)} places cached in {COORDS.relative_to(ROOT)}.")
    if guessed:
        print(f"{len(guessed)} places were found only from a plainer form of their query — worth a glance:")
        for q in guessed:
            print(f"  {q}\n    → {cache[q]['matched']}  ({cache[q]['displayName'][:70]})")


if __name__ == "__main__":
    main(sys.argv[1:])
