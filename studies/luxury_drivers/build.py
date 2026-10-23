"""Run the Study 01 analysis and write the dashboard page.

Run:  uv run python -m studies.luxury_drivers.build
Output: docs/studies/luxury-drivers/index.html (requires data from `fetch` first)
"""

import json
from datetime import date

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.offline import get_plotlyjs_version

from studies.luxury_drivers import analysis, charts, prepare, validate
from studies.luxury_drivers.config import (
    EVENT_MARKET,
    EVENT_MARKET_DEFAULT,
    RAW_DIR,
    SAMPLE_START,
    STOCKS,
    STUDY_DIR,
    TIERS,
)

ROOT = STUDY_DIR.parents[1]
OUT_DIR = ROOT / "docs" / "studies" / "luxury-drivers"
ESTIMATION_END = "2022-12-31"
PERIODS = [("2014", "2019"), ("2020", "2022"), ("2023", "2026")]
PLOT_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toImage"],
}


def run_event_study(log_prices: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    events = pd.read_csv(STUDY_DIR / "events.csv")
    paths = {}
    for i, e in events.iterrows():
        market = log_prices[EVENT_MARKET.get(e.ticker, EVENT_MARKET_DEFAULT)]
        stock = log_prices[e.ticker]
        day0 = analysis.event_car(stock, market, e.event_day, window=(0, 0))
        win3 = analysis.event_car(stock, market, e.event_day, window=(-1, 1))
        events.loc[i, ["car0", "t0", "sigma", "car3", "t3"]] = [
            day0.car,
            day0.t,
            day0.sigma,
            win3.car,
            win3.t,
        ]
        label = f"{e.brand} · {e.person} ({e.event_day})".replace("->", "→")
        paths[label] = analysis.event_path(stock, market, e.event_day)
    return events, paths


def fig_html(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config=PLOT_CONFIG)


def table_html(df: pd.DataFrame, **kwargs) -> str:
    return df.to_html(classes="data", border=0, na_rep="–", **kwargs)


def main() -> None:
    names = {t: name for t, (name, _) in STOCKS.items()}
    stocks = list(names.values())
    colors = dict(zip(stocks, charts.SERIES))

    # Data and quality checks
    prices, _ = prepare.load_raw()
    coverage = validate.coverage(prices).rename(index=names)
    weekly = prepare.build_weekly_dataset(SAMPLE_START).rename(columns=names)

    # Factor model
    full = analysis.factor_table(weekly, stocks)
    by_period = pd.concat(
        {f"{a}–{b}": analysis.factor_table(weekly.loc[a:b], stocks) for a, b in PERIODS}, axis=1
    )
    rolling = {s: analysis.rolling_betas(weekly, s) for s in stocks}
    gap = analysis.sector_vs_brand_gap(weekly, stocks, ESTIMATION_END)

    # Tiers
    tiers = analysis.tier_returns(weekly, TIERS)
    tier_periods = pd.DataFrame({f"{a}–{b}": tiers.loc[a:b].sum() for a, b in PERIODS}).map(
        lambda x: f"{x * 100:+.0f}"
    )

    # Event study
    events, paths = run_event_study(prepare.build_daily_log_prices())
    demna = events.loc[events["person"] == "Demna"].iloc[0]

    beta_cols = {"beta_market": "Market β", "beta_eurusd": "EUR/USD β", "beta_china": "China β"}
    full_table = full[[*beta_cols, "t_market", "t_eurusd", "t_china", "r2"]].rename(
        columns={
            **beta_cols,
            "t_market": "t (mkt)",
            "t_eurusd": "t (FX)",
            "t_china": "t (China)",
            "r2": "R²",
        }
    )
    period_table = by_period.xs("beta_market", axis=1, level=1).rename(
        columns=lambda c: f"Market β {c}"
    )
    event_table = events[
        ["event_day", "brand", "person", "category", "car0", "t0", "car3", "t3", "confounders"]
    ].assign(car0=lambda d: d.car0 * 100, car3=lambda d: d.car3 * 100)
    event_table.columns = [
        "Event day",
        "Brand",
        "Person",
        "Category",
        "Day 0 %",
        "t",
        "Days −1…+1 %",
        "t ",
        "Confounders",
    ]

    context = {
        "built": date.today().isoformat(),
        "data_end": weekly.index[-1].date().isoformat(),
        "n_weeks": len(weekly),
        "plotly_version": get_plotlyjs_version(),
        "retrieved": json.loads((RAW_DIR / "provenance.json").read_text())["retrieved_utc"][:10],
        "r2_min": full["r2"].min(),
        "r2_max": full["r2"].max(),
        "beta_early": by_period[("2014–2019", "beta_market")].median(),
        "beta_late": by_period[("2023–2026", "beta_market")].median(),
        "sector_median": gap["sector"].median() * 100,
        "china_sig": list(full.index[full["p_china"] < 0.05]),
        "china_alt_sig": int(
            (
                analysis.factor_table(weekly, stocks, ["market", "eurusd", "china_alt"])[
                    "p_china_alt"
                ]
                < 0.05
            ).sum()
        ),
        "tier_cum": {t: tiers.loc[a:b, t].sum() * 100 for t in TIERS for a, b in PERIODS[2:]},
        "sector_min": gap["sector"].min() * 100,
        "sector_max": gap["sector"].max() * 100,
        # Event results by person, for quoting in the text (car0 in %).
        "ev": {
            e.person.replace("->", "→"): {"car0": e.car0 * 100, "t0": e.t0}
            for e in events.itertuples()
        },
        "worst_brand": gap["brand"].idxmin(),
        "worst_brand_gap": gap["brand"].min() * 100,
        "best_brand": gap["brand"].idxmax(),
        "best_brand_gap": gap["brand"].max() * 100,
        "demna_car": demna.car0 * 100,
        "demna_t": demna.t0,
        "n_events": len(events),
        "charts": {
            "stocks": fig_html(charts.highlight_performance(weekly[stocks], colors)),
            "tiers": fig_html(charts.performance_index(tiers, dict(zip(TIERS, charts.SERIES)))),
            "betas": fig_html(charts.factor_betas(full)),
            "rolling": fig_html(charts.rolling_betas_chart(rolling)),
            "gap": fig_html(charts.divergence_bars(gap)),
            "events": fig_html(charts.event_dots(events)),
            "paths": fig_html(
                charts.event_paths_chart(
                    paths, default=[*paths].index(next(k for k in paths if "Demna" in k))
                )
            ),
        },
        "tables": {
            "factors": table_html(full_table, float_format="%.2f"),
            "periods": table_html(period_table, float_format="%.2f"),
            "gap": table_html((gap * 100).rename(columns=str.title), float_format="%.0f"),
            "tiers": table_html(tier_periods),
            "events": table_html(event_table, index=False, float_format="%.1f"),
            "coverage": table_html(coverage),
        },
    }

    env = Environment(
        loader=FileSystemLoader(STUDY_DIR / "templates"), autoescape=select_autoescape()
    )
    # Format numbers with a true minus sign (U+2212), as in print typography.
    env.filters["num"] = lambda value, spec="%.0f": (spec % value).replace("-", "\u2212")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # The report is the study's landing page; the dashboard is linked from it.
    for template, filename in [("report.html", "index.html"), ("dashboard.html", "dashboard.html")]:
        html = env.get_template(template).render(**context)
        (OUT_DIR / filename).write_text(html)
        print(f"Wrote {OUT_DIR / filename} ({len(html) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
