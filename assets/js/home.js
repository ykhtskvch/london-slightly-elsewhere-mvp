document.addEventListener("DOMContentLoaded", async () => {
  const container = document.querySelector("[data-featured-routes]");
  if (!container) return;
  const ids = (container.dataset.featuredRouteIds || "").split(",").map(value => value.trim()).filter(Boolean);
  if (!ids.length) return;
  try {
    const routes = await window.routeApp.loadRoutes();
    const byId = new Map(routes.map(route => [route.id, route]));
    const featured = ids.map(id => byId.get(id)).filter(Boolean);
    if (featured.length) container.innerHTML = featured.map(route => window.routeApp.routeCard(route)).join("");
  } catch {
    // The static cards remain available without route data.
  }
});
