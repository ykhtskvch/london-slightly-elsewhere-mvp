# London, Slightly Elsewhere — static MVP

This is the dependency-free static site for Slightly Elsewhere: a modern
walk-discovery product with an editorial voice.

The visual and interaction rules live in `DESIGN.md`. Read that file before adding a page or component.

## Run locally

From this directory, run a static server rather than opening `index.html`
directly. The main pages are pre-rendered, while feedback route choices and
the finder enhancements expect normal HTTP behaviour.

```bash
ruby -run -e httpd . -p 8000
```

Then open `http://localhost:8000`.

## Files that matter

- `data/site.json` — where the site is deployed, and whether analytics is on.
  The only place the host and the path prefix are written down. Moving to a
  custom domain is `origin` plus `basePath` and a rebuild; nothing else in the
  build may hardcode either. `analytics.goatcounter` is null until the privacy
  notice describes it.
- `data/routes.json` — the single source of truth for all routes.
- `data/discovery.json` — controlled card titles, time bands, London/outside
  location and mood tags for every walk. Validation requires exact coverage.
- `data/almanac.json` — editorial, privacy, glossary and page-level copy;
  per-walk authored material lives under each route's `almanac` key.
- `scripts/build_almanac_pages.py` — builds every page. Route pages, the
  homepage, Walks, Find a walk and the glossary are generated in full; utility
  pages keep their `<main>` and receive the shared shell. It also owns the one
  Route Card component used everywhere.
- `assets/js/condition-filter.js` — progressively enhances Walks with the
  London / Outside London switch. All cards read without it.
- `scripts/generate_icons.py` — draws the favicon at every size from the
  palette. Run it after changing the colours; the build does not.
- `scripts/vendor_count_js.py` — fetches GoatCounter's `count.js`, removes
  the two lines that touch browser storage, and writes it into `assets/js`
  so the site serves it itself. Run it after a GoatCounter update and read
  the diff; it stops rather than writing a copy it could not patch.
- `scripts/generate_og_images.py` — draws the fact-led link-preview card for
  every route. Run it after a route title, fact or deploy address changes;
  the build does not. Non-route pages share the intentionally versioned
  `assets/og/site-redesign.png` editorial cover.
- `scripts/convert_photos.py` — gives every photograph in `assets/photos` a
  WebP twin, about 40% lighter. Run it after adding one; the build does not,
  but it says which photographs are still missing theirs. The JPEG stays as
  the fallback and as what the OG cards use.
- `scripts/render_maps.py` — draws the sketch map on every walk page into
  `assets/maps`: OpenStreetMap tiles, the stops as numbered pins in walking
  order, a dashed line joining them that is not the walked path. Run it from
  the Pillow venv after adding or moving a stop; the build does not, it only
  shows a map that exists. Places come from Nominatim and are cached in
  `data/stop-coordinates.json` — hand-edit a wrong pin there (`"source":
  "hand"`) and run again. A route whose stop cannot be placed is skipped
  and reported rather than drawn wrong.
- `assets/css/almanac-tokens.css` — design tokens for the redesign. Nothing
  in `almanac.css` may use a value that is not defined there.
- `data/venue-timing.json` — one editable record per venue for happy-hour checks, current deals and official source links.
- `assets/js/finder.js` — deterministic time, mood and location matching over
  server-rendered cards, including closest-match behaviour.
- `scripts/validate-routes.js` — dependency-free schema and discovery-data
  coverage checks.
- `assets/js/site-head.js` — loaded by every page: closes the phone menu on
  a tap elsewhere or Escape, and parks a walk page's floating start button
  while the essentials rail is on screen.
- `assets/js/config.js` — generated from `data/site.json`. Do not edit: set
  `forms.*` there and rebuild. Null means that form is shut, and `forms.js`
  disables its fields and says so on the page.
- `routes/<slug>/index.html` — generated in full by the build from
  `data/routes.json`. Not edited by hand, and not a shell any more: the pages
  load no JavaScript and read without it.

## Navigation data

Every route has a `navigation` object. Field-checked routes, pilot routes and carefully researched prototypes can use `anchor-by-anchor` navigation: a precise arrival station, first pin, first move, finish and mapped stops. Other prototypes use `start-only` navigation until their full sequence has been field-tested.

