"""Turn Study 02 raw files into aligned quarterly US series (the staging layer)."""

import numpy as np
import pandas as pd

from studies.luxury_wallet.config import RAW_DIR


def to_quarterly(monthly: pd.DataFrame) -> pd.DataFrame:
    """Average monthly values into calendar quarters (index = quarter start date).

    BEA monthly spending is a seasonally adjusted annual rate, so the quarterly mean is the
    quarter's annual-rate level, like BEA's own quarterly tables. Quarters with fewer than three
    months of data (e.g. the latest, still incomplete quarter) are set to missing.
    """
    resampled = monthly.resample("QS")
    return resampled.mean().where(resampled.count() == 3)


def real_spending(nominal: pd.DataFrame, price_index: pd.DataFrame) -> pd.DataFrame:
    """Deflate each category by its own price index: real = nominal / (index / 100)."""
    return nominal / (price_index / 100)


def parse_dfa_quarter(s: pd.Series) -> pd.DatetimeIndex:
    """'1989:Q3' -> 1989-07-01 (quarter start)."""
    return pd.PeriodIndex(s.str.replace(":", ""), freq="Q").to_timestamp(how="start")


def wealth_groups(dfa: pd.DataFrame) -> pd.DataFrame:
    """Net worth by wealth group, collapsed to top 1%, next 9% and bottom 90% ($ millions, nominal)."""
    wide = dfa.assign(date=parse_dfa_quarter(dfa["Date"])).pivot(
        index="date", columns="Category", values="Net worth"
    )
    return pd.DataFrame(
        {
            "wealth_top1": wide["TopPt1"] + wide["RemainingTop1"],
            "wealth_next9": wide["Next9"],
            "wealth_bottom90": wide["Next40"] + wide["Bottom50"],
        }
    )


def wealth_by_asset(dfa: pd.DataFrame) -> pd.DataFrame:
    """Household equity and real-estate wealth, all groups combined ($ millions, nominal).

    Equities are held mostly by the top 10% (88% in 2026); real estate is the main asset of the
    middle class. The two grow almost independently, so they separate the two wallets far better
    than wealth groups do (top 1% and next 9% wealth growth correlate at 0.95).
    """
    totals = (
        dfa.assign(date=parse_dfa_quarter(dfa["Date"]))
        .groupby("date")[["Corporate equities and mutual fund shares", "Real estate"]]
        .sum()
    )
    return totals.rename(
        columns={
            "Corporate equities and mutual fund shares": "wealth_equity",
            "Real estate": "wealth_housing",
        }
    )


def build_us_quarterly() -> pd.DataFrame:
    """Real quarterly US series: spending by category, income, aggregate and group wealth."""
    bea = pd.read_csv(RAW_DIR / "bea_pce_monthly.csv", parse_dates=["date"])
    wide = bea.pivot_table(index="date", columns=["measure", "category"], values="value")
    spending = to_quarterly(
        real_spending(wide["nominal_musd_saar"], wide["price_index"])
    ).add_prefix("spend_")

    fred = pd.read_csv(RAW_DIR / "fred.csv", parse_dates=["date"]).pivot(
        index="date", columns="series", values="value"
    )
    monthly = to_quarterly(fred[["DSPIC96", "PCEPI"]].dropna())
    deflator = monthly["PCEPI"] / 100
    income = monthly["DSPIC96"].rename("income_real")
    networth = (fred["TNWBSHNO"].dropna() / deflator).rename("wealth_total")

    dfa = pd.read_csv(RAW_DIR / "dfa_networth_by_wealth.csv")
    groups = pd.concat([wealth_groups(dfa), wealth_by_asset(dfa)], axis=1)
    groups = groups.div(deflator, axis=0).dropna()

    return pd.concat([spending, income, networth, groups], axis=1).sort_index()


def log_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Quarter-on-quarter log growth (approximately % change / 100)."""
    return np.log(df).diff()
