"""Study 02 calculations. Pure functions: DataFrames in, DataFrames/Series out, no I/O."""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def panel_elasticities(
    growth: pd.DataFrame,
    target: str,
    drivers: list[str],
    entity: str = "geo",
    exclude_years: tuple[int, ...] = (),
) -> pd.DataFrame:
    """Pooled regression of target growth on driver growth with entity fixed effects.

    Fixed effects (one dummy per country) mean each country is compared with its own average
    growth, so the elasticities come from year-to-year variation within countries.
    Heteroskedasticity-robust (HC1) standard errors; with few countries, clustering is unreliable.
    """
    data = growth[[target, *drivers]].dropna().reset_index()
    data = data[~data["time"].isin(exclude_years)]
    dummies = pd.get_dummies(data[entity], prefix="fe", drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([data[drivers], dummies], axis=1))
    model = sm.OLS(data[target], X).fit(cov_type="HC1")
    return pd.DataFrame(
        {
            "target": target,
            "driver": drivers,
            "elasticity": model.params[drivers].values,
            "se": model.bse[drivers].values,
            "t": model.tvalues[drivers].values,
            "p": model.pvalues[drivers].values,
            "r2": model.rsquared,
            "n_obs": int(model.nobs),
            "n_entities": data[entity].nunique(),
        }
    )


def distributed_lag_elasticities(
    growth: pd.DataFrame,
    target: str,
    drivers: list[str],
    lags: int = 4,
    exclude: tuple[str, str] | None = None,
    hac_lags: int = 4,
) -> pd.DataFrame:
    """Regress target growth on current and `lags` lagged growth of each driver.

    The cumulative elasticity of each driver is the sum of its 0..lags coefficients: the percentage
    response of the target over a year to a 1% change in the driver. Standard errors of the sums
    come from a Wald test on the HAC covariance matrix.

    `exclude` drops a date range (inclusive) from the estimation, e.g. the 2020-21 COVID quarters.
    """
    cols = {}
    for d in drivers:
        for k in range(lags + 1):
            cols[f"{d}_L{k}"] = growth[d].shift(k)
    data = pd.concat([growth[target].rename("y"), pd.DataFrame(cols)], axis=1).dropna()
    if exclude:
        data = data.loc[(data.index < exclude[0]) | (data.index > exclude[1])]
    model = sm.OLS(data["y"], sm.add_constant(data.drop(columns="y"))).fit(
        cov_type="HAC", cov_kwds={"maxlags": hac_lags}
    )
    rows = []
    for d in drivers:
        names = [f"{d}_L{k}" for k in range(lags + 1)]
        weights = np.array([1.0 if p in names else 0.0 for p in model.params.index])
        test = model.t_test(weights)
        rows.append(
            {
                "target": target,
                "driver": d,
                "elasticity": float(test.effect[0]),
                "se": float(test.sd[0][0]),
                "t": float(test.tvalue[0][0]),
                "p": float(test.pvalue),
                "r2": model.rsquared,
                "n_obs": int(model.nobs),
                "start": data.index[0].date(),
                "end": data.index[-1].date(),
            }
        )
    return pd.DataFrame(rows)
