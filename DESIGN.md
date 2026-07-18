# Design decisions — London, Slightly Elsewhere

This file applies the Anti-Slop Design Brief to this project. Future pages and components should follow it.

## Project decisions

- **Subject and audience:** an independent route guide for London residents aged roughly 25–45 who want a date, catch-up or local escape with more character and less planning theatre.
- **The page's single job:** help a visitor choose one viable route and understand how to adapt or leave it without awkwardness.
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

## Pre-publish check

1. Can the page be recognised without the logo?
2. Is the route line doing real navigational work?
3. Does the key flow work at 360px, keyboard-only, 200% zoom and without animation?
4. Is every public form connected, specific about errors and covered by the privacy notice?
5. Remove one decorative element before shipping.
