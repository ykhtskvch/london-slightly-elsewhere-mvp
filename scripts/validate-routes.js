#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const routes = JSON.parse(fs.readFileSync(path.join(root, "data/routes.json"), "utf8"));
const discovery = JSON.parse(fs.readFileSync(path.join(root, "data/discovery.json"), "utf8"));
const errors = [];

const routeTypes = new Set(["london-day", "day-walk"]);
const departureHubs = new Set(["marylebone", "paddington", "euston", "kings-cross-st-pancras", "liverpool-street", "stratford", "london-bridge", "victoria", "waterloo", "metropolitan-line", "other"]);
const travelBands = new Set(["under-60", "60-90"]);
const journeyComplexities = new Set(["direct", "one-change"]);
const transportModes = new Set(["rail", "tube", "rail-and-tube"]);
const distanceBands = new Set(["15-18", "18-22", "22-25"]);
const difficulties = new Set(["easy", "moderate", "challenging"]);
const routeShapes = new Set(["circular", "point-to-point", "either"]);
const landscapes = new Set(["coastline", "woodland", "hills", "river", "wetlands", "chalk-downs", "farmland", "heathland", "open-countryside", "villages"]);
const views = new Set(["panoramic", "sea", "woodland", "rolling-countryside", "historic-villages"]);
const urbanPresence = new Set(["mostly-nature", "lightly-settled", "mixed"]);
const pubOptions = new Set(["pub-mid-route", "pub-finish", "multiple-options", "cafe", "bring-food"]);
const discoveryTimeBands = new Set(["1-2-hours", "half-day", "full-day"]);
const discoveryLocations = new Set(["london", "outside-london"]);
const discoveryMoods = new Set(["green", "riverside-canal", "urban", "architecture", "pub", "quiet"]);

const addError = (route, message) => errors.push(`${route?.slug || "data"}: ${message}`);
const isString = value => typeof value === "string" && value.trim().length > 0;
const isUrl = value => {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
};
const validateControlledList = (route, label, values, allowed) => {
  if (!Array.isArray(values) || values.some(value => !allowed.has(value))) addError(route, `${label} contains an unsupported value`);
};

const ids = new Set();
const slugs = new Set();

