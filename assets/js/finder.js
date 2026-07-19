const walkingOrder = ["very-low", "gentle", "medium", "urban-hike"];
const noiseOrder = ["quiet", "moderate", "lively", "loud"];
const budgetOrder = ["free-ish", "under-30", "30-70", "splurge"];

// Mirrors the exact wording shown on the filter chips in
// find-your-route/index.html, so a result card's match chips use the same
// words the reader picked rather than a re-titlecased version of the raw
// filter value.
const optionLabels = {
  occasion: {
    "first-date": "First date",
    "second-date": "Second/third date",
    "friend-catch-up": "Friends",
    "solo-day": "Solo day",
    "rainy-day": "Rainy day",
    "neighbourhood-escape": "Escape"
  },
  groupSize: { "1": "Just me", "2": "Two people", "3-4": "3–4 people" },
  walking: { "very-low": "Very low", "gentle": "Gentle", "medium": "Medium", "urban-hike": "Urban hike" },
  noise: { "quiet": "Quiet", "moderate": "Moderate", "lively": "Lively" },
  budget: { "free-ish": "Free-ish", "under-30": "Under £30", "30-70": "£30–£70" },
  weather: { "sunny": "Sunny", "rainy": "Rainy", "cold": "Cold", "evening": "Evening" }
};

document.addEventListener("DOMContentLoaded", async () => {
  const form = document.querySelector("[data-finder-form]");
  const target = document.querySelector("[data-results]");
  const meta = document.querySelector("[data-results-meta]");
  if (!form || !target || !meta) return;

  let routes = [];
  try {
    routes = await window.routeApp.loadRoutes();
    render(routes, {}, target, meta);
  } catch (error) {
    target.innerHTML = "<p class=\"empty-state\">Route data could not load. Run the site via a local server or static host.</p>";
    return;
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    render(routes, getPreferences(form), target, meta);
  });

  form.addEventListener("reset", () => {
    window.setTimeout(() => render(routes, {}, target, meta), 0);
  });
});

