import numpy as np
import pandas as pd
import pytest

from studies.luxury_drivers.analysis import (
    event_car,
    event_path,
    factor_regression,
    out_of_sample_abnormal,
    rolling_betas,
)

FACTORS = ["market", "eurusd", "china"]


@pytest.fixture
def synthetic_returns():
    """Stock built from known betas (1.2, 0.3, 0.5) plus small noise."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2014-01-03", periods=600, freq="W-FRI")
    f = pd.DataFrame(rng.normal(0, 0.02, (600, 3)), idx, FACTORS)
    f["stock"] = 1.2 * f["market"] + 0.3 * f["eurusd"] + 0.5 * f["china"]
    f["stock"] += rng.normal(0, 0.002, 600)
    return f


def test_factor_regression_recovers_known_betas(synthetic_returns):
    res = factor_regression(synthetic_returns, "stock")

    assert res["beta_market"] == pytest.approx(1.2, abs=0.02)
    assert res["beta_eurusd"] == pytest.approx(0.3, abs=0.02)
    assert res["beta_china"] == pytest.approx(0.5, abs=0.02)
    assert res["r2"] > 0.95
    assert res["n_obs"] == 600


def test_rolling_betas_stable_when_true_betas_constant(synthetic_returns):
    rb = rolling_betas(synthetic_returns, "stock", window=104)

    assert len(rb) == 600 - 103
    assert rb["market"].between(1.15, 1.25).all()


def test_abnormal_return_picks_up_shock_and_ignores_alpha(synthetic_returns):
    r = synthetic_returns.copy()
    r.loc[:"2019-12-31", "stock"] += 0.003  # pre-period alpha: must not be extrapolated
    shock_week = r.index[r.index > "2020-01-01"][10]
    r.loc[shock_week, "stock"] += -0.10  # one-off company-specific drop

    car = out_of_sample_abnormal(r, "stock", "2019-12-31")

    step = car.loc[shock_week] - car.shift(1).loc[shock_week]
    assert step == pytest.approx(-0.10, abs=0.01)
    # Extrapolating the alpha would push the end value ~0.87 below the shock.
    assert car.iloc[-1] == pytest.approx(-0.10, abs=0.1)


def make_log_prices(seed: int, beta: float = 1.0, shock_day: str | None = None, shock=0.0):
    """Daily log prices for a market and a stock with a known beta and an optional shock."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2023-01-02", periods=400)
    market_ret = pd.Series(rng.normal(0, 0.01, 400), days)
    stock_ret = 0.0005 + beta * market_ret + rng.normal(0, 0.005, 400)
    if shock_day:
        stock_ret[pd.Timestamp(shock_day)] += shock
    return stock_ret.cumsum(), market_ret.cumsum()


def test_event_car_detects_shock_on_next_trading_day_after_weekend():
    stock, market = make_log_prices(7, beta=1.1, shock_day="2024-03-04", shock=0.08)

    res = event_car(stock, market, "2024-03-02", window=(0, 0))  # Saturday announcement

    assert str(res["event_trading_day"]) == "2024-03-04"
    assert res["car"] == pytest.approx(0.08, abs=0.015)
    assert res["t"] > 10


def test_event_car_aligns_when_market_misses_a_day():
    stock, market = make_log_prices(11, shock_day="2024-03-05", shock=0.05)
    market = market.drop(pd.Timestamp("2024-03-04"))  # index not published on one day

    res = event_car(stock, market, "2024-03-05", window=(0, 0))

    # The event-day return spans 1 Mar -> 5 Mar for BOTH series, so the shock is still recovered.
    assert res["car"] == pytest.approx(0.05, abs=0.015)


def test_event_path_is_zero_the_day_before_the_event():
    stock, market = make_log_prices(3)

    path = event_path(stock, market, "2024-03-04")

    assert path.loc[-1] == 0
    assert path.index[0] == -10 and path.index[-1] == 20
