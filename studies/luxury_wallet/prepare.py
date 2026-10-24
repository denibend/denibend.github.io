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


LUXURY_GOODS = ["jewelry_watches", "luggage", "clothing_footwear"]
EXPERIENCES = [
    "accommodations",
    "air_transport",
    "package_tours",
    "food_services",
    "recreation_services",
]


def us_baskets_monthly() -> pd.DataFrame:
    """Monthly US spending baskets: nominal shares of total PCE and real (volume) levels.

    Real basket volumes are sums of each category's own-price-deflated spending (in index-base
    dollars); an approximation to chain-weighting that is adequate for a two-basket comparison.
    """
    bea = pd.read_csv(RAW_DIR / "bea_pce_monthly.csv", parse_dates=["date"])
    wide = bea.pivot_table(index="date", columns=["measure", "category"], values="value")
    nominal, prices = wide["nominal_musd_saar"], wide["price_index"]
    real = real_spending(nominal, prices)
    out = pd.DataFrame(
        {
            "share_luxury_goods": nominal[LUXURY_GOODS].sum(axis=1) / nominal["total_pce"],
            "share_experiences": nominal[EXPERIENCES].sum(axis=1) / nominal["total_pce"],
            "real_luxury_goods": real[LUXURY_GOODS].sum(axis=1),
            "real_experiences": real[EXPERIENCES].sum(axis=1),
            "real_total": real["total_pce"],
        }
    )
    out["real_ratio_experiences_to_luxury"] = out["real_experiences"] / out["real_luxury_goods"]
    return out


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


EU_PANEL_GEOS = ["DE", "FR", "IT", "ES", "NL", "BE", "AT"]


def load_ecb_wealth() -> pd.DataFrame:
    """ECB wealth rows (geo, group, TIME_PERIOD, OBS_VALUE) for wealth groups and asset types."""
    dwa = pd.read_csv(RAW_DIR / "ecb_dwa.csv")
    dwa["group"] = dwa["DWA_GRP"].map(
        {
            "B50": "wealth_bottom50",
            "D10": "wealth_top10",
            **dict.fromkeys(["D6", "D7", "D8", "D9"], "wealth_middle40"),
        }
    )
    assets = pd.read_csv(RAW_DIR / "ecb_dwa_assets.csv")
    assets["group"] = assets["INSTR_ASSET"].map({"F5": "wealth_equity", "NUN": "wealth_housing"})
    return pd.concat([dwa, assets]).rename(columns={"REF_AREA": "geo"})


def quarterly_wealth(rows: pd.DataFrame) -> pd.Series:
    """Sum group components (e.g. deciles 6-9) per quarter; missing if any component is missing.

    A plain pandas sum would turn missing values into 0 and create infinite growth rates.
    """
    return rows.groupby(["geo", "group", "TIME_PERIOD"])["OBS_VALUE"].agg(
        lambda s: s.sum(skipna=False)
    )


def annual_wealth(rows: pd.DataFrame) -> pd.DataFrame:
    """Quarterly ECB wealth rows -> annual averages (index geo, time; one column per group).

    A year's average requires all four quarters, so a partial year (e.g. a series starting in Q4)
    does not masquerade as a full-year level.
    """
    q = quarterly_wealth(rows).reset_index()
    q["time"] = q["TIME_PERIOD"].str[:4].astype(int)
    yearly = q.groupby(["geo", "time", "group"])["OBS_VALUE"].agg(["mean", "count"])
    return yearly["mean"].where(yearly["count"] == 4).unstack("group")


def quarter_start(period: pd.Series) -> pd.Series:
    """'2024-Q3' -> Timestamp 2024-07-01."""
    return pd.PeriodIndex(period.str.replace("-", ""), freq="Q").to_timestamp(how="start")


def build_eu_annual() -> pd.DataFrame:
    """Annual EU country panel (index: geo, year) of real spending, income and wealth.

    Spending is deflated by each category's own price index; income and wealth by the household
    consumption deflator. ECB quarterly wealth stocks are averaged within each year.
    """
    spend = pd.read_csv(RAW_DIR / "eurostat_spending_by_purpose.csv")
    spend = spend[spend["geo"].isin(EU_PANEL_GEOS)]
    wide = spend.pivot_table(index=["geo", "time"], columns=["unit", "coicop18"], values="value")
    real = (wide["CP_MEUR"] / (wide["PD20_EUR"] / 100)).add_prefix("spend_")
    deflator = wide[("PD20_EUR", "TOTAL")] / 100

    income = pd.read_csv(RAW_DIR / "eurostat_household_income.csv")
    income = income.set_index(["geo", "time"])["value"].rename("income")

    wealth = annual_wealth(load_ecb_wealth())

    panel = pd.concat([real, income, wealth], axis=1).loc[EU_PANEL_GEOS]
    nominal = ["income", *wealth.columns]
    panel[nominal] = panel[nominal].div(deflator, axis=0)
    return panel.sort_index()


