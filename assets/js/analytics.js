/* Counting, without reading anything off the visitor's device.
 *
 * GoatCounter's count.js sets no cookies, but its own filter reads
 * localStorage on every page load — the "skipgc" key behind its
 * #toggle-goatcounter opt-out. This file replaces that filter with one that
 * touches no storage at all, so a visit to this site stores nothing and
 * reads nothing.
 *
 * The count.js tag carries no_onload, so nothing is counted until the filter
 * below has been installed. count() and bind_events() are then called here,
 * with the same visibility handling the script does itself.
 *
 * What is lost: #toggle-goatcounter no longer stops the count, because
 * knowing that somebody set it would mean reading it back. Do Not Track and
 * Global Privacy Control are honoured instead. They are browser-level, need
 * no storage, and are a setting rather than a URL nobody would guess.
 */
(function () {
  var gc = window.goatcounter;
  if (!gc || !gc.count) return;

  gc.filter = function () {
    // Everything count.js filtered on, minus the localStorage line.
    if ("visibilityState" in document && document.visibilityState === "prerender")
      return "prerender";
    if (location !== parent.location) return "frame";
    if (location.hostname.match(
      /(localhost$|^127\.|^10\.|^172\.(1[6-9]|2[0-9]|3[0-1])\.|^192\.168\.|^0\.0\.0\.0$)/
    )) return "localhost";
    if (location.protocol === "file:") return "localfile";

    // The opt-out, in place of the one that needed storage.
    if (navigator.globalPrivacyControl) return "globalPrivacyControl";
    if (navigator.doNotTrack === "1" || window.doNotTrack === "1") return "doNotTrack";

    return false;
  };

  // count.js counts on load unless the page is still hidden, in which case it
  // waits for the tab to be looked at. Same here.
  if (!("visibilityState" in document) || document.visibilityState === "visible") {
    gc.count();
  } else {
    var onVisible = function () {
      if (document.visibilityState !== "visible") return;
      document.removeEventListener("visibilitychange", onVisible);
      gc.count();
    };
    document.addEventListener("visibilitychange", onVisible);
  }

  gc.bind_events();
})();
