# Study 02 — The Luxury Wallet

*Wealth vs income, goods vs experiences, and the regional mix of luxury demand.*

Status: **research design (draft for Denisa's approval)**, 2026-10-24.

## Research questions and hypotheses
1. **Wealth vs income.** Is luxury spending driven by household *wealth* (equity and net worth) or by *income*?
   - H1: Spending on jewellery and watches responds more to wealth than to disposable income. Clothing
     shows the opposite pattern.
   - H2: Top-tier luxury stocks track wealth; aspirational stocks track income and confidence.
     Tiers as in Study 01.
2. **Goods vs experiences.** Did travel, hotels and dining take share of the discretionary budget from personal
   luxury goods after COVID, and has the shift persisted?
   - H3: The post-2021 shift towards experiences is structural, not a one-off rebound. The experiences
     share stays above its pre-2020 trend through 2025–26.
3. **Regional mix.** Where did luxury demand grow and shrink in 2019–2025, and does a company's regional
   exposure explain its post-2023 brand-specific gap (Study 01)?
   - H4: Companies more exposed to Asia/China in 2022 show larger brand-specific gaps after 2023.

## Data (feasibility checked 2026-10-24)
| Need | Source | Coverage | Licence |
|---|---|---|---|
| US spending by category, monthly, nominal and real (jewellery & watches, clothing, luggage, accommodation, air travel, package tours, food services, recreation) | BEA NIPA flat files (no key) | 1959–Aug 2026 (real from 2007 for detail) | US public domain |
| EU household consumption by purpose (COICOP 2018): clothing, personal effects, recreation, package holidays, accommodation | Eurostat `nama_10_cp18` | 2015–2025, annual, by country | CC BY 4.0 |
| US household net worth (quarterly), real disposable income, saving rate | FRED (Fed Z.1, BEA) | 1945/1959–2026 | Public |
| EU consumer confidence | Eurostat `ei_bsco_m` | monthly, to Sep 2026 | CC BY 4.0 |
| EU tourism nights | Eurostat `tour_occ_nim` | monthly, to Jul 2026 | CC BY 4.0 |
| Revenue by region, 8 companies | Annual reports / results releases | 2019–2025, hand-collected | Public facts, cited per figure |
| Luxury stock tiers | Study 01 pipeline | weekly 2014–2026 | as Study 01 |

Gaps: no open monthly series for Chinese luxury demand found yet, so China is covered through company-reported
regional revenue. Case-Shiller house prices are licensed and will not be used; FHFA is the public alternative.
The OECD confidence series on FRED end in Jan 2024.

## Method (draft)
- **H1:** quarterly growth regressions, 1960–2026: real jewellery & watches spending on real disposable income
  growth and real household net worth growth, with distributed lags and HAC errors. The same model for
  clothing and for total goods as comparisons. Sub-period stability checks. Growth rates, not levels, to
  avoid spurious regression.
- **H2:** monthly tier returns (Study 01) on equity-wealth and income/confidence proxies.
- **H3:** experiences vs luxury-goods shares of discretionary spending (US monthly, EU annual), compared
  with the 2010–2019 trend; persistence test on deviations from trend.
- **H4:** regional revenue shares by company and year; validation = regions sum to reported group revenue.
  Descriptive cross-section against Study 01 brand gaps (n = 8, illustrative only).

## Open decisions
See ROADMAP.md / conversation of 2026-10-24.
