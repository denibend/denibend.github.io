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

## B2 — Age and sex structure, Albania vs EU27 (`data/b2_age_sex.csv`)
- Holds: Albania and EU27, 1990–2025, 1 January, by `sex` (Male/Female) × `age_band` (0-14, 15-24, 25-34, 35-44, 45-54, 55-64, 65-79, 80+), as `population` (people) and `share_of_total` (% of the entity's whole population, both sexes; each year sums to 100).
- Estimated by us: Albania 1990–2001 and EU27 1990–2000 use the UN WPP 2024 age shape × the official total (Eurostat has no age detail then; the brief named WPP for Albania only, so the EU27 also uses WPP's "EU 27" aggregate); Albania 2022 and 2024 interpolate shares between neighbouring years × the official total; EU27 2024's missing 30–34 and 45–49 cells are filled from the sex total.
- Also estimated: EU27 years 2014–2018 and 2020–2025, because Eurostat flags those aggregate cells as its own estimates.
- Break: Albania's levels for 2002–2023 rest on the 2011 census and from 2024 on the 2023 census (total −13%), while shares move under 1 pp at the break — compare shapes, not head counts. WPP's own Albanian levels run ~400k high, so they are not used.
- Missing: 2026 (not yet in demo_pjangroup). No age detail by sex exists in Eurostat for Albania before 2002.
