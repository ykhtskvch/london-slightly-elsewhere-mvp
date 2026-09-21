# Slightly Elsewhere — product design system

Status: authoritative from 21/09/2026. This replaces the earlier field-guide
direction recorded in `DESIGN-CONFLICTS.md`.

## Product direction

Slightly Elsewhere is a modern walk-discovery product with an editorial voice.
It should help somebody choose a viable day out quickly, then reward closer
reading. It is not an old almanac, a long-form magazine homepage, or a copy of
AllTrails.

The primary flow is:

`Home → Find a walk / Walks → Walk → Start in Google Maps`

Use **walk** in interface copy. `route` remains an internal data and URL term.

## Foundation

The implementation source of truth is `assets/css/almanac-tokens.css`.

- Display/headings: Fraunces, kept to medium weights so its warmth and slight
  eccentricity do not turn into a retro or artisan style.
- UI/body: Work Sans.
- Canvas `#f3efe6`, surface `#fffdf8`, ink `#17251f`, text `#263a31`,
  muted `#5d6c64`, border `#c9d1ca`.
- The only saturated accent is forest teal `#176b5b`; hover is `#0d5044` and
  the pale supporting tint is `#e3f0ea`.
- Spacing follows a 4px scale. Do not introduce one-off margins or padding.
- Radius roles are 8, 14, 20 and 28px. Cards and filters use the same border,
  radius and shadow families.
- Body copy is 16px or larger. Touch targets are at least 44×44px.
- Focus is always visible. Secondary text and control boundaries must meet
  WCAG 2.2 AA contrast requirements.

## Type roles

- Hero: fluid 42–82px Fraunces, medium weight.
- Page H1: fluid 32–44px Fraunces.
- Section H2: fluid 26–32px Fraunces.
- Card H3: 22px Fraunces.
- Body: 16px Work Sans, 1.62 line-height.
- UI/meta: 12–14px Work Sans with concise labels.
- Buttons: 16px Work Sans, semibold.

There are no mono UI labels and no third font family.

## Navigation

Primary navigation is always **Walks · About · Find a walk**. Find a walk is
the CTA. On small screens it remains directly available while Walks and About
sit inside a native disclosure menu. Feedback, Terms, Privacy and Accessibility
belong in the footer.

## Route card

`route_card()` in `scripts/build_almanac_pages.py` is the only card component.
Home, Walks, Find a walk and Related walks must all use it.

Information order:

1. Place or start-to-finish name.
2. One-sentence character of the walk.
3. Distance and duration.
4. Start → finish.
5. Up to three controlled mood tags.
6. Photograph or the honest non-photographic fallback.

Only real route photographs may be used. A missing image is not replaced with
stock or an invented scene. Every photo uses the same crop and carries useful
alt text; the fallback is decorative and hidden from assistive technology.

## Page hierarchy

### Home

The first viewport contains the value proposition and two actions. It is
followed by three weekend cards, six mood entry points, then a short trust
explanation. Long manifesto copy belongs on About.

### Walks

Use a short header, the London / Outside London switch and the shared card
grid. Every card remains in the HTML when JavaScript is unavailable.

### Find a walk

Ask only time, mood and location in the primary tool. Return no more than
three suggestions. If no exact result exists, say so and show the closest
walks. Filter state lives in the URL. Three initial suggestions remain useful
without JavaScript.

### Walk page

Before editorial text, show title, atmospheric descriptor, distance, time,
effort, start, finish and the primary **Start in Google Maps** action. Follow
with Walk essentials and Good to know, then the story, stops and secondary
detail. End with three related walks.

## Content and trust

- British English throughout.
- UI copy is short and functional; editorial copy may be atmospheric.
- Field-checked and prototype status must never be blurred.
- Do not invent timings, terrain, photographs, continuous map routes, reviews
  or commercial relationships.
- A full-day walk must state travel, terrain and practical exits.
- Long practical material may use native `<details>`; decision information
  must not be collapsed.

## Interaction, privacy and analytics

- Core browse and walk content works without JavaScript.
- Motion is subtle and respects `prefers-reduced-motion`.
- No component may create horizontal overflow at 375px, 393px, 800px or
  1440px.
- GoatCounter tracks Maps starts, finder use/result selection and successful
  route-feedback submissions. Events contain identifiers/categories, not free
  text.
- Owner QA begins at `?internal=1`; that marker propagates through same-origin
  links and excludes the session without browser storage.

## Release check

Rebuild, validate data and links, then test keyboard navigation and the four
target widths. Verify Home → Find a walk → Walk → Google Maps and Home → Walks
→ Walk. Do not reopen the visual direction after release without user evidence,
analytics or a clear usability defect.
