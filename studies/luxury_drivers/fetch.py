"""Download raw data for Study 01 and save it, with provenance, to data/raw/.

Run:  uv run python -m studies.luxury_drivers.fetch

Sources
- Yahoo Finance via yfinance (unofficial API; terms restrict redistribution, so raw files are
  git-ignored and only derived results are published).
- ECB Data Portal, EXR dataset: euro foreign exchange reference rates (free reuse with attribution).
"""

import io
import json
import warnings
from datetime import UTC, datetime

import pandas as pd
import requests
import yfinance as yf

from studies.luxury_drivers.config import ECB_CURRENCIES, FACTORS, RAW_DIR, START, STOCKS

ECB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{currencies}.EUR.SP00.A"


def fetch_yahoo(tickers: list[str], start: str) -> pd.DataFrame:
    """Daily close and adjusted close in long format: date, ticker, close, adj_close."""
    with warnings.catch_warnings():
        # yfinance itself still uses pandas APIs that pandas 3 deprecates; not actionable here.
        warnings.simplefilter("ignore")
        wide = yf.download(tickers, start=start, auto_adjust=False, progress=False)
    long = (
        wide[["Close", "Adj Close"]]
        .stack(level="Ticker", future_stack=True)
        .rename(columns={"Close": "close", "Adj Close": "adj_close"})
        .reset_index()
        .rename(columns={"Date": "date", "Ticker": "ticker"})
        .dropna(subset=["close"])
    )
    return long[["date", "ticker", "close", "adj_close"]].sort_values(["ticker", "date"])


def fetch_ecb_fx(currencies: list[str], start: str) -> pd.DataFrame:
    """Daily ECB reference rates in long format: date, currency, per_eur."""
    url = ECB_URL.format(currencies="+".join(currencies))
    resp = requests.get(url, params={"format": "csvdata", "startPeriod": start}, timeout=60)
    resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text))
    fx = raw.rename(columns={"TIME_PERIOD": "date", "CURRENCY": "currency", "OBS_VALUE": "per_eur"})
    fx["date"] = pd.to_datetime(fx["date"])
    return fx[["date", "currency", "per_eur"]].dropna().sort_values(["currency", "date"])


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(UTC).isoformat(timespec="seconds")

    prices = fetch_yahoo(list(STOCKS) + list(FACTORS), START)
    prices.to_csv(RAW_DIR / "yahoo_prices.csv", index=False)

    fx = fetch_ecb_fx(ECB_CURRENCIES, START)
    fx.to_csv(RAW_DIR / "ecb_fx.csv", index=False)

    provenance = {
        "retrieved_utc": retrieved,
        "yahoo": {"package": f"yfinance {yf.__version__}", "start": START, "rows": len(prices)},
        "ecb": {"url": ECB_URL.format(currencies="+".join(ECB_CURRENCIES)), "rows": len(fx)},
    }
    (RAW_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
