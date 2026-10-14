#!/usr/bin/env python3
"""
Fills in missing "lat" / "lon" on each entry in data/campgrounds.json using the
town lookup built by scripts/build_us_places.py (static/data/us-places.json).

These are TOWN-CENTER coordinates, good enough for radius search. For exact
campground pins, overwrite lat/lon by hand (right-click the spot in Google Maps
and click the coordinates to copy them). Entries that already have lat/lon are
never touched.

Usage (from the Hugo project root):
    python3 scripts/add_coordinates.py --dry-run   # preview only
    python3 scripts/add_coordinates.py             # write changes
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "campgrounds.json")
PLACES_PATH = os.path.join(ROOT, "static", "data", "us-places.json")

STATES = {
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


def lookup(places_by_state: dict, town: str, abbr: str):
    """Exact name match, else a single prefix match ("Boise" -> "Boise City")."""
    candidates = places_by_state.get(abbr, [])
    t = town.strip().lower()
    for name, lat, lon in candidates:
        if name.lower() == t:
            return (lat, lon), None
    starts = [(n, la, lo) for n, la, lo in candidates if n.lower().startswith(t + " ")]
    if len(starts) == 1:
        return (starts[0][1], starts[0][2]), f'matched "{starts[0][0]}"'
    if len(starts) > 1:
        return None, "ambiguous: " + ", ".join(n for n, _, _ in starts[:5])
    return None, "no match"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(PLACES_PATH):
        print("Missing static/data/us-places.json -- run scripts/build_us_places.py first.")
        return 1

    with open(PLACES_PATH, encoding="utf-8") as f:
        places = json.load(f)
    by_state: dict = {}
    for name, st, lat, lon in places:
        by_state.setdefault(st, []).append((name, lat, lon))

    with open(DATA_PATH, encoding="utf-8") as f:
        campgrounds = json.load(f)

    filled, skipped, problems = 0, 0, []
    out = []
    for entry in campgrounds:
        if entry.get("lat") is not None and entry.get("lon") is not None:
            skipped += 1
            out.append(entry)
            continue
        abbr = STATES.get(entry.get("state", ""))
        town = entry.get("location", "")
        result, note = (None, "no state/location") if not (abbr and town) else lookup(by_state, town, abbr)
        if result is None:
            problems.append(f'  {entry["name"]} ({town}, {entry.get("state")}): {note}')
            out.append(entry)
            continue
        # keep lat/lon right after "location" so the JSON stays readable
        new_entry = {}
        for k, v in entry.items():
            new_entry[k] = v
            if k == "location":
                new_entry["lat"], new_entry["lon"] = result
        if "lat" not in new_entry:
            new_entry["lat"], new_entry["lon"] = result
        out.append(new_entry)
        filled += 1
        if note:
            print(f'  {entry["name"]}: {note}')

    print(f"Filled {filled}, already had coordinates {skipped}, unresolved {len(problems)}")
    if problems:
        print("Fill these in by hand:")
        print("\n".join(problems))

    if args.dry_run:
        print("(dry run -- nothing written)")
        return 0
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Updated data/campgrounds.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