for (const route of routes) {
  if (!isString(route.id)) addError(route, "missing id");
  else if (ids.has(route.id)) addError(route, "duplicate id");
  else ids.add(route.id);

  if (!isString(route.slug)) addError(route, "missing slug");
  else if (slugs.has(route.slug)) addError(route, "duplicate slug");
  else slugs.add(route.slug);

  if (!routeTypes.has(route.routeType)) addError(route, "routeType must be london-day or day-walk");
  if (!("soundtrack" in route)) addError(route, "missing soundtrack field");
  if (route.soundtrack !== null && (!route.soundtrack || !isString(route.soundtrack.artist) || !isString(route.soundtrack.track))) {
    addError(route, "soundtrack must be null or include artist and track");
  }

  if (!route.quickFacts || !Array.isArray(route.stops) || route.stops.length === 0) addError(route, "missing route quick facts or stops");
  if (route.quickFacts?.mainStops !== route.stops?.length) addError(route, "quickFacts.mainStops must match the stop count");

  const stops = Array.isArray(route.stops) ? route.stops : [];
  for (const [stopIndex, stop] of stops.entries()) {
    if (stop.choices === undefined) continue;
    if (!Array.isArray(stop.choices) || stop.choices.length < 2) {
      addError(route, `stops[${stopIndex}].choices must contain at least two options`);
      continue;
    }
    for (const [choiceIndex, choice] of stop.choices.entries()) {
      for (const key of ["name", "description", "mapQuery"]) {
        if (!isString(choice?.[key])) addError(route, `stops[${stopIndex}].choices[${choiceIndex}].${key} is missing`);
      }
      if (choice?.meta !== undefined && !isString(choice.meta)) addError(route, `stops[${stopIndex}].choices[${choiceIndex}].meta must be a string`);
    }
  }

  const optionalDetours = route.optionalDetours;
  if (optionalDetours !== undefined) {
    if (!Array.isArray(optionalDetours) || optionalDetours.length === 0) {
      addError(route, "optionalDetours must be a non-empty array when supplied");
    } else {
      for (const [index, detour] of optionalDetours.entries()) {
        for (const key of ["eyebrow", "name", "description", "mapQuery"]) {
          if (!isString(detour?.[key])) addError(route, `optionalDetours[${index}].${key} is missing`);
        }
      }
    }
  }

  const extension = route.extension;
  if (extension !== undefined) {
    if (!extension || typeof extension !== "object" || Array.isArray(extension)) {
      addError(route, "extension must be an object when supplied");
    } else {
      for (const key of ["eyebrow", "title", "intro", "distance", "duration", "mapOriginQuery"]) {
        if (!isString(extension[key])) addError(route, `extension.${key} is missing`);
      }
      if (!Array.isArray(extension.stops) || extension.stops.length === 0) {
        addError(route, "extension.stops must be a non-empty array");
      } else {
        for (const [index, stop] of extension.stops.entries()) {
          for (const key of ["name", "type", "duration", "description", "mapQuery"]) {
            if (!isString(stop?.[key])) addError(route, `extension.stops[${index}].${key} is missing`);
          }
        }
      }
    }
  }

  const urls = [
    route.navigation?.externalRouteUrl,
    route.navigation?.gpxUrl,
    route.navigation?.finish?.officialUrl,
    route.travel?.officialSourceUrl,
    ...(route.links?.officialSources || []),
    ...stops.map(stop => stop.officialUrl),
    ...stops.flatMap(stop => Array.isArray(stop.choices) ? stop.choices.map(choice => choice.officialUrl) : []),
    ...(Array.isArray(optionalDetours) ? optionalDetours : []).map(detour => detour.officialUrl),
    ...(Array.isArray(extension?.stops) ? extension.stops : []).map(stop => stop.officialUrl)
  ].filter(Boolean);
  for (const url of urls) if (!isUrl(url)) addError(route, `invalid external URL: ${url}`);

  // The page has to exist and has to be this route's page. How it says so
  // depends on which generator wrote it. A thin shell built by
  // build_route_pages.py names the route in data-route-id, because
  // route-page.js reads that to know what to render. A page built by
  // build_almanac_pages.py carries no such attribute — it is written out in
  // full and loads no JavaScript at all — so it identifies itself by its
  // canonical URL, which is the thing that actually breaks if a page is ever
  // written into the wrong directory.
  const page = path.join(root, "routes", route.slug || "", "index.html");
  if (!fs.existsSync(page)) addError(route, "missing route detail page");
  else {
    const html = fs.readFileSync(page, "utf8");
    const named = html.includes(`data-route-id="${route.id}"`);
    const canonical = new RegExp(`<link rel="canonical" href="[^"]*/routes/${route.slug}/">`).test(html);
    if (!named && !canonical) addError(route, "route detail page does not identify itself as this route");
  }

  if (route.routeType === "london-day") {
    const filters = route.filters || {};
    for (const key of ["occasion", "groupSize", "weather"]) if (!Array.isArray(filters[key])) addError(route, `London-day filters.${key} must be an array`);
    for (const key of ["walking", "noise", "budget", "easyExit", "booking"]) if (!isString(filters[key])) addError(route, `London-day filters.${key} is missing`);
    continue;
  }

  const travel = route.travel;
  const hike = route.hike;
  const filters = route.filters || {};
  const validTravel = Boolean(travel && typeof travel === "object" && !Array.isArray(travel));
  const validHike = Boolean(hike && typeof hike === "object" && !Array.isArray(hike));
  if (!validTravel) addError(route, "day-walk routes need a travel object");
  if (!validHike) addError(route, "day-walk routes need a hike object");
  if (!validTravel || !validHike) continue;

  for (const key of ["departureHubs", "travelTimeBand", "journeyComplexity", "arrivalStation", "returnStation", "transportMode", "serviceNote"]) if (!(key in travel)) addError(route, `travel.${key} is missing`);
  if (!("officialSourceUrl" in travel)) addError(route, "travel.officialSourceUrl is missing");
  validateControlledList(route, "travel.departureHubs", travel.departureHubs, departureHubs);
  if (!Number.isFinite(travel.typicalMinutes) || travel.typicalMinutes <= 0 || travel.typicalMinutes > 90) addError(route, "travel.typicalMinutes must be between 1 and 90");
  if (!travelBands.has(travel.travelTimeBand)) addError(route, "unsupported travelTimeBand");
  if (!journeyComplexities.has(travel.journeyComplexity)) addError(route, "unsupported journeyComplexity");
  if (!transportModes.has(travel.transportMode)) addError(route, "unsupported transportMode");
  for (const key of ["arrivalStation", "returnStation", "serviceNote"]) if (!isString(travel[key])) addError(route, `travel.${key} is missing`);

  for (const key of ["distanceKm", "distanceBand", "difficulty", "routeShape", "elevationGainM", "landscape", "views", "urbanPresence", "terrainNotes", "shortenable", "shorterOptionKm", "shorteningNote", "pubOptions"]) if (!(key in hike)) addError(route, `hike.${key} is missing`);
  if ("walkingTime" in hike && hike.walkingTime !== null && !isString(hike.walkingTime)) addError(route, "hike.walkingTime must be a string or null");
  if (!Number.isFinite(hike.distanceKm) || hike.distanceKm < 15 || hike.distanceKm > 25) addError(route, "hike.distanceKm must be between 15 and 25");
  if (!distanceBands.has(hike.distanceBand)) addError(route, "unsupported hike.distanceBand");
  if (!difficulties.has(hike.difficulty)) addError(route, "unsupported hike.difficulty");
  if (!routeShapes.has(hike.routeShape)) addError(route, "unsupported hike.routeShape");
  validateControlledList(route, "hike.landscape", hike.landscape, landscapes);
  validateControlledList(route, "hike.views", hike.views, views);
  if (!urbanPresence.has(hike.urbanPresence)) addError(route, "unsupported hike.urbanPresence");
  validateControlledList(route, "hike.pubOptions", hike.pubOptions, pubOptions);
  if (typeof hike.shortenable !== "boolean") addError(route, "hike.shortenable must be boolean");
  if (hike.elevationGainM !== null && !Number.isFinite(hike.elevationGainM)) addError(route, "hike.elevationGainM must be a number or null");
  if (hike.shorterOptionKm !== null && !Number.isFinite(hike.shorterOptionKm)) addError(route, "hike.shorterOptionKm must be a number or null");
  if (hike.shorteningNote !== null && !isString(hike.shorteningNote)) addError(route, "hike.shorteningNote must be a string or null");
  if (!isString(hike.terrainNotes)) addError(route, "hike.terrainNotes is missing");
  if (hike.earlyExit !== undefined && (!hike.earlyExit || typeof hike.earlyExit !== "object" || Array.isArray(hike.earlyExit) || !isString(hike.earlyExit.label) || ("note" in hike.earlyExit && hike.earlyExit.note !== null && !isString(hike.earlyExit.note)))) addError(route, "hike.earlyExit must include a label and optional note");
  if (hike.conditions !== undefined) {
    if (!hike.conditions || typeof hike.conditions !== "object" || Array.isArray(hike.conditions)) addError(route, "hike.conditions must be an object when supplied");
    else for (const key of ["mudOrDrainage", "exposedSections", "roadSections", "stiles", "foodWater", "toilets", "mobileSignal", "pubTiming"]) {
      if (key in hike.conditions && hike.conditions[key] !== null && !isString(hike.conditions[key])) addError(route, `hike.conditions.${key} must be a string or null`);
    }
  }

  if (filters.routeType !== "day-walk") addError(route, "day-walk filters.routeType must be day-walk");
  if (filters.distance !== hike.distanceBand) addError(route, "filters.distance must match hike.distanceBand");
  if (filters.travelTime !== travel.travelTimeBand) addError(route, "filters.travelTime must match travel.travelTimeBand");
  validateControlledList(route, "filters.departureHubs", filters.departureHubs, departureHubs);
  validateControlledList(route, "filters.landscape", filters.landscape, landscapes);
  validateControlledList(route, "filters.views", filters.views, views);
  validateControlledList(route, "filters.pub", filters.pub, pubOptions);
  if (!urbanPresence.has(filters.urbanPresence)) addError(route, "unsupported filters.urbanPresence");
  if (!difficulties.has(filters.difficulty)) addError(route, "unsupported filters.difficulty");
  if (!routeShapes.has(filters.routeShape)) addError(route, "unsupported filters.routeShape");
  if (!journeyComplexities.has(filters.journeyComplexity)) addError(route, "unsupported filters.journeyComplexity");
  if (typeof filters.shortenable !== "boolean") addError(route, "filters.shortenable must be boolean");
}

