# Study 01 — What Drives European Luxury Stocks?

*Market, currency and China exposure, creative-director changes, and the post-2023 divergence (2014–2026).*

Status: **analysis in progress, not published.** Findings below are preliminary.

## Research questions
1. How much of each stock's return is explained by common factors (European market, EUR/USD, China)
   versus company-specific news?
   H1: China exposure matters beyond the market. H2: euro strength hurts returns (translation effect).
2. Did those sensitivities change over time (2014–19, 2020–22, 2023–26)?
3. Is the post-2023 divergence factor-driven or company-specific? (H3: mainly company-specific.)
4. How does the market react to creative-director changes? *(event study, to do)*
5. Do top-tier and aspirational brands behave differently? *(tier split, to do)*

## Data
| Series | Source | Notes |
|---|---|---|
| LVMH, Hermès, Kering, Richemont, Moncler, Burberry, Prada, Brunello Cucinelli | Yahoo Finance (yfinance) | Adjusted close (dividends reinvested). Raw data not redistributed. |
| STOXX Europe 600, Hang Seng, iShares MSCI China ETF | Yahoo Finance | Price indices, local currency |
| EUR reference rates (USD, CHF, GBP, HKD, CNY) | ECB Data Portal, EXR | Used to convert all stocks to EUR |

Validation (2026-10-23): no missing weeks in 2014-01 → 2026-10, no stale prices, no corporate actions
beyond ordinary dividends (Kering's 2018 Puma distribution is already back-adjusted by Yahoo).
Extreme daily moves (>15%) flagged. Confirmed against news: Kering −16.6% on 2026-10-23 (Q3 2026 revenue,
Gucci −6% comparable), Kering −10.7% on 2025-03-14 (Demna), Richemont 2015-01-15 (SNB franc shock).
Still to check: Kering +16.9% 2026-07-29, Cucinelli −17.3% 2025-09-25, Burberry 2024-07-15/2024-11-14/
2025-05-14, Richemont +16.4% 2025-01-16. Yahoo's STOXX 600 series lacks 64 days since 2014 on which Paris/London traded
(e.g. Ascension); the event study therefore aligns stock and index *prices* before computing returns.

## Method
- Friday-to-Friday log returns in EUR (weekly sampling limits asynchronous-close bias between
  Hong Kong and Europe).
- OLS per stock on market, ΔlogEUR/USD and Hang Seng, Newey–West (HAC, 4 lags) standard errors.
- 104-week rolling betas; sub-period regressions.
- Out-of-sample abnormal returns from 2023: betas estimated on 2014–2022; benchmark = betas × factor
  returns (pre-period alpha deliberately not extrapolated).
- Robustness: MSCI China ETF instead of Hang Seng; local-currency returns for non-EUR listings.

## Preliminary findings (to be reviewed)
- Factors explain 17–46% of weekly variance (R²); most variation is company/sector-specific.
- Market betas rose from ~0.5–1.1 (2014–19) to ~1.2–1.7 (2023–26), Prada excepted.
- **H2 not supported at weekly frequency:** euro strength coincides with *higher* luxury returns
  (positive EUR/USD beta, significant for several names; Prada/Burberry's negative EUR betas are a
  conversion artefact and turn positive in local currency).
- **H1 partly supported:** significant China beta for Kering, Richemont, Burberry, Prada and (marginally,
  t≈2.0) Hermès; 7 of 8 with the MSCI China ETF; strongest in 2020–22, faded in 2023–26 except Prada (HK-listed).
- **H3:** since 2023 every stock except Richemont underperformed its factor-implied return:
  Kering −133, Burberry −107, LVMH −93, Moncler −46, Hermès −43, Prada −40, Cucinelli −13,
  Richemont +3 (cumulative log points).

### Creative-director event study (preliminary)
16 creative announcements 2015–2026 plus 4 Kering/Gucci management changes as a comparison group, in
[events.csv](events.csv), each with source, timing note and confounders. Daily market
model (estimation window −250…−21 trading days; STOXX 600 in EUR, Prada vs Hang Seng in HKD).
- Strong reactions only where the brand dominates group profit: **Demna → Gucci −13.0% on the day**
  (t −5.9), **Tisci → Burberry +5.2%** (t 3.5), Tisci→Lee at Burberry +3.8% (t 2.4),
  Michele → Gucci +2.8% (t 2.3).
- LVMH events (Abloh, Pharrell, Chiuri, Anderson) show no significant reaction, consistent with
  dilution across ~75 maisons.
- Departures move stocks less than appointments (often leaked or anticipated).
- Multiple testing: 15 events × several windows; only Demna and Tisci (|t| > 3.3) survive a
  Bonferroni-style threshold. Prada/Raf Simons is confounded by the Feb 2020 COVID sell-off.
- Saint Laurent / Vaccarello exit (9 Oct 2026): +1.1%, not significant.
- **Management changes moved Kering more than most creative changes:** Bizzarri's exit from Gucci
  +6.8% (t 5.3), Luca de Meo named Kering CEO +10.9% (t 4.6). Mean |day-0 CAR| 5.6% (n=4) vs 2.5%
  for creative events (n=16). Tiny sample and a company in turnaround, where investors may reward
  any change; Cantino's appointment (8 Oct 2024) coincides with a ~10% Hang Seng crash.

### Sector vs brand split and tiers (preliminary)
- Adding a leave-one-out luxury-peer factor splits the post-2023 gap: every name carries a sector-wide
  drag of roughly −28 to −50 log points. The brand-specific remainder ranges from Kering −100,
  Burberry −78 and LVMH −63 to Cucinelli +28 and Richemont +43. This is relative to peers: one peer's
  collapse lifts the others.
- Tiers (equal-weighted, cumulative log return): 2023–26 top tier +10, hard luxury +46,
  diversified −50, aspirational −30. The top-tier/aspirational gap opened in 2020–22 (+81 vs +15).
  The top-minus-aspirational spread has a negative China beta (−0.15, t −2.7): aspirational names are more
  China-sensitive. R² is only 4%, so the spread is mostly not factor-driven.

## Reproduce
```bash
uv run python -m studies.luxury_drivers.fetch   # downloads raw data to data/raw/ (git-ignored)
uv run pytest                                    # checks calculations
uv run python -m studies.luxury_drivers.build   # writes docs/studies/luxury-drivers/index.html
```
Open the output in a browser: `open docs/studies/luxury-drivers/index.html`.
