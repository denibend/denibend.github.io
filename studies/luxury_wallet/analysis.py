"""Study 02 calculations. Pure functions: DataFrames in, DataFrames/Series out, no I/O."""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def out_of_sample_prediction(
    data: pd.DataFrame, target: str, drivers: list[str], fit_end: str, predict_start: str
) -> pd.DataFrame:
    """Fit OLS of target on drivers up to `fit_end`; predict from `predict_start` onwards.

    Returns actual, predicted and gap (actual - predicted) for the prediction window, in the same
    units as the target.
    """
    d = data[[target, *drivers]].dropna()
    fit = d.loc[:fit_end]
    model = sm.OLS(fit[target], sm.add_constant(fit[drivers])).fit()
    later = d.loc[predict_start:]
    predicted = model.predict(sm.add_constant(later[drivers], has_constant="add"))
    return pd.DataFrame(
        {"actual": later[target], "predicted": predicted, "gap": later[target] - predicted}
    )


def spearman_permutation(
    x: np.ndarray, y: np.ndarray, n_perm: int = 20000, seed: int = 0
) -> tuple[float, float]:
    """Spearman rank correlation and a two-sided permutation p-value.

    With very few observations (e.g. 8 companies), shuffling one variable many times shows how often
    a correlation at least this strong arises by chance; this is more honest than an asymptotic p-value.
    """
    from scipy import stats

    rng = np.random.default_rng(seed)
    observed = stats.spearmanr(x, y).statistic
    sims = np.array([stats.spearmanr(rng.permutation(x), y).statistic for _ in range(n_perm)])
    return float(observed), float((np.abs(sims) >= abs(observed)).mean())


def trend_deviation(series: pd.Series, fit_start: str, fit_end: str) -> pd.DataFrame:
    """Log-linear trend fitted on [fit_start, fit_end], extrapolated over the whole series.

    Returns actual, trend and the deviation in % ((actual / trend - 1) * 100). A persistent positive
    deviation after the fit window means the series stays above its pre-period path.
    """
    s = series.dropna()
    t = (s.index - s.index[0]).days / 365.25
    t = pd.Series(t, index=s.index)
    fit = s.loc[fit_start:fit_end]
    model = sm.OLS(np.log(fit), sm.add_constant(t.loc[fit.index])).fit()
    trend = np.exp(model.params["const"] + model.params.iloc[1] * t)
    return pd.DataFrame({"actual": s, "trend": trend, "deviation_pct": (s / trend - 1) * 100})


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


def panel_distributed_lag(
    growth: pd.DataFrame,
    target: str,
    drivers: list[str],
    lags: int = 4,
    entity: str = "geo",
    exclude: tuple[str, str] | None = None,
    hac_lags: int = 4,
) -> pd.DataFrame:
    """Panel version of `distributed_lag_elasticities`: lags built within each entity, entity
    fixed effects, and panel Newey-West standard errors (robust to serial correlation within an
    entity and to heteroskedasticity).
    """
    g = growth.sort_index()
    by = g.groupby(level=entity)
    cols = {f"{d}_L{k}": by[d].shift(k) for d in drivers for k in range(lags + 1)}
    data = pd.concat([g[target].rename("y"), pd.DataFrame(cols)], axis=1).dropna()
    dates = data.index.get_level_values(-1)
    if exclude:
        data = data[(dates < exclude[0]) | (dates > exclude[1])]
    ents = data.index.get_level_values(entity)
    dummies = pd.get_dummies(
        pd.Series(ents, index=data.index), prefix="fe", drop_first=True, dtype=float
    )
    X = sm.add_constant(pd.concat([data.drop(columns="y"), dummies], axis=1))
    groups = pd.factorize(ents)[0]
    model = sm.OLS(data["y"], X).fit(
        cov_type="hac-panel", cov_kwds={"groups": groups, "maxlags": hac_lags}
    )
    rows = []
    for d in drivers:
        names = {f"{d}_L{k}" for k in range(lags + 1)}
        test = model.t_test(np.array([1.0 if p in names else 0.0 for p in model.params.index]))
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
                "n_entities": len(set(ents)),
            }
        )
    return pd.DataFrame(rows)


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
