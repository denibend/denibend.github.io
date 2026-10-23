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


def annualised_vol(weekly_log_returns: pd.Series) -> float:
    return float(weekly_log_returns.std() * np.sqrt(52))
