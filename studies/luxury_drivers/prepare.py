"""Turn raw daily prices and FX rates into aligned EUR return series (the "staging layer")."""

import numpy as np
import pandas as pd

from studies.luxury_drivers.config import RAW_DIR, STOCKS


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = pd.read_csv(RAW_DIR / "yahoo_prices.csv", parse_dates=["date"])
    fx = pd.read_csv(RAW_DIR / "ecb_fx.csv", parse_dates=["date"])
    return prices, fx


def to_wide(prices: pd.DataFrame, column: str = "adj_close") -> pd.DataFrame:
    """Long -> wide: one row per date, one column per ticker (like a pivot table)."""
    return prices.pivot(index="date", columns="ticker", values=column).sort_index()


def convert_to_eur(
    wide: pd.DataFrame, fx: pd.DataFrame, currencies: dict[str, str]
) -> pd.DataFrame:
    """Convert each ticker's prices to EUR using ECB rates (foreign currency per 1 EUR).

    `currencies` maps ticker -> Yahoo currency code. "GBp" (pence) is divided by 100 first.
    FX rates are forward-filled across ECB holidays so every trading day has a rate.
    """
    rates = fx.pivot(index="date", columns="currency", values="per_eur").sort_index()
    rates = rates.reindex(wide.index.union(rates.index)).ffill().reindex(wide.index)

    out = wide.copy()
    for ticker, ccy in currencies.items():
        if ccy == "EUR" or ticker not in out:
            continue
        if ccy == "GBp":
            out[ticker] = out[ticker] / 100
            ccy = "GBP"
        out[ticker] = out[ticker] / rates[ccy]
    return out


def weekly_log_returns(wide: pd.DataFrame) -> pd.DataFrame:
    """Friday-to-Friday log returns, using the last available price in each week.

    Weekly sampling reduces the distortion from markets closing at different times
    (Hong Kong closes before Europe opens).
    """
    weekly = wide.resample("W-FRI").last()
    return np.log(weekly).diff().iloc[1:]


def build_daily_log_prices() -> pd.DataFrame:
    """Daily log prices for the event study (returns are computed later, per stock/index pair).

    European listings in EUR; Prada in HKD (it is benchmarked against the Hang Seng in local
    currency). Returns must be taken only after aligning a stock with its index on common
    trading days; otherwise a day missing from one series makes the next return span two days.
    """
    prices, fx = load_raw()
    is_stock = prices["ticker"].isin(STOCKS)
    stocks = convert_to_eur(
        to_wide(prices[is_stock]),
        fx,
        {t: ccy for t, (_, ccy) in STOCKS.items() if t != "1913.HK"},
    )
    indices = to_wide(prices[~is_stock], column="close")
    return np.log(pd.concat([stocks, indices], axis=1))


def build_weekly_dataset(start: str) -> pd.DataFrame:
    """Weekly EUR log returns for the stocks plus the three factor series.

    Factor definitions:
    - market: STOXX Europe 600 (EUR price index)
    - eurusd: change in log USD per EUR (positive = euro strengthens)
    - china:  Hang Seng index in local currency (HKD is pegged to USD)
    - china_alt: MSCI China ETF in USD (robustness check)
    """
    prices, fx = load_raw()
    stock_prices = convert_to_eur(
        to_wide(prices[prices["ticker"].isin(STOCKS)]),
        fx,
        {t: ccy for t, (_, ccy) in STOCKS.items()},
    )
    factor_prices = to_wide(prices[~prices["ticker"].isin(STOCKS)], column="close")
    usd = fx[fx["currency"] == "USD"].set_index("date")["per_eur"].rename("eurusd")

    returns = weekly_log_returns(pd.concat([stock_prices, factor_prices, usd], axis=1))
    returns = returns.rename(columns={"^STOXX": "market", "^HSI": "china", "MCHI": "china_alt"})
    return returns.loc[start:]
