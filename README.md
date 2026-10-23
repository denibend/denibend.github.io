# Market Research & Analytics Portfolio

Independent research by **Denisa Bendaj**, a business analytics professional with over 10 years in
international luxury, fashion, retail and e-commerce (Bucherer, Gucci, PVH, Tommy Hilfiger), now using
Python for financial, economic and market research.

Each study asks one question, tests it against public data, and publishes:
- a **research report**: question, data, method, results, limitations;
- an **interactive dashboard** for exploring the evidence.

🔗 Portfolio site: https://denibend.github.io
🔗 LinkedIn: https://www.linkedin.com/in/dbendaj/

## Studies

| # | Study | Published | Report | Dashboard |
|---|-------|-----------|--------|-----------|
| 01 | What drives European luxury stocks? Market, FX, China and creative-director effects | 2026-10-23 | [Report](https://denibend.github.io/studies/luxury-drivers/) | [Dashboard](https://denibend.github.io/studies/luxury-drivers/dashboard.html) |

## Reproducing the analysis

Requirements: [uv](https://docs.astral.sh/uv/) (it installs the right Python version automatically).

```bash
git clone https://github.com/denibend/denibend.github.io.git
cd denibend.github.io
uv sync                       # create the environment from uv.lock
uv run pytest                 # run the tests
```

Each study folder in `studies/` has its own README with the exact commands to fetch data and rebuild
its report and dashboard.

## Repository layout

```
studies/<study>/   code for one study: fetch → analysis → charts → build
tests/             automated checks of the calculations
docs/              the published website (served by GitHub Pages)
```

## Data and licensing

Only public data sources are used, and each study documents them. Where a provider's terms
restrict redistribution (e.g. market price data), the raw data is not included in this repository;
only derived statistics and charts are published.

Nothing here is investment advice.
