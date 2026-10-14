# Campgrounds: new data-driven workflow

## What changed

**`data/campgrounds.json`** is now the single source of truth — a flat JSON
array, one object per campground:

```json
{
  "slug": "boise-riverside-rv-park",
  "name": "Boise Riverside RV Park",
  "state": "Idaho",
  "location": "Boise",
  "website": "https://...",
  "google_reviews_url": "https://...",
  "rvlife_url": "https://...",
  "user_verified": true,
  "full_hookups": true,
  "amp_50_electric": true,
  "open_year_round": true
}
```

It was rebuilt from your 32 existing `.md` pages (kept as the source of
truth for name/state/website/URLs/amenities, since that's your hand-checked
content) merged with the extra fields (`location`, `user_verified`) from
your `campgrounds.yml` / `campground2.yml` / `campgrounds3.yml` drafts. All
32 matched up cleanly with no gaps.

Your old `data/campgrounds.json` had two syntax errors (a trailing comma
after Colorado's entry, a missing comma before `"Missouri"`) so it couldn't
even parse — that's fixed as part of the rebuild. The three `.yml`
fragments are now fully absorbed into the new JSON and can be deleted.

**`scripts/generate_campgrounds.py`** generates every page in
`content/campgrounds/` from that JSON. Run it from the project root:

```bash
python3 scripts/generate_campgrounds.py
```

To add a new campground going forward: append one object to
`data/campgrounds.json`, re-run the script, done — no more hand-typing a
`.md` file with front matter and shortcodes. The script also deletes any
`.md` page whose slug is no longer in the JSON, so removing a campground is
just as simple.

**`content/campgrounds/_index.md`** no longer has a hand-maintained
accordion listing every state and campground by hand. It now just calls:

```
{{< campground-finder >}}
```

**`layouts/shortcodes/campground-finder.html`** is the new search/filter
UI. It reads `.Site.Data.campgrounds` (Hugo auto-loads any `data/*.json`
file) directly, so it always reflects the current JSON with no separate
build step. It renders:
- a text search box (matches name or city)
- a state dropdown
- checkboxes for Full Hookups / 50 Amp / Open Year-round
- a card grid that filters live in the browser (plain JS, no dependencies)

This is in addition to — not a replacement for — Blowfish's built-in
`enableSearch` full-text search, which still works for finding campgrounds
by name/content sitewide.

## What to do with these files

1. Drop `data/campgrounds.json` into your project, replacing the old one.
2. Delete `data/campgrounds.yml`, `data/campground2.yml`,
   `data/campgrounds3.yml` — fully superseded.
3. Add `scripts/generate_campgrounds.py`.
4. Replace `content/campgrounds/_index.md` with the version here.
5. Add `layouts/shortcodes/campground-finder.html`.
6. Replace all 32 files in `content/campgrounds/` with the regenerated
   versions here (byte-for-byte same rendered content, plus the new
   structured front matter).
7. Run `hugo server` and check `/campgrounds/` — I wasn't able to run a
   test build in this environment (no `hugo` binary, no network), so
   please sanity-check the filter UI and a couple of individual pages
   before deploying.

## Known gaps / things to double check

- `location` (city) wasn't present in your `.md` files at all — it only
  existed in the `.yml` drafts. All 32 matched by name, but if you rename a
  campground in the JSON going forward, double check the `location` field
  didn't get orphaned.
- The finder shortcode's checkboxes are AND'd together (e.g. checking both
  "Full Hookups" and "50 Amp" shows only campgrounds with both) — let me
  know if you'd rather have OR logic for amenities.
- If your amenity list grows beyond these three flags, the shortcode and
  JSON schema will need a small extension (happy to do that whenever you're
  ready).

## Radius search ("near a town")

The campground finder can filter by distance from any US town. One-time setup, from the project root:

1. `python3 scripts/build_us_places.py` — downloads the Census gazetteer and writes `static/data/us-places.json` (town lookup, loaded only when a visitor uses the location box). Committing that file is optional: the GitHub Pages workflow runs the same script during deploy whenever the file isn't in the repo. You still need to run it locally once if you want `add_coordinates.py` or a local `hugo server` preview to use the town list.
2. `python3 scripts/add_coordinates.py --dry-run`, then without `--dry-run` — fills `lat`/`lon` in `data/campgrounds.json` from town centers. Anything it can't match is listed; add those by hand. To use exact campground pins, overwrite `lat`/`lon` with coordinates from Google Maps (the script never overwrites existing values).
3. New campgrounds: include `"lat"` and `"lon"` in the JSON object. Campgrounds without them still appear in normal searches but are left out of radius results.
