# Campgrounds: data-driven workflow

## How the site is structured

**`data/campgrounds.json`** is the single source of truth: a flat JSON array, one object per campground.

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
  "open_year_round": true,
  "lat": 43.6,
  "lon": -116.2
}
```

There are **no individual campground pages**. Instead:

| URL | What it is |
| --- | --- |
| `/campgrounds/` | Search page. Every campground is a card showing all of its data (name, city, state, badges, website, Google reviews, RV Life, map/directions). Each card links to its entry on the state page. |
| `/campgrounds/<state>/` (e.g. `/campgrounds/idaho/`) | One page per state: intro, at-a-glance table, and a full entry for every campground in that state (`#<slug>` anchors). |
| `/campgrounds/<old-slug>/` | Old individual URLs. They still exist as tiny redirects to the state page (Hugo `aliases`) so old links and Google's index don't 404. |

### Adding, editing or removing a campground

1. Edit `data/campgrounds.json` (add/change/remove an object).
2. Run `python3 scripts/generate_campgrounds.py` from the project root.
3. Commit. (The GitHub Actions workflow also runs the script before building, so a forgotten run can't leave the site stale.)

The script writes `content/campgrounds/<state>.md` for every state in the JSON. The state page *content* is rendered from the JSON by `layouts/_default/state.html`, so the `.md` file is just front matter: unique title, meta description, redirect aliases and a `lastmod` that only changes when that state's data changes.

It also deletes the old one-page-per-campground files and any generated state page whose state no longer has campgrounds.

**Hand-written state copy:** anything you type *below* the closing `+++` in a state `.md` file is kept on re-runs and shown as an intro on that state's page. Adding a few unique sentences per state (best time to visit, long-stay tips, local rules you've learned) is the best long-term SEO improvement you can make.

### Required fields

`slug`, `name`, `state` (full name, e.g. "Idaho"), `location` (city). Everything else is optional and skipped gracefully if missing. New states need no setup; the script knows all 50 states + DC + PR.

## SEO features

- Unique `<title>` and meta description on every page; canonical URLs; `robots` meta (404 is `noindex`).
- Open Graph / Twitter cards with a default share image (`assets/img/og-default.png`, placeholder, replace with your own 1200x630 image).
- JSON-LD structured data: `Organization` + `WebSite` (home), `CollectionPage` + `ItemList` of `Campground` (state pages), `BreadcrumbList` everywhere. See `layouts/partials/schema.html`. Coordinates are deliberately not emitted (see "Radius search").
- Crawlable internal links: home page, search page, every state page and the site footer link to all state pages.
- Sitemap with real `lastmod` values; empty tag/category archives are disabled.
- Favicons + web manifest in `static/` (placeholders, replace as you like).
- Google Analytics only loads in production builds.

After deploying, submit `<your-site>/sitemap.xml` in Google Search Console and Bing Webmaster Tools. If you use a custom domain, update `baseURL` in `config/_default/hugo.toml` and `hugo.yml`, and add the verification code under `[verification]` in `config/_default/params.toml`.

## Radius search ("near a town")

The campground finder can filter by distance from any US town. One-time setup, from the project root:

1. `python3 scripts/build_us_places.py` downloads the Census gazetteer and writes `static/data/us-places.json` (town lookup, loaded only when a visitor uses the location box). Committing that file is optional: the GitHub Pages workflow runs the same script during deploy whenever the file isn't in the repo.
2. `python3 scripts/add_coordinates.py --dry-run`, then without `--dry-run`, fills `lat`/`lon` in `data/campgrounds.json` from town centers. Anything it can't match is listed; add those by hand. To use exact campground pins, overwrite `lat`/`lon` with coordinates from Google Maps (the script never overwrites existing values).
3. New campgrounds: include `"lat"` and `"lon"` in the JSON object. Campgrounds without them still appear in normal searches but are left out of radius results.

Because many coordinates are town centers, distances shown on cards are approximate ("About 12 mi away"), and the "Map & directions" link searches by name + city + state rather than by coordinates.

## Styling note

The Blowfish theme ships a pre-compiled Tailwind stylesheet, so new Tailwind utility classes in project templates won't work unless the theme CSS is rebuilt. The finder, cards and state pages therefore use their own `.tc-*` classes in `assets/css/custom.css`.
