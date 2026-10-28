# CLAUDE.md — operating notes for Claude Code

## Project
Public research portfolio by Denisa Bendaj (GitHub: `denibend`). Target: one study every 1–2 weeks,
each with (A) a professional research report and (B) an interactive dashboard, published on
GitHub Pages at https://denibend.github.io (repo `denibend/denibend.github.io`).

Roles: Claude implements, tests and explains; Denisa sets direction, interprets results and approves
publication. She is a senior BI/commercial analyst (SQL, Power BI, statistics) who is new to Python and
Git, so explain code through SQL/Power BI analogies and don't teach analytics basics.

## Approval required before
Making the repo public or changing Pages settings, publishing conclusions,
deleting/overwriting important files, paid tools, major architectural changes,
sending private data externally, force-push/history rewrites. Everything else in scope: just do it and
explain afterwards. The repo is **public** since 2026-10-23 and every push to `main`
updates the live site, so ask before each push (the earlier standing approval covered the private phase only).

## Architecture
- Python 3.13 managed by `uv` (`pyproject.toml` + `uv.lock`). Run everything via `uv run ...`.
- Dashboards: Plotly figures rendered into static HTML (Jinja2 templates), served from `docs/` by
  GitHub Pages (branch `main`, folder `/docs`). No server, no CI yet.
- One folder per study in `studies/<slug>/`:
  `fetch.py` (acquisition) → `analysis.py` (pure calculations, tested) → `charts.py` (figures)
  → `build.py` (writes `docs/studies/<slug>/index.html` = report, `dashboard.html` = dashboard).
  Each study has its own README.md. Templates live in `studies/<slug>/templates/`.
