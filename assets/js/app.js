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
    }
  };
})();
