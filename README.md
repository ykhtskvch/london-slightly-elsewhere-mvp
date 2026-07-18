# London, Slightly Elsewhere — static MVP

This is a dependency-free static prototype for the route-finder MVP.

The visual and interaction rules live in `DESIGN.md`. Read that file before adding a page or component.

## Run locally

From this directory, run a static server rather than opening `index.html` directly. The route pages and finder load `data/routes.json` with `fetch`, which browsers block from `file://` URLs.

```bash
ruby -run -e httpd . -p 8000
```

Then open `http://localhost:8000`.

## Files that matter

- `data/routes.json` — the single source of truth for all routes.
- `data/venue-timing.json` — one editable record per venue for happy-hour checks, current deals and official source links.
- `assets/js/finder.js` — the deterministic six-filter scoring logic.
- `assets/js/route-page.js` — renders all detail pages from JSON.
- `assets/js/theme.js` — light/dark preference with system fallback.
- `assets/js/config.js` — add form endpoints here before public launch.
- `routes/<slug>/index.html` — thin route page shells; set `data-route-id` to the JSON route id.

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
3. Add it to the JSON array.
4. Copy one route directory, rename it to the slug, and update `data-route-id`.
5. Personally field-test it before changing `status` to `field-checked`; reserve `published` for a final public editorial review.

## Forms

The forms deliberately do not send data yet. Their controls are disabled and the interface says that collection is closed. This avoids pretending that feedback works without an endpoint and avoids collecting personal data locally.

Before sharing publicly:

1. Choose a free form endpoint compatible with static sites.
2. Add the relevant URLs to `assets/js/config.js` as `emailEndpoint`, `feedbackEndpoint` and `contactEndpoint`.
3. Submit a test entry from a deployed preview.
4. Add a privacy notice that names the form processor and states what is stored.

## Deployment

Upload the contents of this directory to any static host. The site uses relative paths, so it also works when hosted under a project subpath, such as a GitLab Pages project URL.

## Launch checks

- Test homepage, finder, all fifteen route links and mobile layout.
- Test a first-date query, rainy-day query and no-filter state.
- Test light theme, dark theme and reduced-motion mode.
- Test keyboard navigation, 200% zoom and a 360px viewport.
- Check all external official links.
- Use `field-checked` status only after a real route check.
- Configure forms and test delivery before asking for email or feedback.
- Update the privacy notice with the form processor, retention period and public contact.
