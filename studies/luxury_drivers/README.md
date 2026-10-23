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
Extreme daily moves reviewed; all match known events except Kering −16.6% on 2026-10-23 (to verify).

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
- **H1 partly supported:** significant China beta for Kering, Richemont, Burberry, Prada (robust to
  the MSCI China ETF); strongest in 2020–22, faded in 2023–26 except Prada (HK-listed).
- **H3:** since 2023 every stock except Richemont underperformed its factor-implied return:
  Kering −133, Burberry −107, LVMH −93, Moncler −46, Hermès −43, Prada −40, Cucinelli −13,
  Richemont +3 (cumulative log points).

## Reproduce
```bash
uv run python -m studies.luxury_drivers.fetch   # downloads raw data to data/raw/ (git-ignored)
uv run pytest                                    # checks calculations
```
