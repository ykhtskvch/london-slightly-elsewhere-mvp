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
