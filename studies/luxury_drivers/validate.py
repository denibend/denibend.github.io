"""Data-quality checks on the raw daily price file (long format: date, ticker, close, adj_close).

Each check returns a small DataFrame so the results can be printed during the build and
summarised in the report's data section.
"""

import pandas as pd


def coverage(prices: pd.DataFrame) -> pd.DataFrame:
    """First/last date, observation count and longest calendar gap per ticker."""

    def summarise(g: pd.DataFrame) -> pd.Series:
        dates = g["date"].sort_values()
        return pd.Series(
            {
                "first": dates.iloc[0].date(),
                "last": dates.iloc[-1].date(),
                "obs": len(dates),
                "max_gap_days": int(dates.diff().dt.days.max()),
            }
        )

    return prices.groupby("ticker").apply(summarise, include_groups=False)


def stale_runs(prices: pd.DataFrame) -> pd.Series:
    """Longest run of consecutive unchanged closes per ticker (frozen prices signal bad data)."""

    def longest_run(close: pd.Series) -> int:
        unchanged = close.diff().eq(0)
        return int(unchanged.groupby((~unchanged).cumsum()).sum().max())

    return prices.sort_values("date").groupby("ticker")["close"].apply(longest_run)


def extreme_moves(prices: pd.DataFrame, threshold: float = 0.15) -> pd.DataFrame:
    """Daily total returns larger than `threshold` in absolute value, for manual review."""
    df = prices.sort_values(["ticker", "date"]).copy()
    df["return"] = df.groupby("ticker")["adj_close"].pct_change()
    return df.loc[df["return"].abs() > threshold, ["date", "ticker", "return"]]


def corporate_action_flags(prices: pd.DataFrame, threshold: float = 0.05) -> pd.DataFrame:
    """Days where adj_close/close jumps by more than `threshold`.

    Ordinary dividends move the ratio by ~1-4%; larger jumps suggest special dividends or
    spin-offs that need checking.
    """
    df = prices.sort_values(["ticker", "date"]).copy()
    df["ratio_change"] = (df["adj_close"] / df["close"]).groupby(df["ticker"]).pct_change()
    return df.loc[df["ratio_change"].abs() > threshold, ["date", "ticker", "ratio_change"]]
