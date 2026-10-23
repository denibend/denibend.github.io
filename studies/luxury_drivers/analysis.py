"""Factor-model calculations for Study 01. Pure functions: DataFrames in, DataFrames out, no I/O."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS

FACTORS = ["market", "eurusd", "china"]


def factor_regression(
    returns: pd.DataFrame, stock: str, factors: list[str] = FACTORS, hac_lags: int = 4
) -> pd.Series:
    """OLS of one stock's returns on the factors, with Newey-West (HAC) standard errors.

    Returns alpha, betas, t-statistics, p-values, R-squared and the number of observations.
    """
    data = returns[[stock, *factors]].dropna()
    model = sm.OLS(data[stock], sm.add_constant(data[factors])).fit(
        cov_type="HAC", cov_kwds={"maxlags": hac_lags}
    )
    names = {"const": "alpha"}
    out = {}
    for name in ["const", *factors]:
        label = names.get(name, name)
        out[f"beta_{label}" if label != "alpha" else "alpha"] = model.params[name]
        out[f"t_{label}"] = model.tvalues[name]
        out[f"p_{label}"] = model.pvalues[name]
    out["r2"] = model.rsquared
    out["n_obs"] = int(model.nobs)
    return pd.Series(out, name=stock)


def factor_table(
    returns: pd.DataFrame, stocks: list[str], factors: list[str] = FACTORS
) -> pd.DataFrame:
    """One row of regression results per stock."""
    return pd.DataFrame([factor_regression(returns, s, factors) for s in stocks])


def rolling_betas(
    returns: pd.DataFrame, stock: str, factors: list[str] = FACTORS, window: int = 104
) -> pd.DataFrame:
    """Factor betas re-estimated on a moving window (default 104 weeks = 2 years)."""
    data = returns[[stock, *factors]].dropna()
    fit = RollingOLS(data[stock], sm.add_constant(data[factors]), window=window).fit()
    return fit.params.drop(columns="const").dropna()


def out_of_sample_abnormal(
    returns: pd.DataFrame,
    stock: str,
    estimation_end: str,
    factors: list[str] = FACTORS,
) -> pd.Series:
    """Cumulative abnormal log return after `estimation_end`.

    Betas are estimated only on data up to `estimation_end`; afterwards each week's abnormal
    return is actual minus factor-implied return (betas x factor returns). The estimation-period
    alpha is deliberately NOT extrapolated: luxury's 2014-2022 outperformance is the thing being
    questioned, so assuming it continues would make any slowdown look like a collapse.
    Summing log returns gives the cumulative gap: positive = beat what factor exposures implied.
    """
    data = returns[[stock, *factors]].dropna()
    train = data.loc[:estimation_end]
    test = data.loc[data.index > pd.Timestamp(estimation_end)]
    betas = sm.OLS(train[stock], sm.add_constant(train[factors])).fit().params[factors]
    return (test[stock] - test[factors] @ betas).cumsum().rename(stock)


def equal_weight(log_returns: pd.DataFrame) -> pd.Series:
    """Log return of an equal-weighted portfolio rebalanced every period.

    Averages simple returns (exp(r) - 1) and converts back to log; averaging log returns
    directly would understate the portfolio's return.
    """
    return np.log(np.exp(log_returns).mean(axis=1))


def leave_one_out_peers(log_returns: pd.DataFrame, stocks: list[str], stock: str) -> pd.Series:
    """Equal-weighted return of all other stocks: a sector factor that excludes the stock itself."""
    return equal_weight(log_returns[[s for s in stocks if s != stock]]).rename("peers")


def sector_vs_brand_gap(
    returns: pd.DataFrame, stocks: list[str], estimation_end: str, factors: list[str] = FACTORS
) -> pd.DataFrame:
    """Split each stock's cumulative abnormal return after `estimation_end` into two parts.

    - total: gap versus market/FX/China factors (`out_of_sample_abnormal`)
    - brand: gap after also controlling for the leave-one-out luxury peer factor
    - sector: total minus brand, i.e. the part shared with luxury peers
    Values are cumulative log returns at the last date.
    """
    rows = []
    for stock in stocks:
        with_peers = returns.assign(peers=leave_one_out_peers(returns, stocks, stock))
        total = out_of_sample_abnormal(returns, stock, estimation_end, factors).iloc[-1]
        brand = out_of_sample_abnormal(with_peers, stock, estimation_end, [*factors, "peers"]).iloc[
            -1
        ]
        rows.append({"stock": stock, "total": total, "sector": total - brand, "brand": brand})
    return pd.DataFrame(rows).set_index("stock")


def tier_returns(log_returns: pd.DataFrame, tiers: dict[str, list[str]]) -> pd.DataFrame:
    """Equal-weighted log returns for each tier."""
    return pd.DataFrame({tier: equal_weight(log_returns[names]) for tier, names in tiers.items()})


def _event_frame(
    stock: pd.Series, market: pd.Series, event_day: str, estimation: tuple[int, int]
) -> tuple[pd.DataFrame, int, pd.Series, float]:
    """Align log prices, locate the event and fit the market model on the estimation window.

    Takes log PRICES: they are aligned on common trading days before differencing, so stock and
    market returns always cover the same period. The event is placed on the first common trading
    day on/after `event_day`. Returns the aligned returns, the event's row position, the
    market-model parameters and the residual standard deviation.
    """
    data = pd.concat({"stock": stock, "market": market}, axis=1).dropna().diff().dropna()
    pos = int(data.index.searchsorted(pd.Timestamp(event_day)))
    est = data.iloc[pos + estimation[0] : pos + estimation[1] + 1]
    fit = sm.OLS(est["stock"], sm.add_constant(est["market"])).fit()
    return data, pos, fit.params, float(np.sqrt(fit.mse_resid))


def event_car(
    stock: pd.Series,
    market: pd.Series,
    event_day: str,
    window: tuple[int, int] = (-1, 1),
    estimation: tuple[int, int] = (-250, -21),
) -> pd.Series:
    """Cumulative abnormal return (market model) over `window` trading days around the event.

    `stock` and `market` are daily LOG PRICES (see `_event_frame`).
    t-statistic assumes independent abnormal returns: CAR / (residual sd x sqrt(window length)).
    """
    data, pos, params, sigma = _event_frame(stock, market, event_day, estimation)
    ev = data.iloc[pos + window[0] : pos + window[1] + 1]
    abnormal = ev["stock"] - (params["const"] + params["market"] * ev["market"])
    car = float(abnormal.sum())
    return pd.Series(
        {
            "event_trading_day": data.index[pos].date(),
            "car": car,
            "t": car / (sigma * np.sqrt(len(ev))),
            "sigma": sigma * np.sqrt(len(ev)),  # standard error of the CAR
            "days": len(ev),
        }
    )


def event_path(
    stock: pd.Series,
    market: pd.Series,
    event_day: str,
    span: tuple[int, int] = (-10, 20),
    estimation: tuple[int, int] = (-250, -21),
) -> pd.Series:
    """Cumulative abnormal return indexed by trading day relative to the event (for charts).

    `stock` and `market` are daily LOG PRICES. Cumulated from the start of `span`, then re-based so the day before the event is zero.
    """
    data, pos, params, _ = _event_frame(stock, market, event_day, estimation)
    ev = data.iloc[pos + span[0] : pos + span[1] + 1]
    abnormal = ev["stock"] - (params["const"] + params["market"] * ev["market"])
    path = abnormal.cumsum()
    path.index = range(span[0], span[0] + len(path))
    return path - path.loc[-1]


def annualised_vol(weekly_log_returns: pd.Series) -> float:
    return float(weekly_log_returns.std() * np.sqrt(52))
