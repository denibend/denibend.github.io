# Albania at a crossroads — data for Tableau Public

Data only: one tidy CSV per brief in `data/`, sources in `data/sources.csv`, one script per
brief in `src/` (`uv run python studies/2026-11-albania-crossroads/src/<brief>.py`).
Briefs: [BRIEFS.md](BRIEFS.md). Raw downloads are cached in `data/raw/` (git-ignored).

## B1 — Albanians by where they live (`data/b1_population_by_location.csv`)
- Holds: people per year 1990–2026 for resident in Albania (INSTAT, 1 Jan, via Eurostat), Albania-born in Italy, Greece, Germany, UK, USA and rest of world (UN migrant stock, mid-year; measure `people_by_location`), plus foreign-born residents in Albania (measure `foreign_born_residents` — a subset of residents, do not stack it).
- Estimated: every non-wave year abroad (UN waves 1990/95/2000/05/10/15/20/24, linear in between); after the last wave Italy follows Eurostat born-in-Albania counts, Germany follows Eurostat Albanian-citizen counts, all others are held flat (UK, USA from 2021; Greece, rest of world, foreign-born from 2025).
- Break: official resident population drops 13.4% in 2024 because the 2023 census reset INSTAT's series and 2012–2023 are not back-revised — not one year's emigration. Measure `people_by_location_census_adjusted` repeats the stack with that ~340k gap spread linearly over 2013–2023 (estimated; equals official in 2012 and from 2024). Use one measure, never both.
- Missing/weak: the UN 2024 edition has no Albania-origin rows for Germany, UK, USA, so those use the 2020 edition (to 2020); UK is likely undercounted (no post-2020 source); INSTAT's own database and ISTAT/ELSTAT were not queried directly — their data arrive through Eurostat.
- Concept: "Albanians abroad" = born in Albania, so it excludes children born abroad and ethnic Albanians from Kosovo/North Macedonia; resident is 1 January, abroad is mid-year.
