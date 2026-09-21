(() => {
  // The mobile menu is a <details>, so it opens and closes with no script.
  // What it cannot do alone is close when the reader taps elsewhere or
  // presses Escape — the two things every menu is expected to do.
  const nav = document.querySelector(".mobile-nav");
  if (!nav) return;
  const summary = nav.querySelector("summary");

  document.addEventListener("click", event => {
    if (nav.open && !nav.contains(event.target)) nav.open = false;
  });

  document.addEventListener("keydown", event => {
    if (event.key !== "Escape" || !nav.open) return;
    nav.open = false;
    if (summary) summary.focus();
  });
})();

(() => {
  // On a phone the walk's start button floats at the foot of the screen.
  // While the essentials rail — which has the same button — is in view,
  // the floating copy is a duplicate, so it stands down until the rail
  // has scrolled past.
  const bar = document.querySelector(".route-startbar");
  const rail = document.querySelector(".route-rail");
  if (!bar || !rail || !("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) bar.classList.toggle("route-startbar--parked", entry.isIntersecting);
  });
  observer.observe(rail);
})();

(() => {
  // A long essentials rail on a phone shows four rows; the rest wait
  // behind a button. The button is hidden in the markup, so without this
  // script every row simply shows.
  const rail = document.querySelector(".route-rail");
  const toggle = rail && rail.querySelector("[data-rail-toggle]");
  if (!rail || !toggle) return;
  const more = toggle.textContent;
  rail.classList.add("route-rail--folded");
  toggle.hidden = false;
  toggle.addEventListener("click", () => {
    const folded = rail.classList.toggle("route-rail--folded");
    toggle.setAttribute("aria-expanded", String(!folded));
    toggle.textContent = folded ? more : "Show fewer";
  });
})();
