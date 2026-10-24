import numpy as np
import pandas as pd
import pytest

from studies.luxury_wallet.analysis import distributed_lag_elasticities
from studies.luxury_wallet.prepare import (
    parse_dfa_quarter,
    real_spending,
    to_quarterly,
    wealth_groups,
)


def test_to_quarterly_averages_months():
    idx = pd.date_range("2024-01-01", periods=6, freq="MS")
    q = to_quarterly(pd.DataFrame({"x": [1, 2, 3, 10, 20, 30]}, idx))

    assert q["x"].tolist() == [2, 20]
    assert q.index[1] == pd.Timestamp("2024-04-01")


def test_real_spending_deflates_by_own_price_index():
    nominal = pd.DataFrame({"a": [100.0, 110.0]})
    prices = pd.DataFrame({"a": [100.0, 110.0]})  # all growth is inflation

    assert real_spending(nominal, prices)["a"].tolist() == pytest.approx([100.0, 100.0])


def test_wealth_groups_collapse_dfa_categories():
    dfa = pd.DataFrame(
        {
            "Date": ["2024:Q1"] * 5,
            "Category": ["TopPt1", "RemainingTop1", "Next9", "Next40", "Bottom50"],
            "Net worth": [10, 20, 30, 40, 5],
        }
    )
    g = wealth_groups(dfa)

    assert g.index[0] == pd.Timestamp("2024-01-01")
    assert g.iloc[0].to_dict() == {"wealth_top1": 30, "wealth_next9": 30, "wealth_bottom90": 45}
    assert parse_dfa_quarter(pd.Series(["1989:Q3"]))[0] == pd.Timestamp("1989-07-01")


def test_distributed_lag_recovers_cumulative_elasticities():
    rng = np.random.default_rng(1)
    idx = pd.date_range("1960-01-01", periods=240, freq="QS")
    g = pd.DataFrame(rng.normal(0, 0.01, (240, 2)), idx, ["income", "wealth"])
    # True response spread over lags: income 0.6 + 0.3 = 0.9 in total; wealth 0.05 + 0.10 = 0.15.
    g["spend"] = (
        0.6 * g["income"]
        + 0.3 * g["income"].shift(1)
        + 0.05 * g["wealth"]
        + 0.10 * g["wealth"].shift(2)
        + rng.normal(0, 0.001, 240)
    )

    res = distributed_lag_elasticities(g, "spend", ["income", "wealth"]).set_index("driver")

    # A sum of five estimated lags carries five lags' worth of noise, so judge each estimate
    # against its own standard error. (Over 200 seeds: unbiased, 95% CI coverage ~94%.)
    for driver, true in [("income", 0.9), ("wealth", 0.15)]:
        assert abs(res.loc[driver, "elasticity"] - true) < 3 * res.loc[driver, "se"]
    assert res.loc["income", "t"] > 10


def test_distributed_lag_exclusion_drops_quarters():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2015-01-01", periods=40, freq="QS")
    g = pd.DataFrame(rng.normal(0, 0.01, (40, 2)), idx, ["x", "y"])

    full = distributed_lag_elasticities(g, "y", ["x"], lags=1)
    cut = distributed_lag_elasticities(g, "y", ["x"], lags=1, exclude=("2020-01-01", "2021-12-31"))

    assert full.loc[0, "n_obs"] - cut.loc[0, "n_obs"] == 8


def test_to_quarterly_drops_incomplete_quarter():
    idx = pd.date_range("2024-01-01", periods=5, freq="MS")  # Q1 complete, Q2 has 2 months
    q = to_quarterly(pd.DataFrame({"x": [1.0, 2, 3, 10, 20]}, idx))

    assert q["x"].iloc[0] == 2
    assert np.isnan(q["x"].iloc[1])


def test_wealth_by_asset_sums_across_groups():
    from studies.luxury_wallet.prepare import wealth_by_asset

    dfa = pd.DataFrame(
        {
            "Date": ["2024:Q1", "2024:Q1"],
            "Category": ["TopPt1", "Bottom50"],
            "Corporate equities and mutual fund shares": [90, 10],
            "Real estate": [5, 45],
        }
    )
    w = wealth_by_asset(dfa)

    assert w.iloc[0].to_dict() == {"wealth_equity": 100, "wealth_housing": 50}


