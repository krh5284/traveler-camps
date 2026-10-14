#!/usr/bin/env python3
"""
Builds static/data/us-places.json, the town lookup used by the campground
finder's "near a town" radius search.

Source: US Census Bureau Gazetteer files (public domain)
  - Places (cities, towns, villages, boroughs, CDPs)
  - County subdivisions (townships, New England towns, etc.) -- needed because
    many places people camp near (e.g. NJ/PA townships) are not Census "places".

Usage (run from the Hugo project root, needs internet once):
    python3 scripts/build_us_places.py

Offline / already downloaded the files?
    python3 scripts/build_us_places.py --places path/to/places.zip --cousubs path/to/cousubs.zip
(.zip or the extracted .txt both work.)

If the Census changes the year in the URL, update the two URLs below or pass
the files in by hand from https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html

Output format: [[name, "ST", lat, lon], ...] sorted by name. When two entries
share the same name + state, the Census "place" wins over a county subdivision,
then the larger land area wins.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "static", "data", "us-places.json")

BASE = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/"
PLACES_URL = BASE + "2023_Gaz_place_national.zip"
COUSUBS_URL = BASE + "2023_Gaz_cousubs_national.zip"

# Longest first so "city and borough" wins over "city".
SUFFIXES = [
    "consolidated government", "metropolitan government", "metro government",
    "unified government", "urban county", "city and borough",
    "zona urbana", "municipality", "plantation", "comunidad", "township",
    "borough", "village", "town", "city", "cdp", "charter township",
    "gore", "grant", "location", "purchase", "reservation",
]
SUFFIXES.sort(key=len, reverse=True)


def clean_name(raw: str) -> str:
    name = re.sub(r"\s*\((balance|pt\.)\)\s*$", "", raw.strip(), flags=re.I)
    low = name.lower()
    for suf in SUFFIXES:
        if low.endswith(" " + suf):
            name = name[: -(len(suf) + 1)]
            break
    return name.strip()


def read_table(path_or_url: str) -> list:
    if path_or_url.startswith("http"):
        print(f"Downloading {path_or_url}")
        req = urllib.request.Request(path_or_url, headers={"User-Agent": "traveler-camps-build"})
        data = urllib.request.urlopen(req, timeout=120).read()
    else:
        with open(path_or_url, "rb") as f:
            data = f.read()

    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            member = next(n for n in zf.namelist() if n.lower().endswith(".txt"))
            data = zf.read(member)

    text = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    reader.fieldnames = [h.strip() for h in reader.fieldnames]
    return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in reader]


def collect(rows: list, priority: int, best: dict) -> int:
    added = 0
    for row in rows:
        raw = row.get("NAME", "")
        if not raw or raw.lower().startswith("county subdivisions not defined"):
            continue
        try:
            lat = float(row["INTPTLAT"])
            lon = float(row["INTPTLONG"])
            land = float(row.get("ALAND_SQMI") or 0)
        except (KeyError, ValueError):
            continue
        name = clean_name(raw)
        state = row["USPS"]
        key = (name.lower(), state)
        # lower priority number wins; then bigger land area
        rank = (priority, -land)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, [name, state, round(lat, 3), round(lon, 3)])
            added += 1
    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--places", default=PLACES_URL)
    ap.add_argument("--cousubs", default=COUSUBS_URL)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    best: dict = {}
    collect(read_table(args.places), 0, best)
    collect(read_table(args.cousubs), 1, best)

    out = sorted((v[1] for v in best.values()), key=lambda r: (r[0].lower(), r[1]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    size_kb = os.path.getsize(args.out) / 1024
    print(f"Wrote {len(out):,} places to {os.path.relpath(args.out, ROOT)} ({size_kb:,.0f} KB uncompressed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