- Exception: `studies/01-albania-beyond-the-headlines/` is data-only for Tableau Public (no report or
  dashboard in `docs/`). Layout (decided 2026-10-28; WORKFLOW.md's `articles/` layout rejected):
  `src/bN.py` (one script per analysis) → `data/bN_*.csv` (one CSV per analysis) in a shared
  `data/` with `data/sources.csv` and git-ignored `data/raw/bN_*`; one `README.md` for the study;
  `tableau/` (per dashboard: a spec + `BUILD.md` steps; mockups git-ignored); `viz/index.html`
  (review page, the only place charts are allowed). Run
  `uv run python studies/01-albania-beyond-the-headlines/src/bN.py [--refresh]`.
  See "Albania study" below.
- `docs/assets/site.css` is the shared, hand-maintained stylesheet; `docs/index.html` is the hand-written
  landing page. Everything else under `docs/studies/` is generated, so edit templates, not output.
- Preview locally with `uv run python -m http.server 8765 --directory docs` (relative links need a server).
- Review rendered pages (headless Chrome screenshot) and check every number in the text against the
  computed results; inject numbers from build.py rather than typing them into templates.
- No shared library until a second study genuinely reuses code; then create `src/`/`common/` and refactor.

## Conventions
- Keep acquisition, calculation and visualization separate; calculation functions take/return DataFrames
  and do no I/O, so they can be tested.
- Analyse returns or changes, not price levels, unless levels are explicitly justified.
- Type hints on public functions; ruff formatting (`uv run ruff format`, `uv run ruff check`).
- Tests in `tests/` with pytest (`uv run pytest`); test every statistical calculation on synthetic data
  with a known answer.

## Data rules
- Record for each dataset: source, retrieval date, period, frequency, units, adjustments, licence.
- Raw downloads go to `studies/<slug>/data/raw/` (git-ignored). Do not commit or publish raw
  restricted data (e.g. Yahoo Finance prices); publish derived statistics and charts.
- API keys only in `.env` (git-ignored); `.env.example` documents the variable names.
- No employer/confidential data, ever.

## Environment notes (macOS, Apple Silicon)
- `uv` and `gh` live in `~/.local/bin` (no Homebrew). If not on PATH in a tool shell, prefix
  `export PATH="$HOME/.local/bin:$PATH"`.
- Git comes from Xcode Command Line Tools. Commit identity uses the GitHub noreply email.

## Status
See ROADMAP.md for current objectives, backlog and decisions.

## Albania study — data rules
The briefs are in studies/01-albania-beyond-the-headlines/BRIEFS.md. A request like "Build B3"
means: open that file, read brief B3 only, and follow the rules here. Do not read the
other briefs.

Currency: all money in EUR, nominal, at that year's average exchange rate
(ECB reference rate; before 1999 use the ECU rate). Never publish USD figures.

Benchmark: EU27 average whenever a brief asks for a comparison.

Output per brief: one tidy CSV in the study's data/ folder, long format:
  entity, year, measure, value, unit, estimated, source_id
Plus data/sources.csv: source_id, name, url, licence, downloaded_utc.

estimated = TRUE for any interpolated, modelled or proxied point. Never fill a gap
silently. If a series does not exist, build the best available and say so.

Code: one script per brief, src/<brief_id>.py, run with uv.
Download -> cache in data/raw/ -> compute -> write CSV. Keep the three steps separate.

Do not build charts. No Plotly, no HTML, no images. Tableau Public does the visuals.
(Exception, decided 2026-10-28: the study's `viz/index.html` review page.)

After each brief, add 5 lines to the study README: what the CSV holds, what is
estimated, what is missing.

Token discipline: never print a dataframe, CSV contents, or more than 10 rows.
Report only: row count, year range, entities, number of estimated rows.
Do not re-read files you have already read in the session.

### Albania study — conventions settled while building B1–B3
- Each `src/bN.py` is self-contained: `download()` (skips files already in `data/raw/` + its
  `bN_manifest.json`; `--refresh` re-fetches) → `load()` → `build()` (pure, no I/O) → `write()`.
  `write()` upserts its rows into the shared `data/sources.csv` by `source_id`.
- Tests: `tests/test_albania_bN.py`, loading the script by file path (the folder name has hyphens,
  so it cannot be imported). Test every fill/interpolation/conversion on synthetic data.
- Extra columns are allowed when a brief needs another dimension; put them after `year`.
  A derived point lists every input: `source_id` = `a;b`.
- When a Tableau spec in `tableau/` asks for it, the brief's CSV is shaped for that view instead
  of `measure, value, unit` (B2: `age_order`, `population`, `pct_of_total`, `pct_signed`).
  Shares meant to add to 100 use largest-remainder rounding so they add to exactly 100.0.
- Third-party mockups stay local (`**/tableau/mockup*.png` is git-ignored): never publish them.
- `estimated` = TRUE for our gap-filling and for values the provider flags as estimated
  (Eurostat flag `e`). Report the README "Estimated" line split into the two kinds.
- If a brief's named source measures a different concept, use a comparable one and say why in the
  README (B3: Eurostat's EU27 remittances count extra-EU inflows only → World Bank EU sum used).
- Albania 2023 census break: from 1 Jan 2024 INSTAT/Eurostat population is on the 2023-census basis,
  2012–2023 are not back-revised (total −13% in one year). Flag it in every brief that uses Albanian
  population levels; B1 carries a `people_by_location_census_adjusted` measure for that.
- Source access notes:
  - INSTAT PxWeb (databaza.instat.gov.al) does not connect from here; Eurostat republishes INSTAT
    series (demo_gind, demo_pjangroup) — use those and name INSTAT in the source `name`.
  - un.org pages refuse the default client: send a browser-like User-Agent. The UN WPP server is
    very slow (30 MB took several retries): stream with a long timeout and resume with `curl -C -`.
  - UN Migrant Stock 2024 has no Albania-origin rows for Germany, UK, USA; the 2020 edition does.
  - UN WPP Albania levels predate the 2023 census (~400k high): use WPP for shapes, not levels.
  - Eurostat `bop_rem` is withdrawn; personal remittances are in `bop_rem6` (item R1).
  - World Bank API covers ALB and the EU aggregate `EUU` to 2025 (last updated 2026-10-08).
- Map data (B13): Tableau's spatial-file connector does not read GeoPackage, so maps are written
  as RFC 7946 GeoJSON (WGS84, 6 decimals) in `data/bN_*.geojson`; source `.gpkg` stays in raw/.
  Measure areas in an equal-area CRS (EPSG:3035), never in Web Mercator. Kontur Population
  totals are pre-2023-census (~2.84M vs 2.39M): use for spatial pattern, not levels.
- Status: B1, B2, B3 done and pushed (2026-10-25 to 2026-10-28); B2 reshaped for Tableau with
  `tableau/B2-TABLEAU-SPEC.md` + `BUILD.md`. B13 (Kontur hexagon map data) built 2026-10-28.
  B4–B8 and `viz/index.html` to do.
