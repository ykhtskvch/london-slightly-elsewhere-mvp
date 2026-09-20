/* Browse-location filter. Route cards stay visible in the HTML; this script
 * reveals the controls and progressively enhances the list. */
(() => {
  const controls = document.querySelector("[data-browse-controls]");
  const meta = document.querySelector("[data-browse-meta]");
  const cards = [...document.querySelectorAll("[data-route-card][data-location]")];
  if (!controls || !meta || !cards.length) return;

  const buttons = [...controls.querySelectorAll("[data-location-filter]")];
  const allowed = new Set(["all", "london", "outside-london"]);
  const requested = new URLSearchParams(window.location.search).get("location");
  let locationFilter = allowed.has(requested) ? requested : "all";

  const writeUrl = () => {
    const url = new URL(window.location.href);
    if (locationFilter === "all") url.searchParams.delete("location");
    else url.searchParams.set("location", locationFilter);
    window.history.replaceState(window.history.state, "", url);
  };

  const apply = (updateUrl = false) => {
    let shown = 0;
    for (const card of cards) {
      const matches = locationFilter === "all" || card.dataset.location === locationFilter;
      card.hidden = !matches;
      if (matches) shown += 1;
    }

    for (const button of buttons) {
      button.setAttribute("aria-pressed", String(button.dataset.locationFilter === locationFilter));
    }

    const noun = shown === 1 ? "walk" : "walks";
    if (locationFilter === "london") meta.textContent = `Showing ${shown} ${noun} in London.`;
    else if (locationFilter === "outside-london") meta.textContent = `Showing ${shown} ${noun} outside London.`;
    else meta.textContent = `Showing ${shown} ${noun}.`;

    controls.hidden = false;
    if (updateUrl) writeUrl();
  };

  for (const button of buttons) {
    button.addEventListener("click", () => {
      const value = button.dataset.locationFilter;
      if (!allowed.has(value)) return;
      locationFilter = value;
      apply(true);
    });
  }

  apply();
})();
