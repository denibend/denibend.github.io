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
The briefs are in studies/2026-11-albania-crossroads/BRIEFS.md. A request like "Build B3"
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

After each brief, add 5 lines to the study README: what the CSV holds, what is
estimated, what is missing.

Token discipline: never print a dataframe, CSV contents, or more than 10 rows.
Report only: row count, year range, entities, number of estimated rows.
Do not re-read files you have already read in the session.
