# Design decisions — London, Slightly Elsewhere

This file applies the Anti-Slop Design Brief to this project. Future pages and components should follow it.

## Which design a page is on

**Every page is on the field-guide design**, except `/routes/seventeen/` —
the unlisted route, which the handoff says stays as it is.

- Field-guide design: `assets/css/almanac-tokens.css` +
  `assets/css/almanac.css`, Newsreader and IBM Plex Mono, one column. Built by
  `scripts/build_almanac_pages.py`. Every page reads in full without
  JavaScript; `condition-filter.js` enhances the index, and `finder.js` and
  `forms.js` drive the finder and the forms as before.
- Previous design: `assets/css/styles.css`, Fraunces and Work Sans, light and
  dark, built by `scripts/build_route_pages.py`. Now used by one page.

The two stylesheets are never loaded together. The rules below still describe
that one page and the project's editorial standards; the palette, the two type
families, the dark theme and the 60–75 character measure are superseded
everywhere else. `DESIGN-CONFLICTS.md` records where the two disagree, what
was decided and why, and what still needs the author.

## Project decisions

- **Subject and audience:** an independent route guide for London residents aged roughly 25–45 who want a date, catch-up, local escape or occasional full day out with more character and less planning theatre.
- **The page's single job:** help a visitor choose one viable route — a London day or a longer day walk — and understand how to adapt or leave it without awkwardness.
- **Aesthetic direction:** **London field notebook** — rain-washed paper, pub-sign enamel, river-map blue, marginal notes and practical route annotations. Editorial, but not broadsheet; warm, but not artisan-café beige.
- **Signature element:** a route line with decision nodes. It appears once in the hero and returns functionally as the stop sequence on route pages.
- **One deliberate risk:** one slightly displaced, rotated margin note in the homepage hero. Everything else stays aligned and quiet.

## Locked rules

- British English throughout.
- Six-colour token palette only; no gradients.
- Fraunces is the display face; Work Sans is the body face. Both are self-hosted variable fonts (latin subset only, no third-party font requests). No extra families.
- Body copy is at least 16px with a 60–75 character measure.
- Spacing uses 4px half-steps and 8px full steps.
- Cards use background shift and named elevation before borders.
- Touch targets are at least 44px.
- Light, dark and reduced-motion states ship together.
- Key content must still make sense before JavaScript loads.
- The site uses no analytics or non-essential cookies during the pilot.
- Do not publish company, address, review or accreditation claims until they are real and verified.

## Copy tests

- One calm opinion per page.
- No hype, fake empathy or generic discovery language.
- Controls describe their outcome.
- Every caveat says who or what the route is not for.
- Dates use DD/MM/YYYY; distances use km, except miles or pints where natural.
- Route cards always state their type and show the facts that matter for it. A soundtrack, when present, sits beneath the subtitle and is clearly editorial.
- A full-day walk must show travel from London, terrain and useful route logistics; it is never published as an invented route line or GPX.

## Pre-publish check

1. Can the page be recognised without the logo?
2. Is the route line doing real navigational work?
3. Does the key flow work at 360px, keyboard-only, 200% zoom and without animation?
4. Is every public form connected, specific about errors and covered by the privacy notice?
5. Remove one decorative element before shipping.
