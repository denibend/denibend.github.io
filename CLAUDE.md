# CLAUDE.md — operating notes for Claude Code

## Project
Public research portfolio by Denisa Bendaj (GitHub: `denibend`). Target: one study every 1–2 weeks,
each with (A) a professional research report and (B) an interactive dashboard, published on
GitHub Pages at https://denibend.github.io (repo `denibend/denibend.github.io`).

Roles: Claude implements, tests and explains; Denisa sets direction, interprets results and approves
publication. She is a senior BI/commercial analyst (SQL, Power BI, statistics) who is new to Python and
Git, so explain code through SQL/Power BI analogies and don't teach analytics basics.

## Approval required before
Pushing to GitHub, creating/altering public repos or Pages settings, publishing conclusions,
deleting/overwriting important files, paid tools, major architectural changes,
sending private data externally. Everything else in scope: just do it and explain afterwards.

## Architecture
- Python 3.13 managed by `uv` (`pyproject.toml` + `uv.lock`). Run everything via `uv run ...`.
- Dashboards: Plotly figures rendered into static HTML (Jinja2 templates), served from `docs/` by
  GitHub Pages (branch `main`, folder `/docs`). No server, no CI yet.
- One folder per study in `studies/<slug>/`:
  `fetch.py` (acquisition) → `analysis.py` (pure calculations, tested) → `charts.py` (figures)
  → `build.py` (writes `docs/studies/<slug>/`). Each study has its own README.md.
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
