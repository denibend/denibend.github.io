"""Run the Study 02 analyses and write the report and dashboard pages.

Run:  uv run python -m studies.luxury_wallet.build
Needs: `uv run python -m studies.luxury_wallet.fetch` and Study 01's fetch (for tier returns).
Output: docs/studies/luxury-wallet/index.html (report) and dashboard.html
"""

import json
from datetime import date

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from plotly.offline import get_plotlyjs_version

from studies.luxury_drivers import analysis as s1_analysis
from studies.luxury_drivers import prepare as s1_prepare
from studies.luxury_drivers.config import SAMPLE_START, STOCKS
from studies.luxury_wallet import analysis, charts, prepare
from studies.luxury_wallet.config import RAW_DIR, STUDY_DIR

ROOT = STUDY_DIR.parents[1]
OUT_DIR = ROOT / "docs" / "studies" / "luxury-wallet"
PUBLISHED = "2026-10-24"  # set at first publication; stays fixed when data is refreshed
COVID = ("2020-01-01", "2021-12-31")
HK_EXCLUDE = ("2020-01-01", "2024-02-29")  # border closure and its base effects
# Driver key -> column name in each region's dataset.
US_DRIVERS = {"income": "income_real", "equity": "wealth_equity", "housing": "wealth_housing"}
EU_DRIVERS = {"income": "income", "equity": "wealth_equity", "housing": "wealth_housing"}
PLOT_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toImage"],
}


def excluding(
    df: pd.DataFrame, window: tuple[str, str], level: int | str | None = None
) -> pd.DataFrame:
    dates = df.index.get_level_values(level) if level is not None else df.index
    return df[(dates < window[0]) | (dates > window[1])]


def typical_effects(
    results: pd.DataFrame, growth: pd.DataFrame, names: dict, sd_from: str, level: str | None = None
) -> pd.DataFrame:
    """Elasticity x one standard deviation of the driver's quarterly growth (excl. COVID), in %."""
    g = excluding(growth, COVID, level)
    g = g[(g.index.get_level_values(level) if level else g.index) >= sd_from]
    sd = g[list(names.values())].std()
    out = results.copy()
    inverse = {v: k for k, v in names.items()}
    out["driver"] = out["driver"].map(inverse)
    out["effect"] = out.apply(lambda r: r["elasticity"] * sd[names[r["driver"]]] * 100, axis=1)
    return out


def h1() -> dict:
    us = prepare.build_us_quarterly()
    g_us = prepare.log_growth(us)
    us_cats = {
        "spend_jewelry_watches": "US · Jewellery & watches",
        "spend_luggage": "US · Luggage & leather goods",
        "spend_clothing_footwear": "US · Clothing & footwear",
        "spend_goods": "US · All goods (benchmark)",
    }
    r_us = pd.concat(
        [
            analysis.distributed_lag_elasticities(g_us, c, list(US_DRIVERS.values()), exclude=COVID)
            for c in us_cats
        ]
    )
    e_us = typical_effects(r_us, g_us, US_DRIVERS, "1990-10-01")
    e_us["category"] = e_us["target"].map(us_cats)

    eu = prepare.build_eu_quarterly()
    g_eu = np.log(eu).groupby(level="geo").diff()
    eu_cats = {
        "spend_semidurable": "EU · Semi-durables (clothing, footwear, travel goods)",
        "spend_durable": "EU · Durables (incl. jewellery & watches, mostly cars)",
        "spend_total": "EU · All consumption (benchmark)",
    }
    r_eu = pd.concat(
        [
            analysis.panel_distributed_lag(g_eu, c, list(EU_DRIVERS.values()), exclude=COVID)
            for c in eu_cats
        ]
    )
    e_eu = typical_effects(r_eu, g_eu, EU_DRIVERS, "2009-01-01", level="date")
    e_eu["category"] = e_eu["target"].map(eu_cats)
    effects = pd.concat([e_us, e_eu])

    dfa = pd.read_csv(RAW_DIR / "dfa_networth_by_wealth.csv")
    last = dfa[dfa["Date"] == dfa["Date"].max()].set_index("Category")
    cols = {
        "Corporate equities and mutual fund shares": "Equities & funds",
        "Real estate": "Real estate",
    }
    groups = {
        "Top 1%": ["TopPt1", "RemainingTop1"],
        "Next 9%": ["Next9"],
        "Next 40%": ["Next40"],
        "Bottom 50%": ["Bottom50"],
    }
    held = pd.DataFrame({g: last.loc[c, list(cols)].sum() for g, c in groups.items()}).rename(
        index=cols
    )
    held = held.div(held.sum(axis=1), axis=0) * 100

    pick = effects.set_index(["category", "driver"])
    return {
        "effects": effects,
        "holdings": held,
        "holdings_date": dfa["Date"].max(),
        "n_us": int(r_us["n_obs"].iloc[0]),
        "n_eu": int(r_eu["n_obs"].iloc[0]),
        "jw_equity": pick.loc[("US · Jewellery & watches", "equity"), "effect"],
        "jw_income": pick.loc[("US · Jewellery & watches", "income"), "effect"],
        "jw_income_el": pick.loc[("US · Jewellery & watches", "income"), "elasticity"],
        "cl_equity_us": pick.loc[("US · Clothing & footwear", "equity"), "effect"],
        "cl_income_us": pick.loc[("US · Clothing & footwear", "income"), "effect"],
        "sd_equity_eu": pick.loc[(eu_cats["spend_semidurable"], "equity"), "effect"],
        "sd_income_eu": pick.loc[(eu_cats["spend_semidurable"], "income"), "effect"],
        "goods_equity_us": pick.loc[("US · All goods (benchmark)", "equity"), "effect"],
        "top10_equities": held.loc["Equities & funds", ["Top 1%", "Next 9%"]].sum(),
        "mid_housing": held.loc["Real estate", ["Next 40%", "Bottom 50%"]].sum(),
    }


