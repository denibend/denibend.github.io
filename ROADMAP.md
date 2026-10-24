# Roadmap

## Completed
- 2026-10-23 · Phase 0: charter agreed; tooling chosen (uv, Python 3.13, Plotly static HTML on GitHub
  Pages from `docs/`); local project and environment created and verified.
- 2026-10-23 · Git configured (noreply email), local repo initialised; GitHub CLI authenticated as `denibend`.
- 2026-10-23 · **Published**: repo public, GitHub Pages live at https://denibend.github.io (Study 01 report,
  dashboard, landing page).
- 2026-10-23 · Study 01: data pipeline + validation, factor model, out-of-sample abnormal returns,
  creative-director event study (15 sourced events); 10 tests passing.

## Current objectives
- Study 01 retrospective (what worked, what to template for Study 02).
- Phase 2: richer landing page (about, skills/methods, featured findings).
- Phase 1, Study 01: **What drives European luxury stocks? FX, China and the market.**
  - Universe (agreed): LVMH, Hermès, Kering, Richemont, Moncler, Burberry, Prada, Brunello Cucinelli.
  - Period (agreed): Jan 2014 – latest.
  - Core (agreed): weekly-return factor regressions (STOXX 600, EUR/USD from ECB, Hang Seng), rolling
    betas, common vs idiosyncratic variance, post-2023 divergence.
  - Event study: done (preliminary). 16 creative + 4 Kering management events (incl. Vaccarello's
    Saint Laurent exit, 9 Oct 2026, verified); reviewed by Denisa 2026-10-24.
  - Done: luxury-peer factor (sector vs brand split), tier split, draft report
    (docs/studies/luxury-drivers/index.html) and dashboard (…/dashboard.html), minimal landing page
    (docs/index.html); checked visually on desktop and at ~520px width.
  - Licensing decision (2026-10-23): publish analysis and charts with source credited; never raw data files.
  - To do: dark mode; verify true 400px mobile layout on a real phone.
  - Licensing: Yahoo Finance prices used for analysis only; publish derived results.

## Current: Study 02 · The luxury wallet (started 2026-10-24)
- Design v2 agreed (studies/luxury_wallet/README.md): H1 wealth vs income by price tier (US, EU, China),
  H2 tiers, H3 which wallets shift to experiences (substitution vs complement), H4 regional mix.
- Done: data pipeline for BEA, FRED, Fed DFA, ECB DWA, Eurostat (cp18, HBS, confidence, tourism), HK retail.
- Open: BLS Consumer Expenditure (spending by income group) blocks automated access; Denisa to decide.
- Next: H1 US analysis; regional revenue collection (2019–2025, 8 companies).

## Luxury research series (from Denisa's input, 2026-10-23)
- Study 02 (in progress, see above) · The luxury wallet: wealth vs income (top-tier vs aspirational vs equity wealth,
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
- Study 02 imports Study 01 modules (tier returns, FX conversion). Move them to a shared module if a
  third study reuses them.
- Portfolio landing page (Phase 2) not started; a minimal placeholder will ship with Study 01.
