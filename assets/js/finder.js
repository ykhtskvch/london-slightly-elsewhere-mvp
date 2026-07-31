const cityOrders = { walking: ["very-low", "gentle", "medium", "urban-hike"], noise: ["quiet", "moderate", "lively", "loud"], budget: ["free-ish", "under-30", "30-70", "splurge"] };
const labels = { routeType: { "london-day": "London day", "day-walk": "Full day out" }, distance: { "15-18": "15–18 km", "18-22": "18–22 km", "22-25": "22–25 km" }, travelTime: { "under-60": "Up to 60 minutes", "60-90": "60–90 minutes" }, departureHub: { marylebone: "Marylebone", paddington: "Paddington", euston: "Euston", "kings-cross-st-pancras": "King’s Cross St Pancras", "liverpool-street": "Liverpool Street", "london-bridge": "London Bridge", victoria: "Victoria", waterloo: "Waterloo", "metropolitan-line": "Metropolitan line", other: "Somewhere else" }, difficulty: { easy: "Easy terrain", moderate: "Moderate", challenging: "Challenging" }, routeShape: { circular: "Circular", "point-to-point": "Station to station", either: "Either" }, pub: { "pub-mid-route": "Pub during the walk", "pub-finish": "Pub near the finish", "multiple-options": "More than one food stop", cafe: "Café or bakery", "bring-food": "Bring food" }, shortenable: { true: "Shorter fallback", false: "No shortening needed" } };

document.addEventListener("DOMContentLoaded", async () => {
  const form = document.querySelector("[data-finder-form]");
  const target = document.querySelector("[data-results]");
  const meta = document.querySelector("[data-results-meta]");
  if (!form || !target || !meta) return;
  let routes;
  try { routes = await window.routeApp.loadRoutes(); } catch { target.innerHTML = '<p class="empty-state">Route data could not load. Please try the deployed site or a local server.</p>'; return; }
  const syncPanels = () => {
    const type = new FormData(form).get("routeType");
    form.dataset.routeType = type || "";
    form.querySelectorAll("[data-route-filter-panel]").forEach(panel => {
      const active = Boolean(type) && panel.dataset.routeFilterPanel === type;
      panel.hidden = !active;
      panel.setAttribute("aria-hidden", String(!active));
      panel.querySelectorAll("input").forEach(input => { input.disabled = !active; });
    });
  };
  syncPanels();
  render(routes, {}, target, meta);
  form.addEventListener("change", event => { if (event.target.name === "routeType") syncPanels(); });
  form.addEventListener("submit", event => { event.preventDefault(); render(routes, preferences(form), target, meta); });
  form.addEventListener("reset", () => window.setTimeout(() => { syncPanels(); render(routes, {}, target, meta); }, 0));
});

function preferences(form) { return Object.fromEntries(new FormData(form).entries()); }

function render(routes, prefs, target, meta) {
  const hasPreferences = Object.keys(prefs).length > 0;
  const routeSet = prefs.routeType ? routes.filter(route => route.routeType === prefs.routeType) : routes;
  const scored = routeSet.map(route => ({ route, ...scoreRoute(route, prefs) })).sort((a, b) => b.score - a.score);
  const results = hasPreferences ? scored.slice(0, 3) : scored;
  if (!results.length) { meta.textContent = "No routes of that kind are available yet."; target.innerHTML = '<p class="empty-state">The full-day finder is ready; carefully checked routes will appear here once they exist.</p>'; return; }
  if (!hasPreferences) meta.textContent = `Browse ${routes.length} routes, or choose the kind of day to make the choice more specific.`;
  else {
    const missed = results[0].criteria.filter(item => item.status === "miss");
    meta.textContent = missed.length ? `Closest match: ${results[0].route.title}. It misses on ${list(missed.map(item => item.label))}.` : `${count(results.length)}, ranked for the shape of day you picked.`;
  }
  target.innerHTML = results.map((item, index) => resultCard(item, index, hasPreferences)).join("");
}

function scoreRoute(route, prefs) { return route.routeType === "day-walk" ? scoreDayWalk(route, prefs) : scoreLondonDay(route, prefs); }

function scoreLondonDay(route, prefs) {
  let score = 50; const criteria = []; const f = route.filters;
  if (prefs.occasion) score += occasionCriterion(f.occasion, prefs.occasion, criteria);
  if (prefs.groupSize) score += includesCriterion(f.groupSize, prefs.groupSize, 10, -12, criteria, "groupSize");
  for (const [key, penalty] of [["walking", -16], ["noise", -14], ["budget", -16]]) score += ordinalCriterion(prefs[key], f[key], cityOrders[key], 10, penalty, criteria, key);
  if (prefs.weather) score += includesCriterion(f.weather, prefs.weather, 12, -13, criteria, "weather");
  if (prefs.occasion === "first-date") { if (f.easyExit === "must-have") score += 12; if (f.booking === "booking-required" || f.noise === "loud") score -= 10; }
  return { score, criteria };
}