def h2() -> dict:
    m = prepare.build_tier_monthly()
    factors = ["market", "china", "eurusd", "confidence_change", "us_income_growth"]
    samples = {
        "2014–2019": m.loc[:"2019-12-01"],
        "2022–2026": m.loc["2022-01-01":],
        "2014–2026 excl. 2020–21": excluding(m, COVID),
        "All months incl. COVID": m,
    }
    rows = []
    for label, d in samples.items():
        r = s1_analysis.factor_regression(d, "top_minus_aspirational", factors, hac_lags=3)
        b, t = r["beta_confidence_change"], r["t_confidence_change"]
        rows.append({"sample": label, "coef": b, "t": t, "se": abs(b / t), "n": int(r["n_obs"])})
    res = pd.DataFrame(rows)
    sd_conf = excluding(m, COVID)["confidence_change"].std()
    late = res.set_index("sample").loc["2022–2026"]
    return {
        "confidence": res,
        "late_coef": late["coef"] * 100,
        "late_t": late["t"],
        "early_t": res.set_index("sample").loc["2014–2019", "t"],
        "typical_move": abs(late["coef"]) * sd_conf * 100,
        "sd_conf": sd_conf,
    }


def h3() -> dict:
    bea = pd.read_csv(RAW_DIR / "bea_pce_monthly.csv", parse_dates=["date"])
    w = bea.pivot_table(index="date", columns=["measure", "category"], values="value")
    real = prepare.real_spending(w["nominal_musd_saar"], w["price_index"]).loc["2005":]
    labels = {
        "jewelry_watches": ("Jewellery & watches", "Luxury-type goods"),
        "luggage": ("Luggage & leather goods", "Luxury-type goods"),
        "clothing_footwear": ("Clothing & footwear", "Luxury-type goods"),
        "air_transport": ("Air travel", "Experiences"),
        "accommodations": ("Hotels", "Experiences"),
        "package_tours": ("Package tours", "Experiences"),
        "food_services": ("Restaurants", "Experiences"),
        "recreation_services": ("Recreation", "Experiences"),
    }
    dev = pd.DataFrame(
        {
            c: analysis.trend_deviation(real[c], "2010-01-01", "2019-12-01")["deviation_pct"]
            .resample("YS")
            .mean()
            for c in labels
        }
    )
    dev.index = dev.index.year
    dev = dev.loc[2016:]
    dev.attrs["labels"] = labels
    latest = int(dev.index.max())

    baskets = prepare.us_baskets_monthly().loc["2005":]
    share = analysis.trend_deviation(baskets["share_experiences"] * 100, "2010-01-01", "2019-12-01")

    eu = prepare.build_eu_quarterly()
    eu_dev, eu_year = {}, None
    for geo in ["DE", "FR", "IT", "ES"]:
        s = eu.xs(geo, level="geo")
        row = {}
        for col, lab in [
            ("spend_semidurable", "Semi-durable goods"),
            ("spend_services", "Services"),
        ]:
            d = analysis.trend_deviation(s[col], "2011-01-01", "2019-10-01")["deviation_pct"]
            annual = d.groupby(d.index.year).agg(["mean", "count"])
            annual = annual[annual["count"] == 4]  # latest complete year only
            row[lab] = annual["mean"].iloc[-1]
            eu_year = int(annual.index[-1])
        eu_dev[geo] = row
    eu_dev = pd.DataFrame(eu_dev).T.rename(
        index={"DE": "Germany", "FR": "France", "IT": "Italy", "ES": "Spain"}
    )

    t = pd.read_csv(RAW_DIR / "eurostat_tourist_nights.csv")
    t["time"] = t["time"].str[:4].astype(int)
    nights = (
        t[t["geo"].isin(["DE", "FR", "IT", "ES"])]
        .groupby(["geo", "time", "c_resid"])["value"]
        .sum(min_count=12)
        .unstack("c_resid")
        .rename(columns={"FOR": "nights_foreign", "DOM": "nights_domestic"})
    )
    panel = prepare.build_eu_annual().join(nights, how="inner")
    gp = np.log(panel).groupby(level="geo").diff()
    comp_cats = {
        "spend_CP112": "Accommodation",
        "spend_CP111": "Restaurants",
        "spend_CP132": "Personal effects (jewellery, watches, travel goods)",
        "spend_CP03": "Clothing & footwear",
    }
    comp = pd.concat(
        [
            analysis.panel_elasticities(
                gp, c, ["nights_foreign", "nights_domestic", "income"], exclude_years=(2020, 2021)
            )
            for c in comp_cats
        ]
    )
    comp["category"] = comp["target"].map(comp_cats)
    comp = comp[comp["driver"] == "nights_foreign"].set_index("category")

    hk = prepare.build_hk_monthly().loc["2004-10-01":]
    ann = hk.resample("YS").sum(min_count=12)
    ann.index = ann.index.year
    per_visitor = (ann["jewellery_sales"] * 1e6 / ann["mainland_visitors"]).dropna()
    per_visitor = per_visitor.drop([2020, 2021, 2022], errors="ignore")
    g_hk = np.log(hk).diff(12)
    hk_drivers = ["mainland_visitors", "shanghai", "hkd_per_cny", "gold_usd"]
    hk_model = analysis.distributed_lag_elasticities(
        g_hk, "jewellery_sales", hk_drivers, lags=0, exclude=HK_EXCLUDE, hac_lags=12
    ).set_index("driver")
    oos = analysis.out_of_sample_prediction(
        g_hk, "jewellery_sales", hk_drivers, "2019-12-01", "2024-03-01"
    )

    return {
        "dev": dev,
        "latest": latest,
        "share": share,
        "eu_dev": eu_dev,
        "eu_year": eu_year,
        "comp": comp,
        "per_visitor": per_visitor,
        "hk_model": hk_model,
        "oos": oos,
        "jw_dev": dev.loc[latest, "jewelry_watches"],
        "air_dev": dev.loc[latest, "air_transport"],
        "air_dev_2024": dev.loc[2024, "air_transport"],
        "hotel_dev": dev.loc[latest, "accommodations"],
        "exp_share_dev": share["deviation_pct"].loc[str(latest)].mean(),
        "exp_share_now": share["actual"].loc[str(latest)].mean(),
        "exp_share_2019": share["actual"].loc["2019"].mean(),
        "pv_peak_year": int(per_visitor.idxmax()),
        "pv_peak": per_visitor.max(),
        "pv_last_year": int(per_visitor.index.max()),
        "pv_last": per_visitor.iloc[-1],
        "oos_early": oos.loc[:"2025-02-01", "gap"].mean() * 100,
        "oos_late": oos.loc["2025-03-01":, "gap"].mean() * 100,
        "n_hk": int(hk_model["n_obs"].iloc[0]),
        "r2_hk": hk_model["r2"].iloc[0],
    }


