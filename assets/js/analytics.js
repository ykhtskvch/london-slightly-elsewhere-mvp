/* Counting, without reading anything off the visitor's device.
 *
 * GoatCounter's count.js sets no cookies, but its own filter reads
 * localStorage on every page load – the "skipgc" key behind its
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
  var internal = new URLSearchParams(window.location.search).get("internal") === "1";

  // Keep an owner's QA session out of analytics as it moves around the site.
  // The marker lives only in the URL: nothing is stored on or read from the
  // visitor's device.
  var propagateInternal = function () {
    if (!internal) return;
    Array.prototype.slice.call(document.querySelectorAll("a[href]")).forEach(function (link) {
      try {
        var url = new URL(link.getAttribute("href"), window.location.href);
        if (url.origin !== window.location.origin) return;
        url.searchParams.set("internal", "1");
        link.href = url.href;
      } catch (_) {}
    });
  };
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", propagateInternal);
  else
    propagateInternal();

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

    if (internal) return "internal";

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
