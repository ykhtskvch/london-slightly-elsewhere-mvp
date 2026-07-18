const walkingOrder = ["very-low", "gentle", "medium", "urban-hike"];
const noiseOrder = ["quiet", "moderate", "lively", "loud"];
const budgetOrder = ["free-ish", "under-30", "30-70", "splurge"];

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
  meta.textContent = hasPreferences
    ? `Three routes, ranked for the shape of day you picked.`
    : `Browse sixteen routes, or use the filters to make the choice more specific.`;
  target.innerHTML = results.map((item, index) => resultCard(item, index)).join("");
}

function scoreRoute(route, prefs) {
  let score = 50;
  const reasons = [];
  const f = route.filters;
  const label = value => window.routeApp.titleCase(value);

  if (prefs.occasion) {
    if (f.occasion.includes(prefs.occasion)) {
      score += 25; reasons.push(label(prefs.occasion));
    } else if (isRelatedOccasion(f.occasion, prefs.occasion)) {
      score += 10; reasons.push("a nearby occasion");
    } else score -= 10;
  }
  if (prefs.groupSize) {
    if (f.groupSize.includes(prefs.groupSize)) { score += 10; reasons.push(`${label(prefs.groupSize)} people`); }
    else score -= 12;
  }
  score += ordinalScore(prefs.walking, f.walking, walkingOrder, 10, -16, reasons, "walking");
  score += ordinalScore(prefs.noise, f.noise, noiseOrder, 10, -14, reasons, "noise");
  score += ordinalScore(prefs.budget, f.budget, budgetOrder, 10, -16, reasons, "budget");
  if (prefs.weather) {
    if (f.weather.includes(prefs.weather)) { score += 12; reasons.push(label(prefs.weather)); }
    else score -= 13;
  }
  if (prefs.occasion === "first-date") {
    if (f.easyExit === "must-have") { score += 12; reasons.push("an easy exit"); }
    if (f.booking === "booking-required") score -= 10;
    if (f.noise === "loud") score -= 10;
  }
  return { score: Math.max(0, Math.min(100, score)), reasons };
}

function ordinalScore(selected, actual, order, exact, farPenalty, reasons, text) {
  if (!selected) return 0;
  const distance = Math.abs(order.indexOf(selected) - order.indexOf(actual));
  if (distance === 0) { reasons.push(`${text} that fits`); return exact; }
  if (distance === 1) return 2;
  return farPenalty;
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

function resultCard(item, index) {
  const { route, reasons } = item;
  const e = window.routeApp.escape;
  const routeState = route.status === "prototype"
    ? "Prototype · "
    : route.status === "field-checked"
      ? "Field-checked · "
      : "Pilot · ";
  const reasonText = reasons.length
    ? `Good for ${reasons.slice(0, 3).join(", ")}${reasons.length > 3 ? " and more" : ""}.`
    : "A flexible place to start.";
  return `
    <article class="result-card route-${e(route.slug)}">
      <div class="result-heading">
        <div><p class="eyebrow">${routeState}${index === 0 ? "Best match" : index === 1 ? "A lighter alternative" : "Another way to go"}</p>
        <h2>${e(route.title)}</h2></div>
        <span class="result-kicker">${index === 0 ? "Best fit" : "Worth a look"}</span>
      </div>
      <p>${e(route.subtitle)}</p>
      <p class="match">${e(reasonText)}</p>
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
