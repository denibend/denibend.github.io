"""Download raw data for Study 02 and save it, with provenance, to data/raw/.

Run:  uv run python -m studies.luxury_wallet.fetch

Sources: BEA NIPA flat files; FRED; Federal Reserve Distributional Financial Accounts;
ECB Distributional Wealth Accounts; Eurostat statistics API; Hong Kong C&SD open API.
"""

import io
import json
import zipfile
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests

from studies.luxury_wallet.config import (
    BEA_CATEGORIES,
    ECB_DWA_AREAS,
    ECB_DWA_ASSETS,
    ECB_DWA_GROUPS,
    EUROSTAT_QUERIES,
    FRED_SERIES,
    HK_OUTLETS,
    HK_RETAIL_TABLE,
    RAW_DIR,
)

BEA_MONTHLY_URL = "https://apps.bea.gov/national/Release/TXT/NipaDataM.txt"
BEA_REGISTER_URL = "https://apps.bea.gov/national/Release/TXT/SeriesRegister.txt"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
DFA_URL = "https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip"
ECB_DWA_URL = (
    "https://data-api.ecb.europa.eu/service/data/DWA/Q.{areas}.S14.N.LE.NWA.{groups}.EUR.S.N"
)
ECB_DWA_ASSETS_URL = (
    "https://data-api.ecb.europa.eu/service/data/DWA/Q.{areas}.S14.A.LE.{assets}._Z.EUR.S.N"
)
EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"
HK_URL = "https://www.censtatd.gov.hk/api/get.php"
# The HK open-data API rejects requests without a browser-like user agent.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"
)


def _get(url: str, **kwargs) -> requests.Response:
    resp = requests.get(url, timeout=120, **kwargs)
    resp.raise_for_status()
    return resp


def fetch_bea_monthly(categories: dict[str, str]) -> pd.DataFrame:
    """Monthly nominal spending (…RC) and price index (…RG) per category, long format."""
    codes = {
        f"{prefix}R{kind}": (name, kind) for name, prefix in categories.items() for kind in "CG"
    }
    raw = pd.read_csv(io.StringIO(_get(BEA_MONTHLY_URL).text), thousands=",")
    raw.columns = ["code", "period", "value"]
    df = raw[raw["code"].isin(codes)].copy()
    df["category"] = df["code"].map(lambda c: codes[c][0])
    df["measure"] = df["code"].map(
        lambda c: {"C": "nominal_musd_saar", "G": "price_index"}[codes[c][1]]
    )
    df["date"] = pd.to_datetime(df["period"], format="%YM%m")
    missing = set(codes) - set(df["code"])
    if missing:
        raise ValueError(f"BEA codes not found in monthly file: {sorted(missing)}")
    return df[["date", "category", "measure", "code", "value"]].sort_values(["code", "date"])


def fetch_fred(series: dict[str, str]) -> pd.DataFrame:
    frames = []
    for sid in series:
        df = pd.read_csv(io.StringIO(_get(FRED_URL, params={"id": sid}).text))
        df.columns = ["date", "value"]
        frames.append(df.assign(series=sid))
    out = pd.concat(frames)
    out["date"] = pd.to_datetime(out["date"])
    out["value"] = pd.to_numeric(out["value"], errors="coerce")  # FRED marks gaps with "."
    return out.dropna()


def fetch_fed_dfa() -> dict[str, pd.DataFrame]:
    """Net worth by wealth group and by income group (levels, $ millions, quarterly)."""
    z = zipfile.ZipFile(io.BytesIO(_get(DFA_URL).content))
    return {
        "dfa_networth_by_wealth": pd.read_csv(z.open("dfa-networth-levels.csv")),
        "dfa_networth_by_income": pd.read_csv(z.open("dfa-income-levels.csv")),
    }


def fetch_ecb_dwa(areas: list[str], groups: list[str]) -> pd.DataFrame:
    """Net wealth (NWA) by wealth group."""
    url = ECB_DWA_URL.format(areas="+".join(areas), groups="+".join(groups))
    raw = pd.read_csv(io.StringIO(_get(url, params={"format": "csvdata"}).text))
    return raw[["REF_AREA", "DWA_GRP", "TIME_PERIOD", "OBS_VALUE", "UNIT_MULT", "TITLE"]]


