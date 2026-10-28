# Albania Part A — data briefs for Claude Code

Eight datasets for Tableau Public. Claude Code produces **data only**, no charts.

How to use this file:
1. Save this file in the repo at `studies/01-albania-beyond-the-headlines/BRIEFS.md`.
2. Add **Section 1** to the end of `CLAUDE.md` — edit the file on disk, don't paste it
   into the chat. Claude Code reads `CLAUDE.md` by itself at the start of every session,
   so the rules arrive for free, once, instead of being retyped in eight prompts.
3. Then one brief per session, and the whole prompt is one line:
   `Build B3.`
   That is enough: `CLAUDE.md` tells it who you are, how the repo is laid out, the data
   rules below, and where the briefs live. It opens this file, reads B3, ignores the rest.

---

## Section 1 — add to the end of CLAUDE.md

```markdown
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

After each brief, add 5 lines to the study README: what the CSV holds, what is
estimated, what is missing.

Token discipline: never print a dataframe, CSV contents, or more than 10 rows.
Report only: row count, year range, entities, number of estimated rows.
Do not re-read files you have already read in the session.
```

---

## Section 2 — the eight briefs

### B1 — Albanians by where they live, 1990–2026
Output: `data/b1_population_by_location.csv` — unit: people.
One row per (year, group). Groups: resident in Albania; Albanians in Italy, Greece,
Germany, UK, USA, rest of world; and separately foreign residents in Albania.
Sources, in order: INSTAT (resident population), UN DESA International Migrant Stock
(origin Albania by destination), Eurostat `migr_pop1ctz`, ISTAT, ELSTAT.
UN stock is five-yearly — interpolate between waves and mark `estimated` TRUE.

### B2 — Age and sex structure, Albania vs EU27
Output: `data/b2_age_sex.csv` — unit: people and share of total.
Rows: entity (Albania, EU27) × year × sex × age band (0–14, 15–24, 25–34, 35–44,
45–54, 55–64, 65–79, 80+). Full pyramid, not just the young bands.
Sources: Eurostat `demo_pjangroup`; UN World Population Prospects for Albanian years
Eurostat does not cover.

### B3 — GDP per person and remittances, Albania vs EU27
Output: `data/b3_gdp_remittances.csv` — unit: EUR per person, and % of GDP.
Measures: GDP per capita (EUR), remittances received (EUR), remittances as % of GDP.
Entities: Albania, EU27. Years 1990–2025 or latest.
Sources: World Bank `NY.GDP.PCAP.CD`, `BX.TRF.PWKR.CD.DT`; Eurostat for EU27.
Convert every USD figure with that year's ECB rate before writing.

### B4 — Corruption, several measures on one sheet
Output: `data/b4_corruption.csv`.
Three blocks in one long file:
- CPI score 2012–2025: Albania, EU27 average, and peers (Montenegro, North Macedonia,
  Serbia, Croatia, Greece).
- World Bank Worldwide Governance Indicators, control of corruption, same entities.
- Justice vetting outcomes as of Oct 2024: reviewed 798, dismissed 267, resigned 113
  (source: EU Delegation to Albania) — three rows, for a KPI tile.
Rescale each index to 0–100 in a separate `value_scaled` column so they share an axis.

### B5 — Prime ministers timeline, 1991–2026
Output: `data/b5_prime_ministers.csv` — hand-built, no API.
Columns: name, party, start_date, end_date, notable_event, source_url.
One row per term. This feeds a Gantt in Tableau, so dates must be real dates.
Verify every start and end date against two sources before writing it.

### B6 — What the pyramid schemes cost
Output: `data/b6_pyramid_losses.csv`.
Start from: savings lost ≈ USD 1.2bn, about half of 1996 GDP. Convert to 1997 EUR
(ECU rate), and give a second column in 2025 EUR.
Derive, each as its own row with the assumption written in a `note` column:
- loss per resident (1997 population)
- loss per household (census average household size)
- years of average work to earn it back (1997 GDP per capita, and average wage if found)
- two comparison rows, clearly marked `estimated` TRUE: the same amount expressed as
  a share of a named city's GDP today, and as a share of one listed company's revenue.
VEFA Holding is the largest single firm (59,005 creditors, ~45% of all claimants) —
add it as its own row if a figure for its debt exists; if not, say so and leave it out.

### B7 — Who works, who studies, who is retired — against remittances
Output: `data/b7_activity_vs_remittances.csv`.
Rows: year × category (employed, unemployed, in education, retired, other inactive),
as people and as share of population 15+. Plus two measures: compensation of employees
(EUR, national accounts) and remittances received (EUR).
Years 1990–2026, or the earliest year each series starts.
Sources: INSTAT labour force survey, ILOSTAT, Eurostat, UNESCO UIS (students),
Albanian Social Insurance Institute (pensioners), World Bank (remittances).
Add a `correlation` note in the README: do remittances fall as the wage bill rises,
and from which year. Report the coefficient, do not chart it.

### B8 — Businesses, and how much of it is the beach
Output: `data/b8_business_structure.csv` — unit: number of active enterprises.
Rows: year × NACE group × region.
"Beach management" is not a NACE class. Use this proxy and label it as a proxy:
accommodation (I55), food and beverage (I56), sports and recreation (R93), restricted
to the coastal prefectures Vlorë, Durrës, Lezhë, Fier. Everything else is the base.
Source: INSTAT statistical business register. The register does not go back to 1990 —
start where it starts, and write the first available year in the README.

---

## Note on Substack

Tableau Public gives you an embed iframe. Substack strips most third-party iframes, and
nothing interactive survives the email version. Check this before you build around it.
The usual fallback is a static image in the post, linked to the live Tableau viz.
