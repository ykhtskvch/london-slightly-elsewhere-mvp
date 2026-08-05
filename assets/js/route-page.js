document.addEventListener("DOMContentLoaded", async () => {
  const id = document.body.dataset.routeId;
  const target = document.querySelector("[data-route-page]");
  if (!id || !target) return;

  try {
    const [routes, venueTiming] = await Promise.all([
      window.routeApp.loadRoutes(),
      window.routeApp.loadVenueTiming()
    ]);
    const storedRoute = routes.find(item => item.id === id);
    const route = storedRoute && {
      ...storedRoute,
      valueTiming: storedRoute.valueTimingVenueId ? venueTiming[storedRoute.valueTimingVenueId] : null
    };
    if (!route) throw new Error("Route not found");
    document.title = `${route.seo?.shortTitle || route.title} | London, Slightly Elsewhere`;
    renderRoute(route, target);
  } catch (error) {
    target.innerHTML = "<section class=\"page-intro\"><p>Route data could not be loaded. Please use a static server or deploy the site.</p></section>";
  }
});

function formatHub(hub) {
  const names = {
    "kings-cross-st-pancras": "King’s Cross St Pancras",
    "liverpool-street": "Liverpool Street",
    stratford: "Stratford",
    "london-bridge": "London Bridge",
    "metropolitan-line": "Metropolitan line",
    other: "Another London departure point"
  };
  return names[hub] || hub.replaceAll("-", " ").replace(/\b\w/g, letter => letter.toUpperCase());
}