Mapped stops can include `locationNote`, `mapQuery` and `directionFromPrevious`. The route template turns these into free Google Maps search and walking-direction links; no Maps API key is required.

## Deals and happy-hour updates

Update `data/venue-timing.json` whenever a venue changes its offer, hours or source page. Each record has a stable venue ID, a short user-facing status, an official URL and a `checked` date.

To attach it to a route, add its ID to `data/routes.json`:

```json
"valueTimingVenueId": "half-moon-putney"
```

Do not publish a regular happy hour unless the venue’s own current page confirms it. If none is confirmed, use the `no-regular-offer-confirmed` status and still link the official page.

## Add another route

1. Copy the JSON shape from `data/routes.json` or the [route-card template](../route-card-template.md).
2. Give it a stable `id` and `slug`.
3. Set `routeType` to `london-day` or `day-walk`; use `soundtrack: null` unless an editorial soundtrack has been chosen.
4. Add it to the JSON array.
5. Add one matching record to `data/discovery.json`; exact coverage is
   required before validation passes.
6. Nothing to copy: the build writes `routes/<slug>/index.html` in full from
   the data. Add an `almanac` block for authored field notes where available.
7. For a `day-walk`, add the required `travel` and `hike` objects before it can pass validation. Use only checked journey and route sources; do not invent a continuous Google Maps route or GPX.
8. Personally field-test it before changing `status` to `field-checked`; reserve `published` for a final public editorial review.

Rebuild the pages and run the data checks before sharing a change:

```bash
python3 scripts/build_almanac_pages.py && node scripts/validate-routes.js && node scripts/validate-site.js
```

Route link-preview images are a separate, less frequent build. The renderer
uses Pillow (`python3 -m pip install Pillow`) and writes all 24 cards
atomically:

```bash
python3 scripts/generate_og_images.py
```

`build_almanac_pages.py` refuses to finish if any built page would store or
read something on a visitor's device: it follows every local `<script src>`
and fails on `localStorage`, `sessionStorage`, `document.cookie` or
`indexedDB`. Every script the site loads is in the repository, GoatCounter's
`count.js` included, so nothing is exempt. It also fails if that script is
loaded without the `no_onload` setting and `analytics.js`, which together
install the filter honouring Do Not Track and Global Privacy Control, and
fails if the CDN copy is ever used instead of the vendored one. The privacy
notice makes those promises, so the build keeps them.
`DESIGN.md` is the current product and visual authority. `DESIGN-CONFLICTS.md`
is retained as an archive of the superseded field-guide direction.

## Forms

Route feedback is connected to Formspree and described by the generated
privacy notice. Contact and future-guide collection remain closed.

When opening another form:

1. Choose a form endpoint compatible with static sites.
2. Put the URL in `data/site.json` under `forms` and rebuild. `config.js` is
   written from it, and the privacy notice switches to its open wording in the
   same build.
3. Answer every `TO CONFIRM` in the notice's open wording first. The build
   refuses to open a form while one is left, and it checks before writing
   anything, so a failed build cannot leave the form open and the notice
   unanswered.
4. Submit a test entry from the deployed site.

## Community validation

Community feedback helps keep a route current, but it does not replace an editorial field walk. A route must never become `field-checked` automatically.

When forms are connected, review reports in batches. After two or three recent, internally consistent reports, add a `community` object to that route in `data/routes.json`:

```json
"community": {
  "reportCount": 3,
  "lastReported": "August 2026",
  "status": "reports-received"
}
```

If a report identifies a closure, unsafe connection or materially wrong detail, set `status` to `needs-review` until you have checked or corrected it. Community reports display as a separate signal; only your own editorial walk can set `status` to `field-checked`.

## Deployment

Upload the contents of this directory to any static host. The site uses relative paths, so it also works when hosted under a project subpath, such as a GitLab Pages project URL.

## Launch checks

- Test homepage, finder, every route link and mobile layout.
- Test exact, closest-match and no-filter finder states.
- Test reduced-motion mode. There is one palette and no dark theme.
- Test keyboard navigation, 200% zoom and a 360px viewport.
- Check all external official links.
- Use `field-checked` status only after a real route check.
- Test Formspree delivery before changing feedback copy or fields.
- Update the privacy notice with the form processor, retention period and public contact.
