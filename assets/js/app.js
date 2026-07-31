(() => {
  const basePath = document.body.dataset.basePath || "./";

  window.routeApp = {
    basePath,
    async loadRoutes() {
      const response = await fetch(`${basePath}data/routes.json`);
      if (!response.ok) throw new Error("Route data could not be loaded.");
      return response.json();
    },
    async loadVenueTiming() {
      const response = await fetch(`${basePath}data/venue-timing.json`);
      if (!response.ok) throw new Error("Venue timing data could not be loaded.");
      return response.json();
    },
    routeHref(route) {
      return `${basePath}routes/${route.slug}/`;
    },
    escape(value = "") {
      return String(value).replace(/[&<>'"]/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
      }[char]));
    },
    titleCase(value = "") {
      return value.replaceAll("-", " ").replace(/\b\w/g, letter => letter.toUpperCase());
    },
    statusLabel(status) {
      return { "field-checked": "Field-checked", "field-test": "Pilot", prototype: "Prototype", published: "Published" }[status] || "Pilot";
    },
    routeCard(route) {
      const e = this.escape;
      const isDayWalk = route.routeType === "day-walk";
      const duration = isDayWalk ? `${route.hike.distanceKm} km` : route.quickFacts.duration;
      const start = isDayWalk ? route.travel.arrivalStation : route.quickFacts.startStation;
      const walk = (route.quickFacts.walkingLevel || "").replaceAll("-", " ");
      const facts = [walk.includes("hike") ? walk : `${walk} walk`, route.quickFacts.budget];
      return `<a data-route-card data-route-type="${e(route.routeType)}" class="route-card route-${e(route.slug)}" href="${this.routeHref(route)}"><div class="card-top"><span class="card-status">${e(this.statusLabel(route.status))}</span><span>${e(duration)}</span></div><h3>${e(route.title)}</h3><p>${e(route.subtitle)}</p><p class="fine-print">Start: ${e(start)}</p><div class="facts">${facts.filter(Boolean).map(fact => `<span class="fact">${e(fact)}</span>`).join("")}</div></a>`;
    }
  };
})();