def build_eu_quarterly() -> pd.DataFrame:
    """Quarterly EU country panel (index: geo, date): real spending by durability, income, wealth.

    Spending in chain-linked volumes (2020 euros); income and wealth deflated by the implicit
    household consumption deflator (current-price total / volume total).
    """
    spend = pd.read_csv(RAW_DIR / "eurostat_spending_by_durability_q.csv")
    spend = spend[spend["geo"].isin(EU_PANEL_GEOS)].assign(date=lambda d: quarter_start(d["time"]))
    wide = spend.pivot_table(index=["geo", "date"], columns=["unit", "na_item"], values="value")
    real = wide["CLV20_MEUR"].rename(
        columns={
            "P31_S14": "spend_total",
            "P311_S14": "spend_durable",
            "P312_S14": "spend_semidurable",
            "P313_S14": "spend_nondurable",
            "P314_S14": "spend_services",
        }
    )
    deflator = wide[("CP_MEUR", "P31_S14")] / wide[("CLV20_MEUR", "P31_S14")]

    inc = pd.read_csv(RAW_DIR / "eurostat_household_income_q.csv")
    inc = inc[inc["geo"].isin(EU_PANEL_GEOS)].assign(date=lambda d: quarter_start(d["time"]))
    income = inc.set_index(["geo", "date"])["value"].rename("income")

    w = quarterly_wealth(load_ecb_wealth()).reset_index()
    w["date"] = quarter_start(w["TIME_PERIOD"])
    wealth = w.pivot_table(index=["geo", "date"], columns="group", values="OBS_VALUE", dropna=False)

    panel = pd.concat([real, income, wealth], axis=1)
    panel = panel.loc[panel.index.get_level_values("geo").isin(EU_PANEL_GEOS)]
    nominal = ["income", *wealth.columns]
    panel[nominal] = panel[nominal].div(deflator, axis=0)
    return panel.sort_index()


JEWELLERY = "Jewellery, watches and clocks, and valuable gifts"


def hkd_per_cny(fx: pd.DataFrame) -> pd.Series:
    """Cross rate from ECB rates (foreign currency per EUR): HKD per CNY. Higher = stronger renminbi."""
    wide = fx.pivot(index="TIME_PERIOD", columns="CURRENCY", values="OBS_VALUE")
    wide.index = pd.to_datetime(wide.index + "-01")
    return (wide["HKD"] / wide["CNY"]).rename("hkd_per_cny")


def build_hk_monthly() -> pd.DataFrame:
    """Monthly Hong Kong / China series (nominal HK$ retail sales, visitor counts, index levels)."""
    retail = pd.read_csv(RAW_DIR / "hk_retail.csv", parse_dates=["date"]).pivot(
        index="date", columns="series", values="value"
    )
    visitors = pd.read_csv(RAW_DIR / "hk_visitors.csv", parse_dates=["date"]).pivot(
        index="date", columns="series", values="value"
    )
    equity = pd.read_csv(RAW_DIR / "china_equity_monthly.csv", parse_dates=["date"]).set_index(
        "date"
    )
    fx = hkd_per_cny(pd.read_csv(RAW_DIR / "ecb_fx_monthly.csv"))
    return pd.DataFrame(
        {
            "jewellery_sales": retail[JEWELLERY],
            "other_retail_sales": retail["Total"] - retail[JEWELLERY],
            "mainland_visitors": visitors["Chinese Mainland"],
            "total_visitors": visitors["Total"],
            "shanghai": equity["Shanghai Composite"],
            "hang_seng": equity["Hang Seng"],
            "gold_usd": equity["Gold"],
            "hkd_per_cny": fx,
        }
    ).sort_index()


def build_tier_monthly(start: str = "2014-01-01") -> pd.DataFrame:
    """Monthly tier returns (Study 01 data, EUR) plus market factors and wallet drivers.

    Reuses Study 01's raw prices and tier definitions (studies.luxury_drivers), so Study 01's
    `fetch` must have been run. Drivers:
    - market, china, eurusd: as in Study 01, monthly log changes;
    - confidence_change: monthly change in the EU consumer confidence balance (points);
    - us_income_growth: monthly log growth of US real disposable income.
    """
    from studies.luxury_drivers import analysis as s1_analysis
    from studies.luxury_drivers import prepare as s1
    from studies.luxury_drivers.config import STOCKS, TIERS

    prices, fx = s1.load_raw()
    stocks = s1.convert_to_eur(
        s1.to_wide(prices[prices["ticker"].isin(STOCKS)]),
        fx,
        {t: c for t, (_, c) in STOCKS.items()},
    ).rename(columns={t: n for t, (n, _) in STOCKS.items()})
    factors = s1.to_wide(prices[~prices["ticker"].isin(STOCKS)], column="close")
    usd = fx[fx["currency"] == "USD"].set_index("date")["per_eur"].rename("eurusd")
    levels = pd.concat([stocks, factors, usd], axis=1).resample("MS").last()
    r = np.log(levels).diff().rename(columns={"^STOXX": "market", "^HSI": "china"})
    tiers = s1_analysis.tier_returns(r[[n for n, _ in STOCKS.values()]], TIERS)

    conf = pd.read_csv(RAW_DIR / "eurostat_consumer_confidence.csv")
    conf = conf[conf["geo"] == "EU27_2020"].assign(date=lambda d: pd.to_datetime(d["time"] + "-01"))
    confidence_change = (
        conf.set_index("date")["value"].sort_index().diff().rename("confidence_change")
    )

    fred = pd.read_csv(RAW_DIR / "fred.csv", parse_dates=["date"])
    income = fred[fred["series"] == "DSPIC96"].set_index("date")["value"]
    income_growth = np.log(income).diff().rename("us_income_growth")

    out = pd.concat(
        [tiers, r[["market", "china", "eurusd"]], confidence_change, income_growth], axis=1
    )
    out["top_minus_aspirational"] = out["Top tier"] - out["Aspirational / fashion-led"]
    return out.loc[start:].dropna()


def log_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Quarter-on-quarter log growth (approximately % change / 100)."""
    return np.log(df).diff()