def test_panel_elasticities_with_fixed_effects():
    from studies.luxury_wallet.analysis import panel_elasticities

    rng = np.random.default_rng(3)
    rows = []
    for i, geo in enumerate(["A", "B", "C", "D", "E", "F"]):
        for year in range(2011, 2026):
            inc, wea = rng.normal(0, 0.02), rng.normal(0, 0.05)
            # Country-specific baseline growth (fixed effect) + true elasticities 1.2 and 0.3.
            y = 0.01 * i + 1.2 * inc + 0.3 * wea + rng.normal(0, 0.002)
            rows.append({"geo": geo, "time": year, "y": y, "income": inc, "wealth": wea})
    g = pd.DataFrame(rows).set_index(["geo", "time"])

    res = panel_elasticities(g, "y", ["income", "wealth"], exclude_years=(2020, 2021))
    r = res.set_index("driver")

    assert abs(r.loc["income", "elasticity"] - 1.2) < 3 * r.loc["income", "se"]
    assert abs(r.loc["wealth", "elasticity"] - 0.3) < 3 * r.loc["wealth", "se"]
    assert res["n_obs"].iloc[0] == 6 * 13


def test_annual_wealth_keeps_missing_and_drops_partial_years():
    from studies.luxury_wallet.prepare import annual_wealth

    rows = []
    for q in range(1, 5):  # 2023: full year; deciles summed per quarter
        rows += [{"geo": "AA", "group": "mid", "TIME_PERIOD": f"2023-Q{q}", "OBS_VALUE": 10.0}] * 2
    rows += [{"geo": "AA", "group": "mid", "TIME_PERIOD": "2022-Q4", "OBS_VALUE": 20.0}] * 2
    rows += [
        {"geo": "BB", "group": "mid", "TIME_PERIOD": f"2023-Q{q}", "OBS_VALUE": float("nan")}
        for q in range(1, 5)
    ]
    w = annual_wealth(pd.DataFrame(rows))["mid"]

    assert w[("AA", 2023)] == 20.0  # two components of 10 summed, averaged over 4 quarters
    assert np.isnan(w[("AA", 2022)])  # only Q4 available: not a full-year level
    assert np.isnan(w[("BB", 2023)])  # missing stays missing, never 0


def test_panel_distributed_lag_builds_lags_within_each_country():
    from studies.luxury_wallet.analysis import panel_distributed_lag

    rng = np.random.default_rng(4)
    frames = []
    for i, geo in enumerate(["A", "B", "C", "D", "E"]):
        idx = pd.MultiIndex.from_product(
            [[geo], pd.date_range("2010-01-01", periods=60, freq="QS")], names=["geo", "date"]
        )
        f = pd.DataFrame(rng.normal(0, 0.01, (60, 2)), idx, ["income", "wealth"])
        # Lagged effect: if lags leaked across countries, the first rows of B would use A's data.
        f["y"] = (
            0.002 * i + 0.8 * f["income"] + 0.2 * f["wealth"].shift(1) + rng.normal(0, 0.001, 60)
        )
        frames.append(f)
    g = pd.concat(frames)

    r = panel_distributed_lag(g, "y", ["income", "wealth"]).set_index("driver")

    assert abs(r.loc["income", "elasticity"] - 0.8) < 3 * r.loc["income", "se"]
    assert abs(r.loc["wealth", "elasticity"] - 0.2) < 3 * r.loc["wealth", "se"]
    assert r["n_obs"].iloc[0] == 5 * (60 - 4)  # 4 lags use up each country's first 4 quarters


def test_hkd_per_cny_cross_rate():
    from studies.luxury_wallet.prepare import hkd_per_cny

    fx = pd.DataFrame(
        {"CURRENCY": ["CNY", "HKD"], "TIME_PERIOD": ["2025-01", "2025-01"], "OBS_VALUE": [7.6, 8.1]}
    )
    rate = hkd_per_cny(fx)

    assert rate.index[0] == pd.Timestamp("2025-01-01")
    assert rate.iloc[0] == pytest.approx(8.1 / 7.6)  # (HKD/EUR) / (CNY/EUR) = HKD per CNY