function renderRoute(route, target) {
  const e = window.routeApp.escape;
  const navigation = route.navigation;
  const mapStart = navigation?.arrival?.mapOriginQuery || navigation?.arrival?.station;
  const isDayWalk = route.routeType === "day-walk";
  const status = route.status === "published"
    ? { label: "Published route", detail: "Self-guided route" }
    : route.status === "field-checked"
      ? { label: "Field-checked route", detail: "Personally field-checked route — live details can still change" }
      : route.status === "prototype"
        ? { label: "Prototype route", detail: "Prototype route — not yet field-checked" }
        : { label: "Pilot route", detail: "Pilot route — walked once; verify live details before going" };
  const facts = isDayWalk ? [
    ["Start", route.travel.arrivalStation],
    ["Finish", route.travel.returnStation],
    ["Distance", `${route.hike.distanceKm} km`],
    ["Walking time", route.hike.walkingTime || route.quickFacts.duration],
    ["Difficulty", route.hike.difficulty],
    ["Route shape", route.hike.routeShape === "point-to-point" ? "Station to station" : route.hike.routeShape],
    ["Travel from London", `About ${route.travel.typicalMinutes} min`],
    ["Shorter fallback", route.hike.shortenable ? "Available" : "Not planned"]
  ] : [
    ["Start", route.quickFacts.startStation],
    ["Time", route.quickFacts.duration],
    ...(route.quickFacts.startBy ? [["Start by", route.quickFacts.startBy]] : []),
    ["Walk", route.quickFacts.walkingLevel],
    ["Budget", route.quickFacts.budget],
    ["Easy exit", route.filters.easyExit === "must-have" ? "Built in" : "Possible"]
  ];
  const list = values => values.map(value => `<li>${e(value)}</li>`).join("");
  const stops = route.stops.map((stop, index) => {
    const previousQuery = index === 0
      ? mapStart
      : route.stops[index - 1].mapQuery;
    const walkingUrl = stop.mapQuery && previousQuery
      ? mapsDirections(previousQuery, stop.mapQuery)
      : stop.mapQuery ? mapsSearch(stop.mapQuery) : null;
    return `
    <li>
      <h3>${e(stop.name)}</h3>
      <span class="stop-meta">${e(stop.type)} · ${e(stop.duration)}${stop.walkingToNext ? ` · ${e(stop.walkingToNext)} to next` : ""}</span>
      ${stop.locationNote ? `<p class="location-note">${e(stop.locationNote)}</p>` : ""}
      ${stop.directionFromPrevious ? `<p class="direction-note"><strong>From the previous point:</strong> ${e(stop.directionFromPrevious)}</p>` : ""}
      <p>${e(stop.description)}</p>
      <div class="stop-links">
        ${walkingUrl ? `<a href="${e(walkingUrl)}" rel="noopener" target="_blank">${index === 0 ? "Walk here from the station" : "Walk from the previous stop"} ↗</a>` : ""}
        ${stop.mapQuery ? `<a href="${e(mapsSearch(stop.mapQuery))}" rel="noopener" target="_blank">Open this point ↗</a>` : ""}
        ${stop.officialUrl ? `<a href="${e(stop.officialUrl)}" rel="noopener" target="_blank">Official information ↗</a>` : ""}
      </div>
    </li>`;
  }).join("");
  const versions = route.versions.map(version => `
    <article class="version-card">
      <h3>${e(version.label)}</h3>
      <p>${e(version.description)}</p>
      <p class="fine-print">${e(version.duration)} · ${e(version.budget)}${version.requiresTicketCheck ? " · ticket check required" : ""}</p>
    </article>`).join("");
  const warnings = list(route.editorial.practicalWarnings);
  const lastChecked = route.editorialControl.lastChecked || "Not yet field-checked";
  const flowLabels = {
    start: "start",
    walk: "walk",
    pub: "pub",
    "live-music": "optional gig",
    bookshop: "bookshop",
    museum: "indoor stop",
    "cafe-or-pub": "warm finish",
    garden: "free gardens",
    view: "view"
  };
  const routeFlow = route.stops.map(stop => flowLabels[stop.type] || stop.type).map(label => `<span>${e(label)}</span>`).join("");
  const mappedStops = route.stops.filter(stop => stop.mapQuery);
  // Google's dir/?api=1 URL scheme accepts up to ~9 waypoints in addition to
  // the destination. Shown on every route, prototype included: the pins
  // themselves are real, and navigation.disclaimer already says how far to
  // trust the sequence for routes that have not been field-checked.
  const wholeRouteUrl = !isDayWalk && navigation?.arrival?.station && mappedStops.length > 0 && mappedStops.length <= 10
    ? mapsRoute(mappedStops)
    : null;
  const navigationBlock = navigation ? `
    <section class="navigation-start" aria-labelledby="start-here-title">
      <div class="navigation-heading">
        <div>
          <p class="eyebrow">${navigation.detailLevel === "anchor-by-anchor" ? "Navigation ready" : "Start pin only"}</p>
          <h2 id="start-here-title">Start without guessing.</h2>
        </div>
        <span class="navigation-level">${navigation.detailLevel === "anchor-by-anchor" ? "Anchor by anchor" : "Prototype"}</span>
      </div>
      <div class="navigation-grid">
        <div><span>Suggested arrival</span><strong>${e(navigation.arrival.station)}</strong><p>${e(navigation.arrival.stationExit)}</p></div>
        <div><span>Set your first pin</span><strong>${e(navigation.arrival.pinLabel)}</strong><p>${e(navigation.arrival.pinQuery)}</p></div>
        <div><span>Once you arrive</span><strong>One useful instruction</strong><p>${e(navigation.arrival.firstMove)}</p></div>
      </div>
      <div class="button-row">
        <a class="button primary" href="${e(mapsDirections(null, navigation.arrival.pinQuery, "transit"))}" rel="noopener" target="_blank">Start in Google Maps ↗</a>
        ${wholeRouteUrl ? `<a class="button soft" href="${e(wholeRouteUrl)}" rel="noopener" target="_blank">Open the whole walk ↗</a>` : ""}
        ${navigation.externalRouteUrl ? `<a class="button soft" href="${e(navigation.externalRouteUrl)}" rel="noopener" target="_blank">Open detailed route ↗</a>` : ""}
        ${navigation.gpxUrl ? `<a class="button soft" href="${e(navigation.gpxUrl)}" rel="noopener" target="_blank">Download GPX ↗</a>` : ""}
      </div>
      <p class="navigation-disclaimer">${e(navigation.disclaimer)}</p>
      <p class="arrival-privacy">We never request your location. Google Maps can use it privately, if you have already given Maps permission.</p>
    </section>` : "";
  const finishBlock = navigation ? `
    <section class="route-finish">
      <p class="eyebrow">${isDayWalk ? "Finish and practical return" : "Finish and easy exit"}</p>
      <h2>${e(navigation.finish.label)}</h2>
      <p><strong>Nearest practical station:</strong> ${e(navigation.finish.nearestStation)}</p>
      <p>${e(navigation.finish.exitNote)}</p>
      ${isDayWalk && route.hike.earlyExit ? `<p><strong>Earlier exit:</strong> ${e(route.hike.earlyExit.label)}${route.hike.earlyExit.note ? ` — ${e(route.hike.earlyExit.note)}` : ""}</p>` : ""}
      <p><a class="button soft" href="${e(mapsSearch(navigation.finish.nearestStation))}" rel="noopener" target="_blank">Open exit station ↗</a></p>
    </section>` : "";
  const feedbackUrl = `${window.routeApp.basePath}feedback/?route=${encodeURIComponent(route.title)}`;
  const community = route.community || {};
  const communityCount = Number(community.reportCount || 0);
  const communityNeedsReview = community.status === "needs-review";
  const communityTitle = communityNeedsReview
    ? "A walker flagged something worth checking."
    : communityCount
      ? `${communityCount} ${communityCount === 1 ? "walker has" : "walkers have"} reported this route.`
      : "No community walks reported yet.";
  const communityDetail = communityNeedsReview
    ? "Treat route details as provisional until the issue has been reviewed."
    : communityCount
      ? `Most recent report: ${community.lastReported || "date not yet recorded"}. Community reports are reviewed; they do not change the Field-checked label.`
      : "Walked it? A concise field note helps keep the route current. Community reports never change the Field-checked label automatically.";
  const communityBlock = `
    <section class="community-signal${communityNeedsReview ? " needs-review" : ""}">
      <p class="eyebrow">Community signal</p>
      <h2>${e(communityTitle)}</h2>
      <p>${e(communityDetail)}</p>
      <p><a class="button soft" href="${e(feedbackUrl)}">Share a field note</a></p>
    </section>`;
  const soundtrackBlock = route.soundtrack ? `<p class="soundtrack">This day sounds like: ${e(route.soundtrack.artist)} — <em>${e(route.soundtrack.track)}</em></p>` : "";
  const travelBlock = isDayWalk ? `
    <section class="travel-details">
      <p class="eyebrow">Getting there from London</p><h2>Start with the train, not a car.</h2>
      <dl class="travel-facts"><div><dt>Leave from</dt><dd>${e(route.travel.departureHubs.map(formatHub).join(" / "))}</dd></div><div><dt>Typical journey</dt><dd>About ${e(route.travel.typicalMinutes)} min · ${e(route.travel.journeyComplexity === "one-change" ? "one change" : "direct")}</dd></div><div><dt>Arrive at</dt><dd>${e(route.travel.arrivalStation)}</dd></div><div><dt>Return from</dt><dd>${e(route.travel.returnStation)}</dd></div><div><dt>Mode</dt><dd>${e(route.travel.transportMode.replaceAll("-", " and "))}</dd></div></dl>
      <p class="fine-print">${e(route.travel.serviceNote)}</p>${route.travel.officialSourceUrl ? `<p><a class="button soft" href="${e(route.travel.officialSourceUrl)}" rel="noopener" target="_blank">Check operator information ↗</a></p>` : ""}
    </section>` : "";
  const terrainEntries = isDayWalk ? [["Terrain", route.hike.terrainNotes], ["Mud and drainage", route.hike.conditions?.mudOrDrainage], ["Exposed sections", route.hike.conditions?.exposedSections], ["Road sections", route.hike.conditions?.roadSections], ["Stiles", route.hike.conditions?.stiles], ["Food and water", route.hike.conditions?.foodWater], ["Toilets", route.hike.conditions?.toilets], ["Mobile signal", route.hike.conditions?.mobileSignal], ["Pub timing", route.hike.conditions?.pubTiming], ["Shortening", route.hike.shorteningNote], ["Elevation", route.hike.elevationGainM == null ? null : `${route.hike.elevationGainM} m gain`]].filter(([, value]) => value) : [];
  const terrainBlock = terrainEntries.length ? `<section><p class="eyebrow">Terrain and conditions</p><h2>Read this before the platform.</h2>${terrainEntries.map(([label, value]) => `<h3>${e(label)}</h3><p>${e(value)}</p>`).join("")}</section>` : "";
  const fieldNoteBlock = route.fieldNote ? `
    <aside class="field-note">
      <p class="eyebrow">Last walked${route.fieldNote.verified ? "" : '<span class="verify-flag">unverified — details not yet reconfirmed</span>'}</p>
      <p>${e(route.fieldNote.text)}</p>
    </aside>` : "";
  const valueTimingBlock = route.valueTiming ? `
    <section class="value-timing">
      <p class="eyebrow">${e(route.valueTiming.label)}</p>
      <h2>${e(route.valueTiming.title)}</h2>
      <p>${e(route.valueTiming.detail)}</p>
      <div class="value-timing-meta">
        <a href="${e(route.valueTiming.sourceUrl)}" rel="noopener" target="_blank">${e(route.valueTiming.sourceLabel)} ↗</a>
        <span>Checked ${e(route.valueTiming.checked)}</span>
      </div>
    </section>` : "";

  target.innerHTML = `
    <section class="route-hero">
      <p class="eyebrow">${status.detail}</p>
      <h1>${e(route.title)}</h1>
      <p class="route-subtitle">${e(route.subtitle)}</p>
      <dl class="quick-facts">
        ${facts.map(([label, value]) => `<div><dt>${e(label)}</dt><dd>${e(value)}</dd></div>`).join("")}
      </dl>
      <div class="route-at-glance" aria-label="Route at a glance">${routeFlow}</div>
      <div class="route-utility">
        <span class="pilot-badge">${status.label}</span>
        <p class="fine-print">Last checked: ${e(lastChecked)}. Verify opening hours and access before going.</p>
        <a class="button soft" href="${e(feedbackUrl)}">Did this work?</a>
      </div>
    </section>
    ${fieldNoteBlock}
    ${communityBlock}
    ${travelBlock}
    ${navigationBlock}
    <div class="route-layout">
      <div class="route-main">
        <section>
          <p class="eyebrow">Why this route exists</p>
          <h2>${e(route.editorial.vibeSummary)}</h2>
          <p>${e(route.routeNarrative)}</p>
        </section>
        <section>
          <div class="fit-panels">
            <div class="fit-panel good-fit"><h2>Best for</h2><ul>${list(route.editorial.bestFor)}</ul></div>
            <div class="fit-panel not-fit"><h2>Not ideal for</h2><ul>${list(route.editorial.notIdealFor)}</ul></div>
          </div>
        </section>
        <section>
          <p class="eyebrow">The route</p>
          <ol class="stop-list">${stops}</ol>
        </section>
        ${terrainBlock}
        ${finishBlock}
        ${valueTimingBlock}
        <section>
          <p class="eyebrow">Choose the shape of the day</p>
          <div class="version-cards">${versions}</div>
        </section>
        <section>
          <h2>Notes before you go</h2>
          <h3>Date notes</h3><p>${e(route.copy.dateNotes)}</p>
          <h3>Friends</h3><p>${e(route.copy.friendGroupNotes)}</p>
          <h3>Solo</h3><p>${e(route.copy.soloNotes)}</p>
          <h3>Food and drink</h3><p>${e(route.copy.foodDrinkNotes)}</p>
        </section>
        <section>
          <h2>When the plan changes</h2>
          <h3>If it rains</h3><p>${e(route.copy.rainyDayBackup)}</p>
          <h3>If it goes well</h3><p>${e(route.copy.continueIfGoingWell)}</p>
          <h3>If you want to leave early</h3><p>${e(route.copy.exitEarly)}</p>
        </section>
        <section>
          <h2>What not to expect</h2>
          <p class="warning">${e(route.editorial.whatNotToExpect)}</p>
          <h3>Practical warnings</h3><ul>${warnings}</ul>
        </section>
        <section>
          <p class="eyebrow">Final editorial note</p>
          <h2>${e(route.copy.finalEditorialNote)}</h2>
          ${soundtrackBlock}
        </section>
      </div>
      <aside class="route-sidebar">
        <h2>Before you go</h2>
        <p><strong>${e(route.quickFacts.bestTime)}</strong></p>
        <p class="fine-print">${e(route.editorial.whatNotToExpect)}</p>
        <p><a class="button soft" href="${e(feedbackUrl)}">Give feedback</a></p>
      </aside>
    </div>
    <section class="route-feedback">
      <p class="eyebrow">Walked this route?</p>
      <h2>Two things help most.</h2>
      <p>What was closed, and where you bailed — more useful than a compliment.</p>
      <p><a class="button primary" href="${e(feedbackUrl)}">Give feedback on this route</a></p>
    </section>`;
}

function mapsSearch(query) {
  const params = new URLSearchParams({ api: "1", query });
  return `https://www.google.com/maps/search/?${params.toString()}`;
}

function mapsDirections(origin, destination, travelmode = "walking") {
  const params = new URLSearchParams({ api: "1", destination, travelmode });
  if (origin) params.set("origin", origin);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

function mapsRoute(stops) {
  const origin = stops[0].mapQuery;
  const destination = stops[stops.length - 1].mapQuery;
  const params = new URLSearchParams({ api: "1", origin, destination, travelmode: "walking" });
  const waypoints = stops.slice(1, -1).map(stop => stop.mapQuery).slice(0, 9);
  if (waypoints.length) params.set("waypoints", waypoints.join("|"));
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}
