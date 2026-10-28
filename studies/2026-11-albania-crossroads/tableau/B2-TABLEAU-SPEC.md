# B2 — Tableau spec

Paste the block below to Claude Code. The mockup is `tableau/mockup-b2.png` in this folder —
it is the look and feel, not the content.

---

## Instruction for Claude Code

Build B2 to feed a Tableau Public dashboard. The mockup is at
`studies/2026-11-albania-crossroads/tableau/mockup-b2.png` — open it before you start.
B2 supplies the population pyramids at the bottom of that mockup and the female/male share
line beside them. The other panels belong to other briefs; do not build them here.

### The file
`data/b2_age_sex.csv` — one row per entity × year × sex × age band. No wide columns,
no pre-pivoted layout: Tableau does the pivoting.

| Column | Type | Notes |
|---|---|---|
| `entity` | text | `Albania` or `EU27` |
| `year` | integer | 1990 to the latest year available |
| `sex` | text | `female` or `male`, lowercase |
| `age_band` | text | `0 to 9`, `10 to 19`, `20 to 29`, `30 to 39`, `40 to 49`, `50 to 59`, `60 to 69`, `70+` |
| `age_order` | integer | 1 for `0 to 9` … 8 for `70+`. Tableau sorts text alphabetically, so the pyramid needs this |
| `population` | integer | people in that band |
| `pct_of_total` | decimal, 1 dp | that band and sex as a share of the entity's **total population of both sexes** that year. All 16 rows of an entity-year sum to 100.0 |
| `pct_signed` | decimal, 1 dp | same number, **negative for female**, positive for male. This is what makes the butterfly work with no calculated field |
| `estimated` | TRUE/FALSE | TRUE for any interpolated or modelled value |
| `source_id` | text | joins to `data/sources.csv` |

Female negative because the mockup puts female on the left.

### Rules
- Age bands exactly as listed, and exactly eight. If the source publishes 5-year bands,
  aggregate to these and say so in the README.
- `pct_of_total` is the share of the **whole** population, not of that sex. In the mockup
  the labels read 16.5% and 16.7% and the two sides together make 100%.
- Include every year from 1990, not only the four in the mockup. I will filter in Tableau.
- EU27 is a weighted aggregate across member states, not an average of national shares.
  If Eurostat publishes EU27 directly, use that and note which EU27 definition it is.
- Sources: Eurostat `demo_pjangroup` first; UN World Population Prospects for Albanian
  years Eurostat does not cover. Mark those rows `estimated` TRUE.

### Also write
`tableau/BUILD.md`, with the steps to build these two panels in Tableau Public from this
one file: which field on rows, which on columns, mark type, how `age_order` sorts the bands,
how `pct_signed` produces the butterfly, how to make the four years small multiples, and
how to label only the largest band on each side. Written so it can be followed without
reading the analysis.

### Do not
Build charts, except in the study's `viz/index.html` review page. No Plotly in the Tableau
pack, no images, no .twb file.
