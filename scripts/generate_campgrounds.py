#!/usr/bin/env python3
"""
Generates one Hugo content page per STATE from data/campgrounds.json.

Usage (run from the Hugo project root):
    python3 scripts/generate_campgrounds.py

Source of truth is data/campgrounds.json. For every state that appears in the
JSON this writes content/campgrounds/<state-slug>.md (e.g. idaho.md). Those
pages use layouts/_default/state.html, which reads the campground entries
straight from the JSON at build time, so the page body never needs hand-editing.

What the script writes to each state page's front matter:
  * title / seo_title / description  (unique per state, built from the data)
  * aliases  -> the old per-campground URLs, so old links and Google's index
                redirect to the state page instead of 404ing
  * data_hash / lastmod -> lastmod only moves when that state's data changes,
                which keeps the sitemap's <lastmod> honest

Anything you type BELOW the closing +++ of a state page (markdown) is kept on
re-runs and shown as an intro on that state's page -- this is the place to add
hand-written, state-specific tips (the best long-term SEO lever).

The script also removes the legacy one-page-per-campground files from
content/campgrounds/ (any <slug>.md whose slug is in the JSON) and any
previously generated state page for a state that no longer has campgrounds.
"""
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "campgrounds.json")
OUT_DIR = os.path.join(ROOT, "content", "campgrounds")
MARKER = 'generated_by = "scripts/generate_campgrounds.py"'
SITE_NAME = "Traveler Camps"

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Puerto Rico": "PR",
}


def toml_string(value: str) -> str:
    value = value or ""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def state_slug(state: str) -> str:
    # Must match Hugo's `urlize` for plain state names (lowercase, hyphens).
    return re.sub(r"[^a-z0-9]+", "-", state.lower()).strip("-")


def join_list(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def unique_cities(entries):
    """Cities ordered by number of campgrounds (desc), then alphabetically."""
    counts = {}
    for e in entries:
        city = (e.get("location") or "").strip()
        if city:
            counts[city] = counts.get(city, 0) + 1
    return [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def build_description(state: str, entries: list) -> str:
    n = len(entries)
    cities = unique_cities(entries)[:3]
    noun = "campground" if n == 1 else "campgrounds"
    text = f"{n} long-term stay {noun} and RV parks in {state}"
    if n == 1:
        text = f"1 long-term stay campground in {state}"
    if cities:
        text += f", including {join_list(cities)}" if n > 1 else f" ({cities[0]})"
    text += ". Compare full hookups, 50 amp electric and year-round availability."
    verified = sum(1 for e in entries if e.get("user_verified"))
    if verified and len(text) < 120:
        text += f" {verified} user-verified."
    if len(text) > 160:
        # Drop the city list rather than cut mid-word.
        text = (f"{n} long-term stay {noun} and RV parks in {state}. "
                "Compare full hookups, 50 amp electric and year-round availability.")
    return text


def build_seo_title(state: str) -> str:
    base = f"{state} Extended-Stay RV Parks & Campgrounds"
    full = f"{base} | {SITE_NAME}"
    return full if len(full) <= 65 else base


def existing_parts(path: str):
    """Return (front_matter_text, body_text) of an existing page, or (None, '')."""
    if not os.path.isfile(path):
        return None, ""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"\A\+\+\+\n(.*?)\n\+\+\+\n?(.*)\Z", text, re.S)
    if not m:
        return None, ""
    return m.group(1), m.group(2)


def render_state_page(state, entries, old_front, body, today):
    slug_list = sorted(e["slug"] for e in entries)
    digest = hashlib.sha1(
        json.dumps(sorted(entries, key=lambda e: e["slug"]), sort_keys=True).encode("utf-8")
    ).hexdigest()[:10]

    lastmod = today
    if old_front:
        old_hash = re.search(r'^data_hash = "([^"]*)"', old_front, re.M)
        old_mod = re.search(r'^lastmod = "([^"]*)"', old_front, re.M)
        if old_hash and old_mod and old_hash.group(1) == digest:
            lastmod = old_mod.group(1)

    aliases = ", ".join(toml_string(f"/campgrounds/{s}/") for s in slug_list)
    lines = [
        "+++",
        "draft = false",
        'layout = "state"',
        MARKER,
        f"title = {toml_string(f'{state} Extended-Stay Campgrounds & RV Parks')}",
        f"seo_title = {toml_string(build_seo_title(state))}",
        f"description = {toml_string(build_description(state, entries))}",
        f"state = {toml_string(state)}",
        f"state_abbr = {toml_string(STATE_ABBR.get(state, ''))}",
        f"campground_count = {len(entries)}",
        f'data_hash = "{digest}"',
        f'lastmod = "{lastmod}"',
        f"aliases = [{aliases}]",
        'sitemap = { changefreq = "weekly", priority = 0.8 }',
        "+++",
    ]
    body = body.strip("\n")
    return "\n".join(lines) + "\n" + (("\n" + body + "\n") if body else "")


def main():
    if not os.path.isfile(DATA_PATH):
        sys.exit(f"Data file not found: {DATA_PATH}")

    with open(DATA_PATH, encoding="utf-8") as f:
        campgrounds = json.load(f)
    if not isinstance(campgrounds, list):
        sys.exit("Expected data/campgrounds.json to be a flat JSON array of campground objects.")

    seen = set()
    by_state = {}
    for entry in campgrounds:
        slug = entry.get("slug")
        if not slug:
            sys.exit(f"Entry missing required 'slug' field: {entry.get('name', entry)}")
        if slug in seen:
            sys.exit(f"Duplicate slug '{slug}' in {DATA_PATH} -- slugs must be unique.")
        seen.add(slug)
        for field in ("name", "state", "location"):
            if not entry.get(field):
                sys.exit(f"Entry '{slug}' is missing required field '{field}'.")
        if entry["state"] not in STATE_ABBR:
            print(f"WARNING: unknown state '{entry['state']}' for '{slug}' "
                  "(add it to STATE_ABBR in this script).")
        if "lat" not in entry or "lon" not in entry:
            print(f"note: '{slug}' has no lat/lon -- it will be left out of radius searches.")
        by_state.setdefault(entry["state"], []).append(entry)

    state_slugs = {state_slug(s): s for s in by_state}
    clash = state_slugs.keys() & seen
    if clash:
        sys.exit(f"A state slug collides with a campground slug: {sorted(clash)}")

    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()

    for slug, state in sorted(state_slugs.items()):
        path = os.path.join(OUT_DIR, f"{slug}.md")
        old_front, body = existing_parts(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_state_page(state, by_state[state], old_front, body, today))
    print(f"Generated {len(state_slugs)} state page(s) in {OUT_DIR}")

    # Cleanup: legacy per-campground pages + generated state pages that are no longer needed.
    removed = []
    for fn in sorted(os.listdir(OUT_DIR)):
        if not fn.endswith(".md") or fn == "_index.md":
            continue
        stem = fn[:-3]
        path = os.path.join(OUT_DIR, fn)
        if stem in state_slugs:
            continue
        legacy = stem in seen
        with open(path, encoding="utf-8") as f:
            generated = MARKER in f.read()
        if legacy or generated:
            os.remove(path)
            removed.append(fn)
    if removed:
        print(f"Removed {len(removed)} obsolete page(s): {removed}")


if __name__ == "__main__":
    main()
