# Where the field-guide design meets this codebase

The handoff (`Implementation Spec.dc.html`, versions 5a / 6a / 6b) was drawn
against a three-route site. This one has 24 routes, a six-filter finder, a
browse grid, client-side rendering and a light/dark theme. Everything below is
a place where the two disagree.

Part one needs a decision from the author and is the reason not to publish
yet. Part two is already resolved in code; it is recorded so the choices are
visible rather than inferred. Part three is what the next pages still need.

The homepage now carries **two walked routes and one unwalked** — Hampstead
was confirmed walked after the first build, and 1.1 records what that
changed.

Status of the work: **every page is on the new design** — the homepage, the
index, Terms used here, all 24 route pages, About, Feedback, Contact, Privacy,
Accessibility, What next?, the finder and the 404.

The single exception is `/routes/seventeen/`, the unlisted route, which the
spec lists as "existing page, stays as is". It is the only page still loading
`assets/css/styles.css`, and so the only reason Fraunces, Work Sans and the
old stylesheet remain in the build. If "stays as is" meant its content rather
than its design, say so and it takes ten minutes.

---

## 1 · Open — the author decides

### 1.1 Hampstead is walked — resolved, but three lines were written for it

Design 5a filed Hampstead as unwalked, with the absence line *"Not since last
winter, and the pub may have changed hands."* The data disagreed:
`status: field-checked` with a **verified** field note, *"Field-walked from
Hampstead Heath Overground in August 2026."* The author confirmed the walk, so
Hampstead is now `almanac.walked: true` and the design copy written on the
other premise is gone.

That made three pieces of copy necessary, all in the author's voice and all
worth checking:

1. **The editor's note**, which counted the walks. Now: *"There are three
   routes here and I have walked two of them, end to end, and those two I
   would send anybody on. The third I have put together from places I know
   separately…"* Same construction as 5a, different count.
2. **The section head**, now singular: *"One I have not walked yet, so there
   is no photograph of it."*
3. **Hampstead's Plate caption and body paragraph**, which the unwalked
   version had no need of. Both are built from the field note — August, the
   climb from the ponds to Kenwood, The Old White Bear as the best pub stop.
   **One detail is not in the data: "Late afternoon."** The field note gives
   the month but no time of day, and the design requires the caption to name
   one. Change it in `almanac.plate.caption` if the walk was at another hour.

Hampstead's FactLine was also moved onto the measured figures, since a walked
route's timings are measured rather than guessed: station *Hampstead Heath*
and *four to five hours*, from `quickFacts` (`4–5 hours`, arriving at
Hampstead Heath Overground), replacing 5a's *Hampstead* and *three to four
hours*.

Hampstead's own route page is still on the previous design and is unaffected;
it already said field-checked, so the two no longer contradict each other.

### 1.2 "There are three routes here" — there are 24