def h4() -> dict:
    weekly = s1_prepare.build_weekly_dataset(SAMPLE_START).rename(
        columns={t: n for t, (n, _) in STOCKS.items()}
    )
    names = [n for n, _ in STOCKS.values()]
    gap = s1_analysis.sector_vs_brand_gap(weekly, names, "2022-12-31") * 100
    shares = prepare.region_shares()
    x = pd.DataFrame(
        {
            "asia_2022": shares["asia"].xs(2022, level="fiscal_year"),
            "asia_2025": shares["asia"].xs(2025, level="fiscal_year"),
            "europe_2022": shares["europe"].xs(2022, level="fiscal_year"),
            "americas_2022": shares["americas"].xs(2022, level="fiscal_year"),
        }
    ).join(gap.rename(columns={"brand": "brand_gap", "total": "total_gap"}))
    x["asia_change"] = x["asia_2025"] - x["asia_2022"]
    tests = {}
    for v in ["asia_2022", "asia_change", "europe_2022", "americas_2022"]:
        tests[v] = analysis.spearman_permutation(x[v].values, x["brand_gap"].values)
    n_rows = len(pd.read_csv(prepare.REGIONAL_REVENUE_CSV))
    return {
        "shares": shares,
        "x": x.sort_values("brand_gap"),
        "tests": tests,
        "n_rows": n_rows,
        "rho": tests["asia_2022"][0],
        "p": tests["asia_2022"][1],
    }


