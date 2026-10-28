# B2 — build the pyramids and the female/male share line in Tableau Public

Two panels from one file, `data/b2_age_sex.csv`. Columns are described in
[B2-TABLEAU-SPEC.md](B2-TABLEAU-SPEC.md). Colours are picked from the mockup; adjust to taste.

| Use | Hex |
|---|---|
| Female (left) | `#F0A13B` orange |
| Male (right) | `#3D9BE9` blue |
| Background | `#1A0B2E` dark purple |
| Text and axis | `#D9D4E3` light grey |

## 0. Connect
1. Tableau Public → **Connect → Text file** → `data/b2_age_sex.csv`.
   (Tableau Public reads a local file; it cannot read the CSV from a GitHub URL.)
2. In the data pane, check the types: `year` and `age_order` are **Number (whole)** and
   **Dimensions** (drag them above the line if Tableau put them under Measures);
   `population`, `pct_of_total`, `pct_signed` are Number (decimal) measures; `estimated` is a
   String or Boolean dimension.

## Panel A — population pyramids, four years side by side

1. New sheet, name it `Pyramid`.
2. **Filters:** drag `entity` to Filters → tick `Albania` (make a second sheet for `EU27`, or
   put `entity` on Rows in step 4 to stack the two). Drag `year` to Filters → tick `1990`,
   `2000`, `2010`, `2025`.
3. **Columns:** drag `year` (a discrete, blue pill), then `pct_signed` to the right of it
   (`SUM(pct_signed)`, a green pill). The discrete `year` splits the view into one pane per year:
   these are the small multiples.
4. **Rows:** drag `age_band`.
5. **Sort the bands:** right-click `age_band` on Rows → **Sort** → *Sort by: Field* →
   field `age_order`, aggregation `Minimum`, order **Descending**. `80+` is now at the top and
   `0-14` at the bottom. Without this, Tableau sorts the text A–Z, which happens to put
   `0-14` on top (an upside-down pyramid) and breaks as soon as a band is renamed.
6. **Marks:** mark type **Bar**. Drag `sex` to **Color** and set Female `#F0A13B`, Male
   `#3D9BE9`. Female bars point left because their `pct_signed` is negative: that is the
   whole butterfly, no calculated field needed.
7. **Axis labels without minus signs:** right-click the `pct_signed` axis → **Format** →
   Axes → Numbers → **Custom** → `0"%";0"%"`. Right-click again → **Edit Axis** → *Fixed*,
   start `-20`, end `20`, so every pane uses the same scale and the four years compare honestly.
   Then untick the axis title, or rename it `% of total population`.
8. **Label only the largest band on each side:** Analysis → **Create Calculated Field**,
   name `Largest band label`:
   ```
   IF ABS(SUM([pct_signed])) = WINDOW_MAX(ABS(SUM([pct_signed])))
   THEN SUM([pct_of_total])
   END
   ```
   Drag it to **Label**. Right-click the pill → **Compute Using → Specific Dimensions** → tick
   **`age_band` only** (leave `sex` and `year` unticked, so the maximum restarts for each side
   of each pyramid). Format the label number as Custom `0.0"%"`. Tableau puts each label at
   the outer end of its bar: left for Female, right for Male, as in the mockup.
9. **Tooltip:** click Tooltip and replace the text with:
   ```
   <sex>, aged <age_band>, <year>
   <SUM(pct_of_total)>% of <entity>'s population (<SUM(population)> people)
   Estimated: <estimated>   Source: <source_id>
   ```
   (Drag `pct_of_total`, `population`, `estimated` and `source_id` to Detail first so they are
   available.)
10. **Tidy:** hide the `year` field label (right-click the header row → Hide Field Labels for
    Columns) and keep the year numbers as titles; Format → Shading → background `#1A0B2E`;
    remove grid lines (Format → Lines → Grid Lines: None).

Honest limits:
- Bars for `0-14` and `65-79` cover 15 years and `80+` is open-ended, so they look larger than
  a 10-year band would. Tableau cannot correct this; keep the band labels visible so the
  reader sees the widths.
- Tableau cannot fade bars by a field. To show which bars are estimated, either keep it in the
  tooltip (above), or make a calculated field `[sex] + IF [estimated] = "TRUE" THEN " (est.)" ELSE "" END`
  on Color with lighter shades for the "(est.)" members.
  (If `estimated` came in as Boolean, write `IF [estimated] THEN`.)

## Panel B — female and male % of total population, 1990–2025

1. New sheet, name it `Sex share`.
2. **Filter:** `entity` → `Albania` (or show the filter to switch to `EU27`).
3. **Exact share calculation** (more accurate than adding the rounded `pct_of_total`, which can
   be off by up to 0.4 points): Create Calculated Field `Sex share %`:
   ```
   SUM([population]) / TOTAL(SUM([population])) * 100
   ```
4. **Columns:** right-click-drag `year` → choose **year (continuous)** (green pill), so the
   axis runs 1990–2025.
5. **Rows:** `Sex share %`. Right-click it → **Compute Using → sex**, so each year's
   Female + Male = 100.
6. **Marks:** **Line**. `sex` on **Color** (same two hex values as Panel A).
7. **Labels:** drag `Sex share %` to Label → Label options: **Line ends**, format Custom
   `0.0"%"`. That gives the first and last values, as in the mockup.
8. **Axis:** Edit Axis → untick *Include zero*, so the small movement around 50% is visible;
   say so in the subtitle (e.g. "axis starts at 48%") so the scale is not misleading.
9. **Tooltip:** `<sex>, <year>: <AGG(Sex share %)>% of <entity>'s population`.

Honest limit: Albania 2022 and 2024 and all years before 2002 are estimates (see the
`estimated` column); the line is smooth there partly because of the interpolation.

## Put them on the dashboard
1. New Dashboard, size **Automatic** or Fixed 1600 × 900.
2. Drag a **Horizontal** container to the bottom; drop `Sex share` on the left (about one
   third of the width) and `Pyramid` on the right.
3. Dashboard → Format → background `#1A0B2E`. Add a Text object above each sheet with the
   title, e.g. "**Female** and **male** percentage of the population by age group", colouring
   the words Female and Male with the two hex values.
4. Show the `entity` filter once and apply it to both sheets (filter menu → **Apply to
   Worksheets → Selected Worksheets** → tick both), so one click switches Albania / EU27.
5. Source line at the bottom: "Eurostat demo_pjangroup; UN World Population Prospects 2024
   for years Eurostat does not cover. Own calculations."
