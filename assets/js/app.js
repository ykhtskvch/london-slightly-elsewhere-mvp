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
    routeTypeLabel(routeType) {
      return routeType === "day-walk" ? "Full day out" : "London day";
    },
    statusLabel(status) {
      return { "field-checked": "Field-checked", "field-test": "Pilot", prototype: "Prototype", published: "Published" }[status] || "Pilot";
    },
    routeCard(route) {
      const e = this.escape;
      const type = this.routeTypeLabel(route.routeType);
      const labels = { "kings-cross-st-pancras": "King’s Cross St Pancras", "liverpool-street": "Liverpool Street", "london-bridge": "London Bridge", "metropolitan-line": "Metropolitan line", "pub-mid-route": "Pub during the walk", "pub-finish": "Pub near the finish", "multiple-options": "More than one food stop", cafe: "Café or bakery", "bring-food": "Bring food" };
      const human = value => labels[value] || this.titleCase(value || "");
      const duration = route.routeType === "day-walk" ? `${route.hike.distanceKm} km` : route.quickFacts.duration;
      const start = route.routeType === "day-walk" ? `Start: ${route.travel.arrivalStation} · ${route.hike.walkingTime || route.quickFacts.duration} walking` : `Start: ${route.quickFacts.startStation}`;
      const facts = route.routeType === "day-walk"
        ? [`About ${route.travel.typicalMinutes} min from ${human(route.travel.departureHubs[0])}`, human(route.hike.difficulty), route.hike.landscape?.slice(0, 2).map(human).join(" + "), human(route.hike.pubOptions?.[0])]
        : [route.quickFacts.walkingLevel, route.quickFacts.noiseLevel, route.quickFacts.budget];
      const soundtrack = route.soundtrack ? `<p class="soundtrack">This day sounds like: ${e(route.soundtrack.artist)} — <em>${e(route.soundtrack.track)}</em></p>` : "";
      return `<a data-route-card data-route-type="${e(route.routeType)}" class="route-card route-${e(route.slug)}" href="${this.routeHref(route)}"><div class="card-top"><span>${e(type)} · ${e(this.statusLabel(route.status))}</span><span>${e(duration)}</span></div><h3>${e(route.title)}</h3><p>${e(route.subtitle)}</p>${soundtrack}<p class="fine-print">${e(start)}</p><p class="caveat">${e(route.editorial.whatNotToExpect)}</p><div class="facts">${facts.filter(Boolean).map(fact => `<span class="fact">${e(fact)}</span>`).join("")}</div></a>`;
    }
  };
})();