def fig_html(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config=PLOT_CONFIG)


def table_html(df: pd.DataFrame, **kwargs) -> str:
    return df.to_html(classes="data", border=0, na_rep="–", **kwargs)


def main() -> None:
    r1, r2, r3, r4 = h1(), h2(), h3(), h4()

    effects_table = r1["effects"].pivot_table(
        index="category", columns="driver", values=["elasticity", "t", "effect"]
    )
    effects_table.columns = [
        f"{charts.DRIVER_LABELS[d].split(' (')[0]} · {m}" for m, d in effects_table.columns
    ]
    comp_table = r3["comp"][["elasticity", "t", "n_obs"]].rename(columns={"n_obs": "n"})
    hk_table = r3["hk_model"][["elasticity", "t"]].rename(
        index={
            "mainland_visitors": "Mainland visitor arrivals",
            "hkd_per_cny": "Renminbi buying power (HKD per CNY)",
            "shanghai": "Shanghai Composite",
            "gold_usd": "Gold price (control)",
        }
    )
    h4_table = r4["x"][
        ["asia_2022", "europe_2022", "americas_2022", "asia_change", "brand_gap", "total_gap"]
    ]
    h4_tests = pd.DataFrame(r4["tests"], index=["Spearman ρ", "permutation p"]).T
    dev_table = r3["dev"].rename(columns={k: v[0] for k, v in r3["dev"].attrs["labels"].items()})

    context = {
        "published": date.fromisoformat(PUBLISHED).strftime("%-d %B %Y"),
        "built": date.today().isoformat(),
        "retrieved": json.loads((RAW_DIR / "provenance.json").read_text())["retrieved_utc"][:10],
        "plotly_version": get_plotlyjs_version(),
        "h1": r1,
        "h2": r2,
        "h3": r3,
        "h4": r4,
        "charts": {
            "effects": fig_html(charts.driver_effects(r1["effects"])),
            "holdings": fig_html(charts.holdings(r1["holdings"])),
            "confidence": fig_html(charts.confidence_by_sample(r2["confidence"])),
            "deviation": fig_html(charts.category_deviation(r3["dev"])),
            "share": fig_html(charts.share_vs_trend(r3["share"])),
            "eu_shift": fig_html(charts.eu_shift(r3["eu_dev"])),
            "per_visitor": fig_html(charts.hk_per_visitor(r3["per_visitor"])),
            "hk_oos": fig_html(charts.hk_actual_vs_model(r3["oos"])),
            "mix": fig_html(charts.regional_mix(r4["shares"], [2019, 2022, 2025])),
            "scatter": fig_html(charts.asia_vs_gap(r4["x"])),
        },
        "tables": {
            "effects": table_html(effects_table, float_format="%.2f"),
            "holdings": table_html(r1["holdings"], float_format="%.0f"),
            "confidence": table_html(
                r2["confidence"].set_index("sample").assign(coef=lambda d: d.coef * 100),
                float_format="%.2f",
            ),
            "deviation": table_html(dev_table, float_format="%+.1f"),
            "eu_shift": table_html(r3["eu_dev"], float_format="%+.1f"),
            "complement": table_html(comp_table, float_format="%.2f"),
            "hk": table_html(hk_table, float_format="%.2f"),
            "per_visitor": table_html(
                r3["per_visitor"].rename("HK$ per mainland visitor").to_frame(), float_format="%.0f"
            ),
            "h4": table_html(h4_table, float_format="%.1f"),
            "h4_tests": table_html(h4_tests, float_format="%.2f"),
        },
    }
    env = Environment(
        loader=FileSystemLoader(STUDY_DIR / "templates"), autoescape=select_autoescape()
    )
    env.filters["num"] = lambda value, spec="%.0f": (spec % value).replace("-", "−")
    env.filters["thousands"] = lambda value: f"{value:,.0f}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for template, filename in [("report.html", "index.html"), ("dashboard.html", "dashboard.html")]:
        html = env.get_template(template).render(**context)
        (OUT_DIR / filename).write_text(html)
        print(f"Wrote {OUT_DIR / filename} ({len(html) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
