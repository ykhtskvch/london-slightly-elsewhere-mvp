#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const routes = JSON.parse(fs.readFileSync(path.join(root, "data/routes.json"), "utf8"));
const failures = [];

function walk(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if ([".git", "node_modules", "build", "dist"].includes(entry.name)) continue;
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(absolute));
    else if (entry.name.endsWith(".html")) files.push(absolute);
  }
  return files;
}

function relative(file) {
  return path.relative(root, file).split(path.sep).join("/");
}

function count(source, expression) {
  return [...source.matchAll(expression)].length;
}

function fail(file, message) {
  failures.push(`${relative(file)}: ${message}`);
}

function localTarget(file, raw) {
  if (!raw || raw.startsWith("#") || raw.startsWith("?")) return null;
  if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(raw)) return null;
  const clean = decodeURIComponent(raw.split(/[?#]/, 1)[0]);
  if (!clean) return null;
  const candidate = clean.startsWith("/")
    ? path.join(root, clean.replace(/^\/+/, ""))
    : path.resolve(path.dirname(file), clean);
  if (!candidate.startsWith(root)) return null;
  if (clean.endsWith("/")) return path.join(candidate, "index.html");
  if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
    return path.join(candidate, "index.html");
  }
  return candidate;
}

const htmlFiles = walk(root);
let imageCount = 0;
let linkCount = 0;

for (const file of htmlFiles) {
  const source = fs.readFileSync(file, "utf8");
  const name = relative(file);
  const h1s = count(source, /<h1\b/gi);
  if (h1s !== 1) fail(file, `expected exactly one h1, found ${h1s}`);

  const ids = [...source.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
  if (duplicateIds.length) fail(file, `duplicate ids: ${duplicateIds.join(", ")}`);

  if (name !== "routes/seventeen/index.html") {
    if (!source.includes('class="site-head"')) fail(file, "missing shared site header");
    for (const label of [">Walks<", ">Find a walk<", ">About<"]) {
      if (!source.includes(label)) fail(file, `shared navigation is missing ${label.slice(1, -1)}`);
    }
    if (!source.includes("assets/css/almanac.css")) fail(file, "missing current design stylesheet");
  }

  for (const match of source.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    const target = localTarget(file, match[1]);
    if (!target) continue;
    linkCount += 1;
    if (!fs.existsSync(target)) fail(file, `missing local target ${match[1]}`);
  }

  for (const match of source.matchAll(/<img\b[^>]*>/gi)) {
    imageCount += 1;
    const tag = match[0];
    if (!/\balt="[^"]*"/.test(tag)) fail(file, "content image has no alt attribute");
    if (!/\bwidth="\d+"/.test(tag) || !/\bheight="\d+"/.test(tag)) {
      fail(file, "content image is missing intrinsic width/height");
    }
    const src = tag.match(/\bsrc="([^"]+)"/)?.[1];
    const target = src && localTarget(file, src);
    if (target && !fs.existsSync(target)) fail(file, `missing image ${src}`);
  }
}

const homeFile = path.join(root, "index.html");
const home = fs.readFileSync(homeFile, "utf8");
if (!home.includes('class="home-hero"')) fail(homeFile, "missing discovery hero");
if (count(home, /<article class="route-card"/g) !== 3) fail(homeFile, "homepage must contain 3 route cards");

const browseFile = path.join(root, "routes/index.html");
const browse = fs.readFileSync(browseFile, "utf8");
if (!browse.includes("data-browse-controls")) fail(browseFile, "missing location controls");
if (count(browse, /<article class="route-card"/g) !== routes.length) {
  fail(browseFile, `expected ${routes.length} route cards`);
}

const finderFile = path.join(root, "find-your-route/index.html");
const finder = fs.readFileSync(finderFile, "utf8");
if (count(finder, /class="finder-group"/g) !== 3) fail(finderFile, "finder must have 3 question groups");
if (count(finder, /\bdata-finder-card\b/g) !== routes.length) {
  fail(finderFile, `expected ${routes.length} server-rendered finder cards`);
}

for (const route of routes) {
  const file = path.join(root, "routes", route.slug, "index.html");
  const source = fs.readFileSync(file, "utf8");
  if (!source.includes('class="button button--primary primary-map"')) fail(file, "missing primary Maps CTA");
  if (!source.includes('class="essentials"')) fail(file, "missing walk essentials");
  const related = source.match(/<section class="discovery-section related-walks">([\s\S]*?)<\/section>/)?.[1] || "";
  if (count(related, /<article class="route-card"/g) !== 3) fail(file, "related walks must contain 3 cards");
}

if (failures.length) {
  console.error(`Site validation failed with ${failures.length} problem${failures.length === 1 ? "" : "s"}:`);
  for (const failure of failures) console.error(`  ${failure}`);
  process.exit(1);
}

console.log(
  `Site validation passed: ${htmlFiles.length} HTML pages, ${routes.length} walk pages, ` +
  `${linkCount} local references, ${imageCount} content images.`
);
