document.addEventListener("DOMContentLoaded", async () => {
  const controls = document.querySelector("[data-catalogue-controls]");
  const meta = document.querySelector("[data-catalogue-meta]");
  const container = document.querySelector("[data-browse-routes]");
  if (!controls || !meta || !container) return;
  let routes;
  try { routes = await window.routeApp.loadRoutes(); } catch { return; }
  container.innerHTML = routes.map(route => window.routeApp.routeCard(route)).join("");
  const cards = [...container.querySelectorAll("[data-route-card]")];
  const apply = type => {
    const visible = cards.filter(card => type === "all" || card.dataset.routeType === type);
    cards.forEach(card => { card.hidden = !visible.includes(card); });
    meta.textContent = `${visible.length} ${visible.length === 1 ? "route" : "routes"} shown.`;
    const url = new URL(window.location.href); type === "all" ? url.searchParams.delete("type") : url.searchParams.set("type", type); window.history.replaceState({}, "", url);
  };
  const requested = new URLSearchParams(window.location.search).get("type");
  const initial = ["all", "london-day", "day-walk"].includes(requested) ? requested : "all";
  controls.querySelector(`input[value="${initial}"]`).checked = true;
  apply(initial);
  controls.addEventListener("change", event => apply(event.target.value));
});