// Discovery metadata is kept separate from the editorial route records so a
// small, controlled filter vocabulary cannot drift into the author's copy.
// Coverage is exact: every route has one entry, and an entry may not survive
// after its route has been removed or renamed.
const discoverySlugs = new Set();
if (!Array.isArray(discovery)) {
  errors.push("discovery: data/discovery.json must be an array");
} else {
  for (const item of discovery) {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      errors.push("discovery: every entry must be an object");
      continue;
    }

    const expectedKeys = ["cardTitle", "location", "moods", "slug", "timeBand"];
    const actualKeys = Object.keys(item).sort();
    if (actualKeys.join(",") !== expectedKeys.join(",")) {
      errors.push(`discovery/${item.slug || "unknown"}: fields must be exactly ${expectedKeys.join(", ")}`);
    }

    if (!isString(item.slug)) {
      errors.push("discovery: entry is missing slug");
      continue;
    }
    if (discoverySlugs.has(item.slug)) {
      errors.push(`discovery/${item.slug}: duplicate slug`);
    } else {
      discoverySlugs.add(item.slug);
    }

    if (!slugs.has(item.slug)) errors.push(`discovery/${item.slug}: no matching route`);
    if (!isString(item.cardTitle)) errors.push(`discovery/${item.slug}: cardTitle is missing`);
    if (!discoveryTimeBands.has(item.timeBand)) {
      errors.push(`discovery/${item.slug}: unsupported timeBand`);
    }
    if (!discoveryLocations.has(item.location)) {
      errors.push(`discovery/${item.slug}: unsupported location`);
    }
    if (!Array.isArray(item.moods) || item.moods.length < 1 || item.moods.length > 4) {
      errors.push(`discovery/${item.slug}: moods must contain between one and four values`);
    } else {
      if (new Set(item.moods).size !== item.moods.length) {
        errors.push(`discovery/${item.slug}: moods must not contain duplicates`);
      }
      if (item.moods.some(mood => !discoveryMoods.has(mood))) {
        errors.push(`discovery/${item.slug}: moods contains an unsupported value`);
      }
    }
  }
}