function scoreDayWalk(route, prefs) {
  let score = 50; const criteria = []; const f = route.filters;
  for (const [key, weight] of [["distance", 24], ["travelTime", 22], ["departureHub", 20], ["difficulty", 20], ["landscape", 14], ["urbanPresence", 10], ["views", 10], ["pub", 10], ["routeShape", 6], ["journeyComplexity", 8]]) {
    if (!prefs[key]) continue;
    const actual = key === "departureHub" ? f.departureHubs : key === "pub" ? f.pub : f[key];
    score += includesCriterion(Array.isArray(actual) ? actual : [actual], prefs[key], weight, -Math.round(weight * .65), criteria, key);
  }
  if (prefs.shortenable === "true") score += includesCriterion([String(f.shortenable)], "true", 12, -10, criteria, "shortenable");
  return { score, criteria };
}

function includesCriterion(values, selected, match, miss, criteria, key) { const matched = values.includes(selected); criteria.push({ label: label(key, selected), status: matched ? "match" : "miss" }); return matched ? match : miss; }
function occasionCriterion(values, selected, criteria) { const matched = values.includes(selected); const close = !matched && values.some(value => isRelatedOccasion(value, selected)); const status = matched ? "match" : close ? "close" : "miss"; criteria.push({ label: label("occasion", selected), status }); return matched ? 25 : close ? 10 : -10; }
function isRelatedOccasion(actual, selected) { return [["first-date", "second-date"], ["friend-catch-up", "solo-day"], ["rainy-day", "neighbourhood-escape"]].some(group => group.includes(actual) && group.includes(selected)); }
function ordinalCriterion(selected, actual, order, match, miss, criteria, key) { if (!selected) return 0; const distance = Math.abs(order.indexOf(selected) - order.indexOf(actual)); const status = distance === 0 ? "match" : distance === 1 ? "close" : "miss"; criteria.push({ label: label(key, selected), status }); return status === "match" ? match : status === "close" ? 2 : miss; }
function label(key, value) { return labels[key]?.[value] || window.routeApp.titleCase(value); }
function list(values) { return values.length === 1 ? values[0] : `${values.slice(0, -1).join(", ")} and ${values.at(-1)}`; }
function count(total) { return total === 1 ? "One route" : `${["No", "One", "Two", "Three"][total] || total} routes`; }

function resultCard(item, index, hasPreferences) {
  const { route, criteria } = item; const e = window.routeApp.escape; const missed = criteria.filter(item => item.status === "miss");
  const ranking = !hasPreferences ? "" : index === 0 ? (missed.length ? "Closest match" : "Best match") : "Worth a look";
  const matchLine = hasPreferences
    ? `<p class="match">${missed.length ? `Closest on ${list(criteria.filter(item => item.status !== "miss").map(item => item.label)) || "the overall shape"}.` : "Matches everything you picked."}</p>`
    : "";
  const type = route.routeType === "day-walk" ? "Full day out" : "London day";
  const facts = route.routeType === "day-walk" ? [`${route.hike.distanceKm} km`, `About ${route.travel.typicalMinutes} min from ${label("departureHub", route.travel.departureHubs[0])}`, label("difficulty", route.hike.difficulty), route.hike.landscape.slice(0, 2).map(value => label("landscape", value)).join(" + "), label("pub", route.hike.pubOptions[0])] : [route.quickFacts.duration, `${route.quickFacts.walkingLevel} walk`, route.quickFacts.noiseLevel, route.quickFacts.budget, `Start: ${route.quickFacts.startStation}`];
  const soundtrack = route.soundtrack ? `<p class="soundtrack">This day sounds like: ${e(route.soundtrack.artist)} — <em>${e(route.soundtrack.track)}</em></p>` : "";
  return `<article class="result-card route-${e(route.slug)}"><div class="result-heading"><div><p class="eyebrow">${e(type)}${ranking ? ` · ${ranking}` : ""}</p><h2>${e(route.title)}</h2></div><span class="result-kicker">${e(window.routeApp.statusLabel(route.status))}</span></div><p>${e(route.subtitle)}</p>${soundtrack}${matchLine}<div class="facts">${facts.map(fact => `<span class="fact">${e(fact)}</span>`).join("")}</div><p class="caveat">${e(route.editorial.whatNotToExpect)}</p><p><a class="button soft" href="${window.routeApp.routeHref(route)}">See the route</a></p></article>`;
}
