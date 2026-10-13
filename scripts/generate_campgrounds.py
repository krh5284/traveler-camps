#!/usr/bin/env python3
"""
Generates one Hugo content page per campground from data/campgrounds.json.

Usage (run from the Hugo project root):
    python3 scripts/generate_campgrounds.py

Source of truth is data/campgrounds.json. Edit that file (or script your own
tooling to append to it) and re-run this to create/update the pages in
content/campgrounds/. Existing pages are overwritten, so don't hand-edit
files in content/campgrounds/ directly -- edit the JSON instead.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "campgrounds.json")
OUT_DIR = os.path.join(ROOT, "content", "campgrounds")


def toml_string(value: str) -> str:
    """Render a Python string as a valid TOML basic (double-quoted) string."""
    value = value or ""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def toml_bool(value) -> str:
    return "true" if value else "false"


def render_page(entry: dict) -> str:
    name = entry["name"]
    state = entry["state"]
    location = entry.get("location", "")
    website = entry.get("website", "")
    google_url = entry.get("google_reviews_url", "")
    rvlife_url = entry.get("rvlife_url", "")

    front_matter_lines = [
        "+++",
        "draft = false",
        f"title = {toml_string(f'{state} - {name}')}",
        f"state = {toml_string(state)}",
        f"location = {toml_string(location)}",
        f"website = {toml_string(website)}",
        f"google_reviews_url = {toml_string(google_url)}",
        f"rvlife_url = {toml_string(rvlife_url)}",
        f"user_verified = {toml_bool(entry.get('user_verified'))}",
        f"full_hookups = {toml_bool(entry.get('full_hookups'))}",
        f"amp_50_electric = {toml_bool(entry.get('amp_50_electric'))}",
        f"open_year_round = {toml_bool(entry.get('open_year_round'))}",
        "+++",
        "",
    ]

    body_lines = []
    if website:
        body_lines.append(f"Website - <{website}>")
        body_lines.append("")
    if google_url:
        body_lines.append(f"[Reviews on Google]({google_url})")
        body_lines.append("")
    if rvlife_url:
        body_lines.append(f"[RV Life Page]({rvlife_url})")
        body_lines.append("")

    keywords = []
    if entry.get("user_verified"):
        keywords.append("User Verified")
    if entry.get("full_hookups"):
        keywords.append("Full Hookups")
    if entry.get("amp_50_electric"):
        keywords.append("50 Amp Electric")
    if entry.get("open_year_round"):
        keywords.append("Open Year-round")

    if keywords:
        body_lines.append("{{< keywordList >}}")
        for kw in keywords:
            body_lines.append(f'{{{{< keyword icon="check" >}}}} {kw} {{{{< /keyword >}}}}')
        body_lines.append("{{< /keywordList >}}")

    return "\n".join(front_matter_lines + body_lines) + "\n"


def main():
    if not os.path.isfile(DATA_PATH):
        sys.exit(f"Data file not found: {DATA_PATH}")

    with open(DATA_PATH, encoding="utf-8") as f:
        campgrounds = json.load(f)

    if not isinstance(campgrounds, list):
        sys.exit("Expected data/campgrounds.json to be a flat JSON array of campground objects.")

    seen_slugs = set()
    os.makedirs(OUT_DIR, exist_ok=True)

    for entry in campgrounds:
        slug = entry.get("slug")
        if not slug:
            sys.exit(f"Entry missing required 'slug' field: {entry.get('name', entry)}")
        if slug in seen_slugs:
            sys.exit(f"Duplicate slug '{slug}' in {DATA_PATH} -- slugs must be unique.")
        seen_slugs.add(slug)

        out_path = os.path.join(OUT_DIR, f"{slug}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(render_page(entry))

    print(f"Generated {len(seen_slugs)} campground page(s) in {OUT_DIR}")

    # Clean up stale pages for campgrounds removed from the JSON
    existing = {
        fn for fn in os.listdir(OUT_DIR)
        if fn.endswith(".md") and fn != "_index.md"
    }
    expected = {f"{slug}.md" for slug in seen_slugs}
    stale = existing - expected
    for fn in stale:
        os.remove(os.path.join(OUT_DIR, fn))
    if stale:
        print(f"Removed {len(stale)} stale page(s) no longer in the JSON: {sorted(stale)}")


if __name__ == "__main__":
    main()