for (const route of routes) {
  if (isString(route.slug) && !discoverySlugs.has(route.slug)) {
    addError(route, "missing discovery entry");
  }
}

// The `almanac` block drives the field-guide design. These checks are the
// design's acceptance criteria expressed as data rules: the five facts in a
// fixed order, one effort scale of three words, a photograph only where a
// route has been walked, and an absence sentence written per route rather
// than from a template.
const effortWords = new Set(["flat", "gentle", "a proper walk"]);
const factOrder = ["station", "time", "effort", "cost", "toilets"];
// A fact value is set in `white-space: nowrap`, so an over-long one would
// push the column sideways at 375px.
const FACT_VALUE_MAX = 28;
const absenceSentences = new Map();

for (const route of routes) {
  const almanac = route.almanac;
  if (almanac === undefined) continue;
  if (!almanac || typeof almanac !== "object" || Array.isArray(almanac)) {
    addError(route, "almanac must be an object when supplied");
    continue;
  }

  if (typeof almanac.walked !== "boolean") addError(route, "almanac.walked must be boolean");
  if (almanac.lastWalked !== null && !isString(almanac.lastWalked)) addError(route, "almanac.lastWalked must be a string or null");
  if (!effortWords.has(almanac.effort)) addError(route, `almanac.effort must be one of ${[...effortWords].join(", ")}`);
  if (!isString(almanac.linkName)) addError(route, "almanac.linkName is missing");

  const facts = almanac.factLine;
  if (!facts || typeof facts !== "object" || Array.isArray(facts)) addError(route, "almanac.factLine is missing");
  else {
    const found = [...String(facts.sentence || "").matchAll(/\{([a-z]+)\}/g)].map(match => match[1]);
    if (found.join(",") !== factOrder.join(",")) {
      addError(route, `almanac.factLine.sentence must name ${factOrder.join(", ")} once each, in that order`);
    }
    for (const key of factOrder) {
      if (!isString(facts[key])) addError(route, `almanac.factLine.${key} is missing`);
      else if (facts[key].length > FACT_VALUE_MAX) addError(route, `almanac.factLine.${key} is over ${FACT_VALUE_MAX} characters and would not fit on one line at 375px`);
    }
    if (facts.effort !== almanac.effort) addError(route, "almanac.factLine.effort must match almanac.effort");
  }

  if (almanac.walked) {
    const plate = almanac.plate;
    if (!plate || !isString(plate.caption)) addError(route, "a walked route needs almanac.plate.caption");
    if (plate && !plate.image && !isString(plate.placeholder)) addError(route, "almanac.plate needs an image or a placeholder label");
    if ("absence" in almanac) addError(route, "a walked route must not carry an absence sentence");
  } else {
    if (!isString(almanac.absence)) addError(route, "an unwalked route needs almanac.absence");
    if (!isString(almanac.caveat)) addError(route, "an unwalked route needs almanac.caveat");
    if ("plate" in almanac) addError(route, "photographs appear only on walked routes");
    const seen = absenceSentences.get(almanac.absence);
    if (seen) addError(route, `almanac.absence repeats the sentence used by ${seen} – each absence is written for its own route`);
    else if (isString(almanac.absence)) absenceSentences.set(almanac.absence, route.slug);
  }
}

if (errors.length) {
  console.error(`Route validation failed with ${errors.length} error${errors.length === 1 ? "" : "s"}:`);
  errors.forEach(error => console.error(`- ${error}`));
  process.exitCode = 1;
} else {
  console.log(`Route validation passed: ${routes.length} routes, ${routes.filter(route => route.routeType === "london-day").length} London days, ${routes.filter(route => route.routeType === "day-walk").length} full days out, ${discovery.length} discovery entries.`);
}
