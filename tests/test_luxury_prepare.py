import numpy as np
import pandas as pd
import pytest

from studies.luxury_drivers.prepare import convert_to_eur, weekly_log_returns
from studies.luxury_drivers.validate import corporate_action_flags, extreme_moves, stale_runs


def make_fx(dates, **rates):
    return pd.DataFrame(
        [(d, ccy, r) for ccy, r in rates.items() for d in dates],
        columns=["date", "currency", "per_eur"],
    )


def test_convert_to_eur_handles_chf_pence_and_eur():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    wide = pd.DataFrame(
        {"A.SW": [100.0, 100.0], "B.L": [850.0, 850.0], "C.PA": [50.0, 50.0]}, dates
    )
    fx = make_fx(dates, CHF=0.95, GBP=0.85)

    eur = convert_to_eur(wide, fx, {"A.SW": "CHF", "B.L": "GBp", "C.PA": "EUR"})

    assert eur["A.SW"].iloc[0] == pytest.approx(100 / 0.95)
    assert eur["B.L"].iloc[0] == pytest.approx(8.50 / 0.85)  # 850 pence = £8.50 = €10
    assert eur["C.PA"].iloc[0] == 50.0


def test_convert_to_eur_forward_fills_ecb_holidays():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    wide = pd.DataFrame({"A.SW": [100.0, 100.0]}, dates)
    fx = make_fx(dates[:1], CHF=0.5)  # no ECB rate on the second day

    eur = convert_to_eur(wide, fx, {"A.SW": "CHF"})

    assert eur["A.SW"].tolist() == [200.0, 200.0]


def test_weekly_log_returns_uses_last_price_of_each_week():
    # Mon 1 Jan 2024 .. Fri 12 Jan 2024; price doubles from week 1's Friday to week 2's Friday.
    days = pd.bdate_range("2024-01-01", "2024-01-12")
    prices = pd.DataFrame({"X": [1, 1, 1, 1, 10, 3, 3, 3, 3, 20]}, days, dtype=float)

    r = weekly_log_returns(prices)

    assert len(r) == 1
    assert r["X"].iloc[0] == pytest.approx(np.log(2))


def test_quality_checks_flag_known_problems():
    dates = pd.bdate_range("2024-01-01", periods=6)
    prices = pd.DataFrame(
        {
            "date": dates,
            "ticker": "X",
            "close": [10, 10, 10, 10, 13, 13.0],
            "adj_close": [9, 9, 9, 9, 11.7, 12.35],  # ratio jumps ~5.6% on the last day
        }
    )

    assert stale_runs(prices)["X"] == 3
    assert extreme_moves(prices)["date"].tolist() == [dates[4]]
    assert corporate_action_flags(prices)["date"].tolist() == [dates[5]]
