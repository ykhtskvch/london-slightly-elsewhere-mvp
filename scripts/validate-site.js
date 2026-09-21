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
  const walked = ["field-checked", "published"].includes(route.status);
  const mapClass = walked ? "button button--primary primary-map" : "button button--secondary";
  const mapCta = `class="${mapClass}" data-goatcounter-click="maps/${route.slug}"`;
  if (!source.includes(mapCta)) fail(file, `missing ${walked ? "primary" : "secondary"} Maps CTA`);
  if (!source.includes('class="route-rail"')) fail(file, "missing walk essentials rail");
  const related = source.match(/<section class="discovery-section related-walks">([\s\S]*?)<\/section>/)?.[1] || "";
  if (count(related, /<article class="route-card"/g) !== 3) fail(file, "related walks must contain 3 cards");
}

// Crawlability. Nothing here is hard to get right once; all of it is easy
// to break later without noticing, which is the only way it would break.
const site = JSON.parse(fs.readFileSync(path.join(root, "data/site.json"), "utf8"));
const siteUrl = `${site.origin}${site.basePath}`;
const noindex = source => /<meta name="robots" content="[^"]*\bnoindex\b/.test(source);
const pageFor = url => {
  if (!url.startsWith(siteUrl)) return null;
  const rest = url.slice(siteUrl.length);
  return path.join(root, rest, rest === "" || rest.endsWith("/") ? "index.html" : "");
};

const sitemapFile = path.join(root, "sitemap.xml");
const sitemap = fs.readFileSync(sitemapFile, "utf8");
const listed = new Set();
for (const match of sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)) {
  const url = match[1];
  const page = pageFor(url);
  if (!page) { fail(sitemapFile, `${url} is not under ${siteUrl}`); continue; }
  listed.add(page);
  if (!fs.existsSync(page)) { fail(sitemapFile, `${url} has no page`); continue; }
  const source = fs.readFileSync(page, "utf8");
  if (noindex(source)) fail(page, "listed in the sitemap but marked noindex");
  const canonical = source.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  if (canonical !== url) fail(page, `canonical is ${canonical || "missing"}, sitemap says ${url}`);
}
for (const file of htmlFiles) {
  const source = fs.readFileSync(file, "utf8");
  if (relative(file) === "404.html" || noindex(source) || listed.has(file)) continue;
  fail(file, "indexable page missing from the sitemap");
}

const robotsFile = path.join(root, "robots.txt");
const robots = fs.readFileSync(robotsFile, "utf8");
if (!robots.includes(`Sitemap: ${siteUrl}sitemap.xml`)) fail(robotsFile, "does not name the sitemap");
const searchBots = ["*", "googlebot", "bingbot", "oai-searchbot", "claude-searchbot", "claude-user"];
let agents = [];
for (const line of robots.split("\n")) {
  const [, field, value] = line.match(/^\s*([a-z-]+)\s*:\s*(.*?)\s*$/i) || [];
  if (!field) { agents = []; continue; }
  if (field.toLowerCase() === "user-agent") agents.push(value.toLowerCase());
  if (field.toLowerCase() === "disallow" && value === "/") {
    for (const agent of agents.filter(agent => searchBots.includes(agent))) {
      fail(robotsFile, `blocks search crawler ${agent} from the whole site`);
    }
  }
}

for (const file of htmlFiles) {
  const source = fs.readFileSync(file, "utf8");
  const blocks = [...source.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
  if (blocks.length > 1) fail(file, `${blocks.length} JSON-LD blocks; one per page`);
  for (const [, block] of blocks) {
    try { JSON.parse(block); } catch (error) { fail(file, `JSON-LD does not parse: ${error.message}`); }
  }
  if (!noindex(source) && relative(file) !== "404.html" && relative(file) !== "index.html") {
    if (!source.includes('"@type":"BreadcrumbList"')) fail(file, "missing BreadcrumbList markup");
  }
}
for (const route of routes) {
  const file = path.join(root, "routes", route.slug, "index.html");
  const source = fs.readFileSync(file, "utf8");
  for (const needle of ['"@type":"Article"', '"author":', '"publisher":']) {
    if (!source.includes(needle)) fail(file, `Article markup is missing ${needle}`);
  }
}

const llmsFile = path.join(root, "llms.txt");
if (!fs.existsSync(llmsFile)) fail(llmsFile, "missing");
else {
  const llms = fs.readFileSync(llmsFile, "utf8");
  for (const match of llms.matchAll(/\]\(([^)]+)\)/g)) {
    const page = pageFor(match[1]);
    if (!page) fail(llmsFile, `${match[1]} is not under ${siteUrl}`);
    else if (!fs.existsSync(page)) fail(llmsFile, `${match[1]} has no page`);
  }
  for (const route of routes) {
    if (!llms.includes(`${siteUrl}routes/${route.slug}/`)) fail(llmsFile, `does not list ${route.slug}`);
  }
}

if (failures.length) {
  console.error(`Site validation failed with ${failures.length} problem${failures.length === 1 ? "" : "s"}:`);
  for (const failure of failures) console.error(`  ${failure}`);
  process.exit(1);
}

console.log(
  `Site validation passed: ${htmlFiles.length} HTML pages, ${routes.length} walk pages, ` +
  `${linkCount} local references, ${imageCount} content images, ${listed.size} sitemap entries.`
);