function getPreferences(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function render(routes, prefs, target, meta) {
  const hasPreferences = Object.keys(prefs).length > 0;
  const scored = routes.map(route => ({ route, ...scoreRoute(route, prefs) })).sort((a, b) => b.score - a.score);
  const results = hasPreferences ? scored.slice(0, 3) : scored;

  meta.classList.remove("results-meta-honest");
  if (!hasPreferences) {
    meta.textContent = "Browse sixteen routes, or use the filters to make the choice more specific.";
  } else {
    const topMissed = results[0].criteria.filter(c => c.status !== "match");
    if (!topMissed.length) {
      meta.textContent = "Three routes, ranked for the shape of day you picked.";
    } else {
      meta.textContent = `Nothing fits everything you picked. Closest is ${results[0].route.title} — it misses on: ${formatList(topMissed.map(c => c.label))}.`;
      meta.classList.add("results-meta-honest");
    }
  }
  target.innerHTML = results.map((item, index) => resultCard(item, index)).join("");
}

function scoreRoute(route, prefs) {
  let score = 50;
  const criteria = [];
  const f = route.filters;

  if (prefs.occasion) {
    const label = optionLabel("occasion", prefs.occasion);
    if (f.occasion.includes(prefs.occasion)) { score += 25; criteria.push({ key: "occasion", label, status: "match" }); }
    else if (isRelatedOccasion(f.occasion, prefs.occasion)) { score += 10; criteria.push({ key: "occasion", label, status: "close" }); }
    else { score -= 10; criteria.push({ key: "occasion", label, status: "miss" }); }
  }
  if (prefs.groupSize) {
    const label = optionLabel("groupSize", prefs.groupSize);
    if (f.groupSize.includes(prefs.groupSize)) { score += 10; criteria.push({ key: "groupSize", label, status: "match" }); }
    else { score -= 12; criteria.push({ key: "groupSize", label, status: "miss" }); }
  }
  score += ordinalCriterion(prefs.walking, f.walking, walkingOrder, 10, -16, criteria, "walking");
  score += ordinalCriterion(prefs.noise, f.noise, noiseOrder, 10, -14, criteria, "noise");
  score += ordinalCriterion(prefs.budget, f.budget, budgetOrder, 10, -16, criteria, "budget");
  if (prefs.weather) {
    const label = optionLabel("weather", prefs.weather);
    if (f.weather.includes(prefs.weather)) { score += 12; criteria.push({ key: "weather", label, status: "match" }); }
    else { score -= 13; criteria.push({ key: "weather", label, status: "miss" }); }
  }
  if (prefs.occasion === "first-date") {
    if (f.easyExit === "must-have") score += 12;
    if (f.booking === "booking-required") score -= 10;
    if (f.noise === "loud") score -= 10;
  }
  return { score: Math.max(0, Math.min(100, score)), criteria };
}

function ordinalCriterion(selected, actual, order, exact, farPenalty, criteria, key) {
  if (!selected) return 0;
  const label = optionLabel(key, selected);
  const distance = Math.abs(order.indexOf(selected) - order.indexOf(actual));
  if (distance === 0) { criteria.push({ key, label, status: "match" }); return exact; }
  if (distance === 1) { criteria.push({ key, label, status: "close" }); return 2; }
  criteria.push({ key, label, status: "miss" });
  return farPenalty;
}

function optionLabel(key, value) {
  return optionLabels[key]?.[value] || window.routeApp.titleCase(value);
}

function isRelatedOccasion(occasions, selected) {
  const pairs = {
    "first-date": ["second-date", "friend-catch-up"],
    "second-date": ["first-date", "friend-catch-up", "neighbourhood-escape"],
    "friend-catch-up": ["second-date", "neighbourhood-escape", "solo-day"],
    "solo-day": ["rainy-day", "neighbourhood-escape"],
    "rainy-day": ["solo-day", "first-date"],
    "neighbourhood-escape": ["solo-day", "second-date", "visitors"],
    "visitors": ["neighbourhood-escape", "solo-day"]
  };
  return occasions.some(occasion => pairs[selected]?.includes(occasion));
}

function formatList(items) {
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

function matchSummary(criteria) {
  if (!criteria.length) return "A flexible place to start.";
  const missed = criteria.filter(c => c.status !== "match");
  if (!missed.length) return "Matches everything you picked.";
  return `Close match — everything except ${formatList(missed.map(c => c.label))}.`;
}

function matchStatusPrefix(status) {
  return status === "match" ? "Matches" : status === "close" ? "Close on" : "Misses on";
}

function resultCard(item, index) {
  const { route, criteria } = item;
  const e = window.routeApp.escape;
  const routeState = route.status === "prototype"
    ? "Prototype · "
    : route.status === "field-checked"
      ? "Field-checked · "
      : "Pilot · ";
  const isFullMatch = criteria.every(c => c.status === "match");
  const eyebrowLabel = index === 0
    ? (isFullMatch ? "Best match" : "Closest match")
    : index === 1 ? "A lighter alternative" : "Another way to go";
  const kicker = index === 0 ? (isFullMatch ? "Best fit" : "Closest fit") : "Worth a look";
  const chips = criteria.length
    ? `<ul class="match-chips" aria-label="How this route matches what you picked">${criteria.map(c => `<li class="match-chip match-chip-${c.status}"><span class="visually-hidden">${matchStatusPrefix(c.status)}: </span>${e(c.label)}</li>`).join("")}</ul>`
    : "";
  return `
    <article class="result-card route-${e(route.slug)}">
      <div class="result-heading">
        <div><p class="eyebrow">${routeState}${eyebrowLabel}</p>
        <h2>${e(route.title)}</h2></div>
        <span class="result-kicker">${kicker}</span>
      </div>
      <p>${e(route.subtitle)}</p>
      <p class="match">${e(matchSummary(criteria))}</p>
      ${chips}
      <div class="facts">
        <span class="fact">${e(route.quickFacts.duration)}</span>
        <span class="fact">${e(route.quickFacts.walkingLevel)} walk</span>
        <span class="fact">${e(route.quickFacts.noiseLevel)}</span>
        <span class="fact">${e(route.quickFacts.budget)}</span>
        <span class="fact">Start: ${e(route.quickFacts.startStation)}</span>
      </div>
      <p class="caveat">${e(route.editorial.whatNotToExpect)}</p>
      <p><a class="button soft" href="${window.routeApp.routeHref(route)}">See the route</a></p>
    </article>`;
}
