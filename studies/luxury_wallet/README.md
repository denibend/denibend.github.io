# Study 02 — The Luxury Wallet

*Wealth vs income, goods vs experiences, and the regional mix of luxury demand: US, EU and China.*

Status: **research design v2** (revised with Denisa's input, 2026-10-24).

## Research questions and hypotheses

### 1 · Wealth vs income, by price tier
Spending categories mix price tiers: "clothing" includes high-priced items and "jewellery & watches" includes
low-priced ones. A category total is therefore a blend of wealth-driven and income-driven buyers.
- **H1a:** Category totals respond to both drivers. Jewellery & watches is more wealth-sensitive than clothing, but
  neither is purely one or the other.
- **H1b:** The high-priced end follows the wealth of the *top* of the distribution (top 1% / top 10%), while the
  mass end follows income. Tests:
  (i) category spending on income plus wealth split by group (top 1%, next 9%, middle 40%, bottom 50%);
  (ii) luxury companies' regional revenue and top-tier stocks on top-group wealth vs income.
- Regions: **US** (BEA spending + Fed Distributional Financial Accounts), **EU** (Eurostat spending by country +
  ECB Distributional Wealth Accounts), **China** where possible (Hong Kong jewellery & watch retail sales,
  company-reported Asia revenue).

### 2 · Tiers (from Study 01)
- **H2:** Top-tier luxury stocks track wealth; aspirational stocks track income and confidence.

### 3 · Goods vs experiences: which wallets shift
- **H3a (substitution):** The post-COVID shift from goods to experiences is concentrated in income-driven,
  middle-class wallets, which trade a bag for a trip.
- **H3b (complement):** Wealth-driven wallets do not shift. They add experiences *and* buy fresh items to wear on
  them. Implications: top-tier luxury demand rises with travel rather than falling; luxury sales in destinations
  (luxury groups' revenue in Europe, Hong Kong jewellery sales) move with inbound tourist nights.
- Persistence: does the experiences share stay above its 2010–19 trend through 2025–26?

### 4 · Regional mix
- **H4:** Companies more exposed to Asia/China in 2022 show larger brand-specific gaps after 2023 (Study 01).

## Data (feasibility checked 2026-10-24)
| Need | Source | Coverage | Licence / access |
|---|---|---|---|
| US spending by category, monthly (jewellery & watches, clothing, luggage, accommodation, air travel, package tours, food services, recreation) | BEA NIPA flat files | 1959–Aug 2026 | Public domain |
| US wealth by group (top 1%, 90–99%, 50–90%, bottom 50%) | Fed Distributional Financial Accounts | quarterly 1989–2026 | Public domain |
| US real disposable income, saving rate, aggregate net worth | FRED (BEA, Fed Z.1) | 1959–2026 | Public |
| US spending by income group | BLS Consumer Expenditure Survey | annual | **Blocked for automated download (403/503); decision needed** |
| EU spending by purpose, by country (COICOP 2018) | Eurostat `nama_10_cp18` | 2015–2025, annual | CC BY 4.0 |
| EU spending structure by income quintile | Eurostat HBS `hbs_str_t223` | 2015, 2020 only | CC BY 4.0 |
| Euro-area wealth by group (bottom 50%, middle 40%, top 10%), by country | ECB Distributional Wealth Accounts | quarterly to 2026-Q1 | ECB reuse with attribution |
| EU consumer confidence; tourist nights by residence | Eurostat `ei_bsco_m`, `tour_occ_nim` | monthly, to 2026 | CC BY 4.0 |
| Hong Kong retail sales: jewellery, watches, valuable gifts | HK Census & Statistics Dept open API | monthly Oct 2004–Aug 2026 | Open data |
| Revenue by region, 8 companies | Annual reports / results releases | 2019–2025, hand-collected | Public facts, cited per figure |
| Luxury stock tiers | Study 01 pipeline | weekly 2014–2026 | as Study 01 |

Not used: Case-Shiller (licensed; FHFA instead); the OECD confidence series on FRED (ended Jan 2024).

## Method (draft)
- **H1a/H1b (US):** quarterly growth regressions, 1990–2026, of real category spending on real disposable income
  growth and real wealth growth by group, with distributed lags and HAC errors. Comparisons: clothing,
  jewellery & watches, total goods. Sub-period stability.
- **H1 (EU):** country panel 2015–2025 (annual) of category spending growth on income and wealth by group, with
  country fixed effects. Short sample, so it is a supporting rather than primary test.
- **H1 (China):** Hong Kong jewellery sales against Chinese equity wealth proxies and visitor flows. Descriptive.
- **H3:** experiences vs goods shares (US monthly, EU annual) against 2010–19 trends; income-group shares
  (BLS, if accessible; HBS 2015 vs 2020); destination sales against tourist nights.
- **H4:** regional revenue shares by company and year, validated so regions sum to group revenue;
  cross-section against Study 01 brand gaps (n = 8, illustrative).

## Preliminary findings (H1, 2026-10-24)
Typical-quarter effect = elasticity × one standard deviation of the driver's quarterly growth (% of
category spending, over the following year). Main specifications exclude 2020–21.

| | Income | Equity wealth | Housing wealth |
|---|---|---|---|
| **US** jewellery & watches (1990–2026) | 1.11 | **1.51** | 0.70 |
| **US** luggage & leather goods | 0.65 | **1.46** | 0.62 |
| **US** clothing & footwear | 0.11 | **0.86** | 0.30 |
| **US** all goods | 0.37 | 0.52 | 0.42 |
| **EU** semi-durables (clothing, footwear, travel goods), 7 countries, 2011–2026 | **1.00** | **0.80** | 0.09 |
| **EU** durables (incl. jewellery & watches, dominated by cars) | 1.13 | 0.59 | −0.17 |
| **EU** total consumption | 0.44 | 0.14 | 0.12 |

- Luxury-type goods respond to equity wealth (held 88% by the top 10% in the US) more than goods in general,
  in both regions. The clothing-type effect is of similar size: US 0.86, EU 0.80.
- In the EU these goods are also strongly income-driven; US clothing barely responds to income. Housing
  wealth matters in the US but not in the EU, consistent with weaker housing-wealth effects in Europe.
- US jewellery & watches is the most income-elastic category (elasticity ≈ 1.2): the category blends
  both wallets, as the price-tier hypothesis suggests.
- Wealth *groups* cannot be separated in aggregate data (US top-1% and next-9% growth correlate at 0.95),
  hence the equity-vs-housing split. EU annual data (2015–2025) proved too short and too sensitive to 2022
  (reopening + equity fall); the quarterly panel results hold with or without 2022.
- Unreliable: US accommodation and package tours show implausible negative income elasticities (small,
  noisy categories; tax-rebate timing).

### China via Hong Kong (preliminary, 2026-10-24)
Year-on-year growth of HK jewellery, watch & valuable-gift retail sales (HK$), monthly 2005–2026,
excluding 2020-01…2024-02 (border closure and base effects); HAC errors with 12 lags; n = 201, R² ≈ 0.62.

| Driver (yoy growth) | Elasticity | t |
|---|---|---|
| Mainland visitor arrivals | 0.67 | 8.9 |
| Renminbi buying power (HKD per CNY) | 2.36 | 5.2 |
| Shanghai Composite (mainland equity wealth) | 0.10 | 2.2 |
| Gold price, added as a control (USD) | 0.10 | 0.8 |

- The tourism channel dominates: HK luxury sales move with mainland visitors and the renminbi. A
  mainland equity-wealth effect exists but is small. This is consistent with the H3b complement idea
  (luxury bought as part of travel).
- Structural break after reopening. Sales per mainland visitor peaked at HK$3,205 (2011), fell to
  ~HK$1,700 (2016–18) and reached a record low of HK$1,383 in 2025. Against a model fitted on 2005–19,
  sales ran 20–25 points *below* prediction in Mar 2024–Feb 2025 and 1–7 points below since Mar 2025.
  The 2026 rebound is about what returning visitors and record gold prices imply anyway.
- Caveats: nominal HK$ values; the category includes gold jewellery; visitor data are by nationality
  since Oct 2024 (arrival cards abolished); context events (2013 anti-corruption campaign, 2014 and 2019
  protests) are not modelled.
