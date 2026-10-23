# Roadmap

## Completed
- 2026-10-23 · Phase 0: charter agreed; tooling chosen (uv, Python 3.13, Plotly static HTML on GitHub
  Pages from `docs/`); local project and environment created and verified.
- 2026-10-23 · Git configured (noreply email), local repo initialised; GitHub CLI authenticated as `denibend`.
- 2026-10-23 · Study 01: data pipeline + validation, factor model, out-of-sample abnormal returns,
  creative-director event study (15 sourced events); 10 tests passing.

## Current objectives
- Phase 0 finish: create public repo `denibend/denibend.github.io` and enable Pages, **after approval**.
- Phase 1, Study 01: **What drives European luxury stocks? FX, China and the market.**
  - Universe (agreed): LVMH, Hermès, Kering, Richemont, Moncler, Burberry, Prada, Brunello Cucinelli.
  - Period (agreed): Jan 2014 – latest.
  - Core (agreed): weekly-return factor regressions (STOXX 600, EUR/USD from ECB, Hang Seng), rolling
    betas, common vs idiosyncratic variance, post-2023 divergence.
  - Event study: done (preliminary); Denisa to review events.csv; Saint Laurent/Vaccarello exit
    (reportedly Oct 2026) unverified.
  - To do: luxury-peer factor (sector vs brand-specific), tier split (Hermès+Cucinelli top tier;
    Richemont hard luxury; LVMH diversified; Kering, Burberry, Prada, Moncler aspirational),
    charts, dashboard, report.
  - Licensing: Yahoo Finance prices used for analysis only; publish derived results.

## Luxury research series (from Denisa's input, 2026-10-23)
- Study 02 (proposed) · The luxury wallet: wealth vs income (top-tier vs aspirational vs equity wealth,
  real wages, confidence), goods vs experiences (BEA PCE categories, Eurostat COICOP), regional revenue
  mix from company filings.
- Study 03 (proposed) · Attention economy: is public attention to luxury brands spikier and shorter-lived?
  Wikipedia pageviews (open), Google Trends (fragile, relative), reported marketing spend. Note: the
  "shrinking attention span" claim is contested, so test it rather than assume it. True media-effectiveness/MMM
  needs proprietary data and is out of scope.

## Research backlog
- Anatomy of the Euro Area Inflation Shock (Eurostat HICP; contribution decomposition), a strong next candidate.
- When Bonds Stopped Hedging: stock–bond correlation regimes vs inflation.
- Does Consumer Sentiment Predict Spending? (EU confidence vs retail volumes; forecast evaluation).
- Europe's Political Fragmentation 1985–2025 (ParlGov, PopuList; effective number of parties).

## Outstanding decisions
- Report and dashboard: one page with two sections, or two linked pages.

## Technical debt / notes
- Portfolio landing page (Phase 2) not started; a minimal placeholder will ship with Study 01.