The EditorNote counts three. That is true of the homepage, which shows three,
and false of the site, which has 24 in `/routes/`. The designer knew the list
would grow (their own note on 6a says the filter exists "because the list must
grow"), but the homepage copy was written for a site of three. Unchanged by
the Hampstead correction.

### 1.3 The photographs do not exist

No assets were supplied. Both walked entries ship the design's hatched
placeholder and a label — `[ photo — towpath west of the bridge ]` and
`[ photo — the climb to Kenwood, above the ponds ]` — on the homepage, and
Putney's again on its route page. Three visible placeholders in production,
one more than before Hampstead was flipped.

Dropping in a real photograph needs no code change: set
`almanac.plate.image` on the route and the `<img>` replaces the hatch. The
hatch is the only gradient in the stylesheet and goes with it.

### 1.4 March, July, August

The colophon says *"Written in London in March"*. Putney's Plate caption says
*"Six in the evening, mid-March"* while its field note says *"A Friday in
early July"*. Hampstead's caption now says August, which its field note
supports. The handoff lists the season as an open question for the author; it
is still open, and there are now three months on one page.

### 1.5 Two vocabularies for the same thing

- **Effort.** The design allows exactly three words: flat, gentle, a proper
  walk. `almanac.effort` uses them, and `validate-routes.js` now enforces
  them — but only for the three routes that have an `almanac` block.
  `quickFacts.walkingLevel` still says `very-low`, `medium`, `urban-hike`
  across the other 21, and the finder, the browse grid and the OG images read
  that field. Acceptance criterion 3 ("only three effort words appear
  anywhere") is not met until every route is converted.
- **Status.** `walked` / `not walked` now sits alongside `field-checked` /
  `pilot` / `prototype`. The design replaced the badges with the walked split;
  the old statuses are still doing work everywhere else on the site.
  `almanac.walked` is authored by hand, not derived from `status`, which is
  what let Hampstead be filed wrongly in the first place. Worth deciding
  whether the two should be tied together as the other 21 routes are
  converted.

### 1.6 The index cannot show five facts, because thirteen routes have no toilets

The index intro is design copy and says *"The five facts on every line are the
same five you get on the route page, in the same order."* It is true of three
rows. **Thirteen London days have no toilet information anywhere in their
record**, so their line carries four facts — station, time, effort, cost — in
the same fixed order, with the fifth left out rather than invented. Acceptance
criterion 2 is not met across the index until that field exists.

The eight full days out do have toilet notes, but written as sentences
(*"Use the toilets at Chesham or Rickmansworth station; do not expect public
facilities between them."*) rather than as the short phrase the mono line
needs. Those eight need a short form, not new research.

### 1.6a Twenty-one route pages have no AbsenceMark

An unwalked route is supposed to carry, where the photograph would be, one
sentence written for that route saying why there isn't one. Three routes have
their copy; the other 21 show **no absence block at all** rather than a
templated one, because a shared sentence is the thing the handoff forbids most
bluntly — it turns honesty into a widget. The status line above still says
where the route stands ("Prototype route — not yet field-checked."), so
nothing is claimed that is not true, but the shape the design wanted is
missing until each sentence is written.

`python3 scripts/build_almanac_pages.py` prints the outstanding list every
time it runs: 21 routes, each needing `absence`, `effort`, `factLine` and
`indexNote`.

### 1.7 The index rows for 21 routes have no sentence in the author's voice

An IndexRow ends with a line that states how confident the author is, then
the link. Only Putney, Hampstead and Bloomsbury have one — the rest carry the
link alone (*"What I think it is."*). Generating those sentences from a
template is the thing the handoff forbids in the strongest terms: one shared
sentence turns honesty into a widget. So the rows are shorter until each one
is written, which at least makes the gap visible.

### 1.8 The effort word for 21 routes is derived, not authored

The filter and every index line need one of flat / gentle / a proper walk.
Three routes have `almanac.effort`; the other 21 are mapped in the builder
from the scales the data still uses — `very-low` → flat, `gentle` → gentle,
`medium` and `urban-hike` → a proper walk, and every full day out → a proper
walk, since they run 15–22 km. Mechanical and reversible, but it is an
editorial judgement about how hard a walk is, and it should be confirmed
route by route as each one gets its `almanac` block.

### 1.9 "Terms used here" now carries sixteen terms, not seven

Design 6b specifies seven — Flat, Gentle, A proper walk, Walked, Not walked,
Cost, Toilets — and replaces the page. The page it replaces defines nine
others (Old room, Easy exit, The useful version, What not to expect,
Field-checked, Pilot, Prototype, A warm finish, Slightly elsewhere) that the
22 pages still on the previous design depend on: Field-checked, Pilot and
Prototype are the status vocabulary those pages print, and Old room and A
warm finish appear in route copy.

Deleting them would have broken pages that are still live, so 6b's seven come
first, and the nine follow under the page's own former h1, *"Words this site
uses on purpose."*, with its intro intact. Drop that second group once the
status badges are gone from the site.

Two things to fix in the design copy itself:

- The intro says **"Five words do most of the work on this site"** and then
  lists seven. It ships verbatim because the copy is marked final; it is a
  one-word change.
- **Cost** is defined as "travel not included", which is why the index cannot
  give the eight full days out a cost band: their budgets are written as
  "train fare + pub lunch", and the fare is the part that moves. Selecting
  either cost word therefore drops all eight. Nothing is claimed that the
  data does not support, but the omission is invisible to a reader.

### 1.7 A data field reads as a sentence

`editorialControl.lastChecked` for Putney holds `"Personally field-checked —
July 2026"`, so the page renders *"Last checked: Personally field-checked —
July 2026."* This predates the redesign; it is more obvious now that the line
is prose rather than a caption under a badge. The field wants a date.

---

## 2 · Resolved — decisions taken, and why

### 2.1 The route page was never designed

The handoff says the route page's "frame exists in the design files; detail
not yet designed". It was built from the same components: one column, ruled
sections, `.definition` rows where there were cards and panels, the stop list
using the IndexRow geometry (34px numerals column, 22px gap), and the
five-fact FactLine in place of the quick-facts grid. No new colour, type role
or rule weight was introduced. It is the part of this work most likely to want
a proper design pass.

### 2.2 Pages are now built, not rendered in the browser

Route pages were a thin shell that `route-page.js` filled in from
`routes.json` after load. The design requires every page to be readable with
JavaScript disabled, so `scripts/build_almanac_pages.py` writes the redesigned
pages in full at build time; they load no JavaScript at all. `ALMANAC_ROUTES`
in that file lists which routes have moved, and `build_route_pages.py` imports
it and skips them, so the two generators cannot overwrite each other.

`route-page.js`, `home.js` and `app.js` are untouched and still serve the 23
pages that have not moved.

### 2.3 The site header is gone, and the footer grew

"Nothing sits above the EditorNote" removes the header, and with it the only
links to `/find-your-route/` and `/routes/`. Design 5a has no link to either —
it did not need one for three routes. Orphaning the finder and the index of a
24-route site is a functional regression, not a style change, so the Apparatus
carries all eight links the old header and footer had between them, in the
design's mono treatment: Find a route, Browse routes, Feedback, About, Terms
used here, What next?, Privacy, Accessibility. The spec names five.

Reverting to the specified five is an edit to `apparatus.links` in
`data/almanac.json` — but do it only once the index is reachable some other
way.

### 2.4 No dark theme

`DESIGN.md` locks "light, dark and reduced-motion states ship together". The
new palette has one background — paper is *"the only content background"* —
and a dark variant would need colours outside the token list. The converted
pages are light only, declare `color-scheme: light`, and do not load
`theme.js` or show the `◐` toggle (which the mapping table removes anyway, as
having no accessible name and no function). Reduced motion is moot: the only
motion in the design is a link colour change with no duration.

The rest of the site still has both themes. Someone who toggles to dark on the
browse page and then opens the homepage gets a light page.

### 2.5 Links, not buttons — including the map links

The design allows no buttons. The Google Maps controls became text links; the
destinations and behaviour are unchanged. The `↗` glyph is gone (no icons),
replaced by a visually-hidden "(opens in a new tab)", which tells screen
readers something the arrow never did.

### 2.6a The ConditionFilter needs JavaScript, and says so by not appearing

The handoff asks for the filter's state to live in the query string "so a
filtered index can be linked and works without JavaScript". On a static host
the second half is not possible: nothing on the server can read the query
string, and pre-rendering every combination of nine words is 512 pages.

So the filter block is served with `hidden` and revealed by
`assets/js/condition-filter.js`, which also reads the query string on load and
rewrites it on every choice — a filtered index is still linkable. Without
JavaScript the index itself reads in full, all 24 rows, which is what
"readable without JavaScript" is protecting. Showing a control that looks live
and does nothing would be worse than not showing it.

The filter words are `<button>` elements, not links, despite the design's
"links, not buttons" rule. That rule is about the ghost-button CTA the
redesign removed; a word that toggles rather than navigates is a button, and
being one is what lets a screen reader announce it as pressed. They carry no
button styling of any kind.

This is the site's second filtering mechanism, beside `/find-your-route/`.
Worth deciding whether the ConditionFilter replaces the six-filter finder or
sits beside it.

### 2.6b `?type=` still works, and now means something slightly different

The old browse page filtered on `?type=london-day` / `?type=day-walk`. The
design has no route-type axis, so those URLs are translated onto the duration
axis — `day-walk` becomes "most of a day". The link still lands on a sensible
filtered index, but the set is not identical: eleven routes take most of a
day, because three London days do too.

### 2.6c Every index row has a red link, so a viewport shows about eight

Criterion 4 gives each route exactly one link. Criterion 7 caps red at three
per viewport. On an index of 24 routes those cannot both hold — the design's
own 6a sits exactly at the limit with three rows.

The mock shows all three row links in red-lead, including the unwalked ones,
so that is what shipped. If the count matters more than the match, the two
obvious moves are to give unwalked rows the quiet link treatment (leaving red
to mark only the routes the author vouches for, which fits the page's logic)
or to quiet them all.

### 2.6d The pages the handoff never designed keep their markup

About, Feedback, Contact, Privacy, Accessibility, What next?, the finder and
the 404 have content and no design. Rather than retype two long forms and a
six-filter finder — and risk the JavaScript that drives them — the build lifts
each page's `<main>` unchanged into the new shell and restyles the old class
names in `almanac.css`. `finder.js` and `forms.js` are untouched, and the
build is idempotent because it re-reads the same `<main>` each run.

What that restyling does:

- **Chips become the index filter's selectable words.** The finder's radio
  chips and the index's ConditionFilter now read as one idea: a chosen word
  in red-lead with a red rule under it, an unchosen one in ink with a grey
  rule. The scoring in `finder.js` is unchanged.
- **Result cards become index rows.** The card's fact chips are set as one
  mono line with numerals separators, and its "London day · Best match" label
  is set as meta rather than as an Eyebrow, so the page still has exactly one.
- **The three "possible collections" on What next?** become ruled rows.
  Their headings were `<h3>` under no `<h2>`; they are now `<h2>`, which is
  the only markup change made to any of these pages.
- **Buttons.** A link dressed as a button is a link again. A form's submit
  stays a control — a form needs one — drawn as a single 1px ink rule with no
  fill and no radius. This is the one place "no buttons anywhere" cannot hold.

### 2.6e The 404 is generated, and styled only on the deployed site

Its assets and links are absolute from the site root, so the page works at
whatever depth the missing URL had — a deliberate earlier fix, preserved. On
a local preview served at `/`, that prefix resolves to nothing and the 404
renders unstyled. That was true before this work; it is correct on Pages.

It is also the one page among the undesigned ones whose markup is generated
rather than lifted. A lifted `<main>` is build output as well as source, so
an absolute link inside one would quietly pin the deploy path into a file the
build only copies. Every address on the 404 now comes from `BASE_PATH` in
`data/site.json`, and `legacy_page()` refuses to convert any page whose
`<main>` contains an absolute in-site link.

### 2.6f Disabled form fields sit under 4.5:1

The feedback, contact and What next? forms are disabled because no endpoint
is configured, and a disabled `<select>`'s option text lands at about 3.5:1.
WCAG exempts inactive controls from contrast, and the state is the existing
"collection is closed" behaviour, so it was left alone — worth knowing it
will resolve itself when the endpoints are connected.

### 2.6 Three red elements per viewport, on a page with fifteen links

Acceptance criterion 7 caps red-lead at three per viewport. A route page has
about fifteen links, most of them map links on individual stops. Two link
treatments were introduced rather than break the criterion: editorial links
stay red-lead, and repeated utility links take the quiet treatment the design
already uses for the apparatus and the "Terms used here" link — ink-secondary
with a rule-minor underline, moving to ink on hover.

### 2.7 The homepage has a hidden `<h1>`

The design starts the page with a paragraph and allows nothing above it, which
would leave the homepage without a level-one heading. It carries
`<h1 class="visually-hidden">London, Slightly Elsewhere</h1>` — nothing
visible sits above the editor's note, and the heading order is h1 → h2 (the
walked route, the section head) → h3 (the unwalked routes). Titles, meta
descriptions and JSON-LD are byte-for-byte what they were.

### 2.8 What "66ch" means

The spec gives the body measure as 66ch, but `ch` resolves against each
element's own font size, so the same rule produces 598px for 16px text and
640px for 17.5px text. The design files evaluate it at 16px. The measure
tokens are therefore pixel values taken from the design files — 667 / 635 /
586 / 598 / 562 — and every column on the built pages matches the mock
exactly. Below 768px they all exceed the viewport, so the measure falls back
to the page padding, which is what the responsive table asks for.

Note that 598px of Newsreader at 17.5px is about 89 characters, not 66.
`DESIGN.md` asks for a 60–75 character measure. The approved design wins on
these two pages; it is worth knowing the two rules disagree.

### 2.9 Small corrections to the spec's own numbers

- **Tap targets.** The spec says 10px of vertical padding on a mobile
  TextLink. An inline box is only about 1.15em tall, so 10px lands at 37–39px,
  under the 44px the same document requires. Links get 14px; the 11px mono
  apparatus links are too small for padding alone and become `inline-flex`
  with `min-height: 44px`.
- **Fact values.** Criterion 11 forbids a line break inside a fact value, so
  `.factline b` is `white-space: nowrap`. `validate-routes.js` caps each value
  at 28 characters, since a longer one would push the column sideways at
  375px.
- **Spacing.** The mocks use 9, 10, 18, 30 and 40px, none of which are on the
  spacing scale the same handoff defines. The implementation uses the scale.
  Type sizes, line heights, colours, rule weights and copy are exact.
- **The Plate frame** carries no padding, so the photograph itself is 2:1
  (3:2 below 768px) inside the 1px rule. In the mock the padding is inside the
  ratio, which would inset a real photograph.

### 2.10 Copy that was moved rather than rewritten

Apart from the three lines the Hampstead correction required (1.1), nothing
was reworded. Where the design deletes a component, its text went somewhere:

- The hero's five elements → the EditorNote (design mapping table).
- Quick-facts grid, duration chip, metadata rail → the FactLine.
- Status badges → the status sentence and the AbsenceMark.
- The route page's uppercase eyebrow labels → removed where they only
  announced the heading beneath them; promoted to the section head where they
  carried meaning of their own ("Finish and easy exit.", "Choose the shape of
  the day.").
- The sidebar's `bestTime` → a "Best time" row under "Notes before you go."
  ("Best time" is the only label written for this build.)
- The footer's *"Walked by a person. Wrong by the time you read it…"* → the
  route page's corrections band.
- Four links to the feedback form became two. The sidebar and the route
  utility bar that held the other two no longer exist.

The three headings that had no terminal full stop now have one, per the
design's sentence-case rule. One heading still does not: *"New Moon nights can
be a cheaper way in"*, which is a title in `data/venue-timing.json` and is the
author's copy to change.

### 2.11 Two stylesheets, on purpose

`almanac-tokens.css` (colour, type, spacing, measure, rules, self-hosted
Newsreader and IBM Plex Mono) and `almanac.css` (components) are loaded only
by the converted pages. The rest of the site keeps `styles.css` with Fraunces
and Work Sans. The two are never loaded together. This is what lets the
migration happen a page at a time; it also means the site carries four font
files and two type systems until it is finished.

---

## 3 · What is left

Every page is converted. What remains is copy and one asset job, not layout.

- **Copy for 21 routes.** Each needs an `almanac` block: an effort word from
  the three, a FactLine sentence with its five values, a link name that
  states how confident the author is, an index line, and an absence sentence
  written for that route. The build prints the list; the validator refuses a
  repeated absence sentence, which is the point. Until then those routes run
  on derived facts (1.6–1.8, 1.6a).
- **Toilet information for thirteen London days**, and a short form of the
  eight full-day toilet notes.
- **Photographs.** Three hatched placeholders are live (1.3).
- **OG images.** `generate_og_images.py` still draws the old palette and
  fonts, so link previews look like the previous design.
- **`/routes/seventeen/`**, left on the old design per the spec — the only
  thing keeping `styles.css`, Fraunces and Work Sans in the build.
- **The two filters.** The ConditionFilter on the index and the six-filter
  finder now look like one system but are still two mechanisms. Deciding
  whether the finder retires would remove `finder.js` and a page.
- `node scripts/validate-routes.js` could not be run while this was written —
  there is no Node on the machine it was built on. The new `almanac` rules
  were checked against the data by hand; run the validator before merging.
