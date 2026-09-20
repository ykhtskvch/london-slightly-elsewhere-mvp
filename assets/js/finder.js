(() => {
  const PARAMS = ["time", "mood", "location"];

  const track = (path, title) => {
    try {
      const counter = window.goatcounter;
      if (!counter || typeof counter.count !== "function") return;
      counter.count({ event: true, path, title });
    } catch {}
  };

  const preferences = form => {
    const data = new FormData(form);
    return Object.fromEntries(PARAMS.flatMap(name => {
      const value = data.get(name);
      return value ? [[name, String(value)]] : [];
    }));
  };

  const cardValues = (card, name) => {
    const value = name === "mood" ? card.dataset.moods : card.dataset[name];
    return (value || "").split("|").filter(Boolean);
  };

  const score = (card, selected) => {
    const entries = Object.entries(selected);
    const matches = entries.reduce((total, [name, value]) => (
      total + (cardValues(card, name).includes(value) ? 1 : 0)
    ), 0);
    return { matches, exact: matches === entries.length };
  };

  const readUrl = form => {
    const params = new URLSearchParams(window.location.search);
    for (const name of PARAMS) {
      for (const input of form.querySelectorAll(`input[name="${name}"]`)) input.checked = false;
      const value = params.get(name);
      if (!value) continue;
      const input = [...form.querySelectorAll(`input[name="${name}"]`)]
        .find(candidate => candidate.value === value);
      if (input) input.checked = true;
    }
  };

  const writeUrl = selected => {
    const url = new URL(window.location.href);
    for (const name of PARAMS) {
      const value = selected[name];
      if (value) url.searchParams.set(name, value);
      else url.searchParams.delete(name);
    }
    window.history.replaceState(window.history.state, "", url);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("[data-finder-form]");
    const target = document.querySelector("[data-finder-results]");
    const meta = document.querySelector("[data-results-meta]");
    if (!form || !target || !meta) return;

    const cards = [...target.querySelectorAll("[data-finder-card]")];

    const render = (updateUrl = false) => {
      const selected = preferences(form);
      const selectedCount = Object.keys(selected).length;
      const ranked = cards
        .map((card, index) => ({ card, index, ...score(card, selected) }))
        .sort((left, right) => right.matches - left.matches || left.index - right.index);

      let results;
      if (selectedCount === 0) {
        results = ranked.slice(0, 3);
        const total = results.length;
        meta.textContent = total === 0
          ? "No walks are available yet."
          : total === 1
            ? "One suggestion to start with."
            : `${total} suggestions to start with.`;
      } else {
        const exact = ranked.filter(item => item.exact);
        if (exact.length) {
          results = exact;
          meta.textContent = exact.length === 1
            ? "Showing one matching walk."
            : `Showing ${exact.length} matching walks.`;
        } else {
          results = ranked.slice(0, 3);
          meta.textContent = "Nothing quite matches — these are the closest walks.";
        }
      }

      const visible = new Set(results.map(item => item.card));
      for (const card of cards) card.hidden = !visible.has(card);
      if (updateUrl) writeUrl(selected);
    };

    const applyFilters = title => {
      render(true);
      track("finder/filter-apply", title);
    };

    readUrl(form);
    render();
    track("finder/open", "Find a walk opened");

    form.addEventListener("change", event => {
      if (!PARAMS.includes(event.target.name)) return;
      applyFilters("Finder filters changed");
    });

    form.addEventListener("submit", event => {
      event.preventDefault();
      applyFilters("Finder filters submitted");
    });

    form.addEventListener("reset", () => {
      window.setTimeout(() => {
        for (const name of PARAMS) {
          for (const input of form.querySelectorAll(`input[name="${name}"]`)) input.checked = false;
        }
        applyFilters("Finder filters cleared");
      }, 0);
    });

    const trackResult = event => {
      const link = event.target.closest("a");
      const card = link && link.closest("[data-finder-card]");
      if (!card || !target.contains(card)) return;
      const slug = card.dataset.routeSlug;
      if (slug) track(`finder/result/${slug}`, "Finder result opened");
    };
    target.addEventListener("click", trackResult);
    target.addEventListener("auxclick", trackResult);
  });
})();
