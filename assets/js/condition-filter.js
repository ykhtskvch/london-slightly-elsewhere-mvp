/* ConditionFilter – the index filter written as a sentence.
 *
 * The only JavaScript on any page in the field-guide design, and the only
 * thing on the index that needs it. The rows themselves are in the HTML, so
 * the index reads in full with this file blocked; the filter block is served
 * hidden and revealed here, because a static host cannot filter on a query
 * string and a control that looks live but does nothing is the thing this
 * redesign exists to remove.
 *
 * Selection applies immediately – no Apply button – and lives in the query
 * string, so a filtered index can be linked.
 *
 * A route matches a word only if it is tagged with it. Where the data has no
 * answer on an axis (the eight full days out carry no cost or weather tags)
 * the route does not match, rather than being assumed to. The filter never
 * claims more than the data says.
 */
(() => {
  const filter = document.querySelector("[data-condition-filter]");
  const index = document.querySelector("[data-index]");
  if (!filter || !index) return;

  const words = [...filter.querySelectorAll("[data-word]")];
  const clear = filter.querySelector("[data-clear]");
  const count = filter.querySelector("[data-result]");
  const rows = [...index.querySelectorAll("[data-row]")];
  const groups = [...index.querySelectorAll("[data-group]")];

  // The result line is prose, so the numbers are words. Beyond thirty the
  // index would be long enough to want a different sentence anyway.
  const NUMBERS = ["none", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    "twenty-one", "twenty-two", "twenty-three", "twenty-four", "twenty-five",
    "twenty-six", "twenty-seven", "twenty-eight", "twenty-nine", "thirty"];
  const spell = value => NUMBERS[value] || String(value);
  const sentenceCase = value => value.charAt(0).toUpperCase() + value.slice(1);

  // Old browse links used ?type=london-day / day-walk. The duration axis says
  // the same thing in the index's own words, so those URLs keep working.
  const LEGACY_TYPE = { "london-day": "an afternoon", "day-walk": "most of a day" };

  const selected = new Set();

  const readUrl = () => {
    const params = new URLSearchParams(window.location.search);
    for (const word of words) {
      const axis = word.dataset.axis;
      const values = (params.get(axis) || "").split(",").filter(Boolean);
      if (values.includes(word.dataset.word)) selected.add(word.dataset.word);
    }
    const legacy = LEGACY_TYPE[params.get("type")];
    if (legacy) selected.add(legacy);
  };

  const writeUrl = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("type");
    const axes = new Map();
    for (const word of words) {
      if (!selected.has(word.dataset.word)) continue;
      const list = axes.get(word.dataset.axis) || [];
      list.push(word.dataset.word);
      axes.set(word.dataset.axis, list);
    }
    for (const word of words) url.searchParams.delete(word.dataset.axis);
    for (const [axis, list] of axes) url.searchParams.set(axis, list.join(","));
    window.history.replaceState({}, "", url);
  };

  const matches = row => {
    const tags = new Set((row.dataset.tags || "").split("|").filter(Boolean));
    // Words within one axis are alternatives; the axes are all required.
    const axes = new Map();
    for (const word of words) {
      if (!selected.has(word.dataset.word)) continue;
      const list = axes.get(word.dataset.axis) || [];
      list.push(word.dataset.word);
      axes.set(word.dataset.axis, list);
    }
    for (const list of axes.values()) {
      if (!list.some(value => tags.has(value))) return false;
    }
    return true;
  };

  const apply = () => {
    let shown = 0;
    let walked = 0;
    for (const row of rows) {
      const ok = matches(row);
      row.hidden = !ok;
      if (!ok) continue;
      shown += 1;
      if (row.dataset.walked === "true") walked += 1;
    }
    // A heading that introduces nothing is worse than no heading.
    for (const group of groups) {
      group.hidden = !group.querySelector("[data-row]:not([hidden])");
    }
    for (const word of words) {
      word.setAttribute("aria-pressed", selected.has(word.dataset.word) ? "true" : "false");
    }

    // The result line reports both how many match and how many of those have
    // been walked – the fact the index is ordered by.
    const walkedClause = `${spell(walked)} of them I have walked.`;
    let line;
    if (selected.size === 0) {
      line = `No words chosen. ${sentenceCase(spell(shown))} ` +
        `${shown === 1 ? "route" : "routes"}, and ${walkedClause}`;
    } else {
      const chosen = `${sentenceCase(spell(selected.size))} ` +
        `${selected.size === 1 ? "word" : "words"} chosen.`;
      line = shown === 0
        ? `${chosen} Nothing matches; take a word out.`
        : `${chosen} ${sentenceCase(spell(shown))} ` +
          `${shown === 1 ? "route matches" : "routes match"}; ${walkedClause}`;
    }
    count.textContent = line;
    clear.hidden = selected.size === 0;
    writeUrl();
  };

  for (const word of words) {
    word.addEventListener("click", () => {
      const value = word.dataset.word;
      selected.has(value) ? selected.delete(value) : selected.add(value);
      apply();
    });
  }

  clear.addEventListener("click", () => {
    selected.clear();
    apply();
  });

  readUrl();
  filter.hidden = false;
  apply();
})();
