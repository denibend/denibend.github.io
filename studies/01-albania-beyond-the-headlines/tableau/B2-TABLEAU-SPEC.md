# B2 — Tableau spec (as built)

What `data/b2_age_sex.csv` contains, shaped for the Tableau Public dashboard. The mockup
(`tableau/mockup-b2.png`) shows the look and feel, not the content. It is a third-party design,
so it is kept locally and git-ignored, not published in this repo.

B2 supplies the population pyramids at the bottom of that mockup and the female/male share
line beside them. The other panels belong to other briefs.
Build steps: [BUILD.md](BUILD.md).

---

## The file
`data/b2_age_sex.csv` — one row per entity × year × sex × age band. No pre-pivoted layout:
Tableau does the pivoting. This is the one Albania file that is not in the long
`measure, value, unit` layout, so the pyramid needs no pivot and no calculated field.

| Column | Type | Notes |
|---|---|---|
| `entity` | text | `Albania` or `EU27` (EU27_2020: the 27 member states from 2020, for every year) |
| `year` | integer | 1990 to 2025 (1 January) |
| `sex` | text | `Female` or `Male` |
| `age_band` | text | `0-14`, `15-24`, `25-34`, `35-44`, `45-54`, `55-64`, `65-79`, `80+` |
| `age_order` | integer | 1 for `0-14` … 8 for `80+`. Tableau sorts text alphabetically, so the pyramid needs this |
| `population` | integer | people in that band |
| `pct_of_total` | decimal, 1 dp | that band and sex as a share of the entity's **total population of both sexes** that year. All 16 rows of an entity-year sum to exactly 100.0 (largest-remainder rounding) |
| `pct_signed` | decimal, 1 dp | same number, **negative for Female**, positive for Male. This is what makes the butterfly work with no calculated field |
| `estimated` | TRUE/FALSE | TRUE for any interpolated or modelled value, and for values Eurostat flags as estimated |
| `source_id` | text | joins to `data/sources.csv`; `a;b` when a value combines two sources |

Female is negative because the mockup puts female on the left.

## Rules
- Eight age bands, as listed. They follow the brief (BRIEFS.md, B2), not the ten-year bands in
  the mockup. Eurostat publishes five-year groups; they are summed into these bands.
  The bands are not all the same width: `0-14` and `65-79` cover 15 years, `80+` is open-ended,
  the rest cover 10. Those bars are longer partly because the band is wider.
- `pct_of_total` is the share of the **whole** population, not of that sex: the two sides of
  one pyramid together make 100%.
- Every year from 1990 to 2025 is included, not only the four in the mockup. Filter in Tableau.
- EU27 is Eurostat's own EU27_2020 aggregate (a weighted total across member states, not an
  average of national shares). For 1990–2000, which Eurostat does not break down by age, the
  shape comes from UN WPP's "EU 27" aggregate, scaled to Eurostat's total.
- Sources: Eurostat `demo_pjangroup` first; UN World Population Prospects 2024 for the years
  Eurostat does not cover (Albania 1990–2001, EU27 1990–2000); Albania 2022 and 2024 are
  interpolated. All of those rows are `estimated` TRUE. Details in the study README.

## Do not
Build charts, except in the study's `viz/index.html` review page. No Plotly in the Tableau
pack, no images, no .twb file.