def fetch_ecb_dwa_assets(areas: list[str], assets: list[str]) -> pd.DataFrame:
    """Asset holdings of all households (group _Z), e.g. equity (F5) and housing (NUN)."""
    url = ECB_DWA_ASSETS_URL.format(areas="+".join(areas), assets="+".join(assets))
    raw = pd.read_csv(io.StringIO(_get(url, params={"format": "csvdata"}).text))
    return raw[["REF_AREA", "INSTR_ASSET", "TIME_PERIOD", "OBS_VALUE", "UNIT_MULT", "TITLE"]]


def jsonstat_to_frame(data: dict) -> pd.DataFrame:
    """Flatten a JSON-stat 2.0 dataset (Eurostat API) into a long DataFrame.

    Values are stored as {flat_index: value}; the flat index is the row-major position across the
    dimensions listed in data["id"] with sizes data["size"].
    """
    dims, sizes = data["id"], data["size"]
    labels = {
        d: {pos: code for code, pos in data["dimension"][d]["category"]["index"].items()}
        for d in dims
    }
    flat = np.array([int(k) for k in data["value"]], dtype=int)
    coords = np.unravel_index(flat, sizes) if len(flat) else [np.array([], dtype=int)] * len(dims)
    out = pd.DataFrame({d: [labels[d][i] for i in coords[n]] for n, d in enumerate(dims)})
    out["value"] = list(data["value"].values())
    return out


def fetch_eurostat(dataset: str, filters: dict) -> pd.DataFrame:
    params = [("format", "JSON"), ("lang", "EN")]
    for key, value in filters.items():
        for v in value if isinstance(value, list) else [value]:
            params.append((key, v))
    data = _get(EUROSTAT_URL.format(dataset=dataset), params=params).json()
    if "value" not in data:
        raise ValueError(f"Eurostat {dataset}: {str(data)[:300]}")
    return jsonstat_to_frame(data)


def fetch_hk_retail(table: str, outlets: list[str]) -> pd.DataFrame:
    resp = _get(
        HK_URL,
        params={"id": table, "lang": "en", "full_series": "1"},
        headers={"User-Agent": BROWSER_UA},
    )
    df = pd.DataFrame(resp.json()["dataSet"])
    df = df[(df["OUTLET_TYPEDesc"].isin(outlets)) & (df["freq"] == "M") & (df["sv"] == "VAL_RS")]
    df = df.assign(
        date=pd.to_datetime(df["period"], format="%Y%m"),
        value=pd.to_numeric(df["figure"], errors="coerce"),
    )
    return df[["date", "OUTLET_TYPEDesc", "value"]].rename(columns={"OUTLET_TYPEDesc": "outlet"})


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    provenance = {"retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"), "files": {}}

    def save(name: str, df: pd.DataFrame, source: str) -> None:
        df.to_csv(RAW_DIR / f"{name}.csv", index=False)
        provenance["files"][name] = {"source": source, "rows": len(df)}
        print(f"{name:32s} {len(df):>7,} rows  {source}")

    save("bea_pce_monthly", fetch_bea_monthly(BEA_CATEGORIES), BEA_MONTHLY_URL)
    save("fred", fetch_fred(FRED_SERIES), FRED_URL)
    for name, df in fetch_fed_dfa().items():
        save(name, df, DFA_URL)
    save("ecb_dwa", fetch_ecb_dwa(ECB_DWA_AREAS, ECB_DWA_GROUPS), ECB_DWA_URL)
    save("ecb_dwa_assets", fetch_ecb_dwa_assets(ECB_DWA_AREAS, ECB_DWA_ASSETS), ECB_DWA_ASSETS_URL)
    for name, (dataset, filters) in EUROSTAT_QUERIES.items():
        save(f"eurostat_{name}", fetch_eurostat(dataset, filters), f"Eurostat {dataset}")
    save(
        "hk_retail", fetch_hk_retail(HK_RETAIL_TABLE, HK_OUTLETS), f"{HK_URL}?id={HK_RETAIL_TABLE}"
    )

    (RAW_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
