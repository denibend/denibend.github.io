"""B3 — GDP per person and remittances, Albania vs EU27, 1990–2025.

Run:  uv run python studies/01-albania-beyond-the-headlines/src/b3.py [--refresh]

Steps (kept separate): download() caches raw files in data/raw/ -> load() reads the cache
-> build() computes the tidy table (pure, tested) -> write() writes the CSV and sources.csv.

Method:
- USD -> EUR at that year's average rate: ECB reference rate from 1999, ECU rate (Eurostat
  ert_bil_eur_a) before. No USD figure is written.
- GDP per capita: World Bank NY.GDP.PCAP.CD for Albania; Eurostat nama_10_pc (current EUR per
  inhabitant) for the EU27 from 1995, World Bank's EU aggregate (EUU) before.
- Remittances received: World Bank BX.TRF.PWKR.CD.DT (personal remittances) for both. For the
  EU27 that is the sum of what member states receive, the same concept as Albania's figure.
  Eurostat's EU27 BoP aggregate only counts extra-EU inflows, so it is not used.
- Remittances as % of GDP: remittances / NY.GDP.MKTP.CD, both World Bank, same currency.
"""

import csv
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

STUDY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = STUDY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_CSV = DATA_DIR / "b3_gdp_remittances.csv"
SOURCES_CSV = DATA_DIR / "sources.csv"
MANIFEST = RAW_DIR / "b3_manifest.json"

YEARS = range(1990, 2026)
ECB_FROM = 1999
ENTITIES = {"ALB": "Albania", "EUU": "EU27"}
EUROSTAT_FROM = 1995

WB_API = "https://api.worldbank.org/v2/country/ALB;EUU/indicator"
EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
WB_LICENCE = "CC BY 4.0"
EUROSTAT_LICENCE = "CC BY 4.0 (Eurostat reuse policy)"

WB_INDICATORS = {
    "wb_ny_gdp_pcap_cd": ("NY.GDP.PCAP.CD", "GDP per capita (current US$)"),
    "wb_ny_gdp_mktp_cd": ("NY.GDP.MKTP.CD", "GDP (current US$)"),
    "wb_bx_trf_pwkr_cd_dt": ("BX.TRF.PWKR.CD.DT", "Personal remittances, received (current US$)"),
}
SOURCES = {
    **{
        sid: {
            "name": f"World Bank WDI {code} — {label}, Albania and EU (EUU)",
            "url": f"{WB_API}/{code}?format=json&per_page=500&date=1990:2026",
            "licence": WB_LICENCE,
            "file": f"b3_{sid}.json",
        }
        for sid, (code, label) in WB_INDICATORS.items()
    },
    "ecb_exr_usd": {
        "name": "ECB euro foreign exchange reference rate, USD per EUR, annual average",
        "url": "https://data-api.ecb.europa.eu/service/data/EXR/A.USD.EUR.SP00.A?format=csvdata",
        "licence": "ECB statistics, free reuse with source acknowledged",
        "file": "b3_ecb_exr_usd.csv",
    },
    "eurostat_ert_bil_eur_a": {
        "name": "Eurostat ert_bil_eur_a — USD per ECU/EUR, annual average (ECU before 1999)",
        "url": f"{EUROSTAT_API}/ert_bil_eur_a?currency=USD&statinfo=AVG&format=JSON&lang=EN",
        "licence": EUROSTAT_LICENCE,
        "file": "b3_eurostat_ert_bil_eur_a.json",
    },
    "eurostat_nama_10_pc": {
        "name": "Eurostat nama_10_pc — GDP at current prices, EUR per inhabitant, EU27",
        "url": f"{EUROSTAT_API}/nama_10_pc?geo=EU27_2020&na_item=B1GQ&unit=CP_EUR_HAB"
        "&format=JSON&lang=EN",
        "licence": EUROSTAT_LICENCE,
        "file": "b3_eurostat_nama_10_pc.json",
    },
}

MEASURES = {
    "gdp_per_capita_eur": "EUR per person",
    "remittances_received_eur": "EUR",
    "remittances_pct_gdp": "% of GDP",
}


# --- 1. Download -------------------------------------------------------------------------


def download(refresh: bool = False) -> None:
    """Fetch every source into data/raw/ unless already cached; record the download time."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for source_id, src in SOURCES.items():
        path = RAW_DIR / src["file"]
        if path.exists() and not refresh and source_id in manifest:
            continue
        resp = requests.get(src["url"], timeout=120)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        manifest[source_id] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(manifest, indent=2))


# --- 2. Read the cache -------------------------------------------------------------------


def _eurostat_series(path: Path) -> pd.Series:
    """JSON-stat with every non-time dimension filtered to one value -> Series by year."""
    d = json.loads(path.read_text())
    time_index = d["dimension"]["time"]["category"]["index"]
    year_of = {pos: int(year) for year, pos in time_index.items()}
    values = {year_of[int(k) % len(time_index)]: float(v) for k, v in d["value"].items()}
    return pd.Series(values).sort_index()


def _wb_frame(path: Path) -> pd.DataFrame:
    """World Bank API JSON -> entity, year, value (nulls dropped)."""
    _, rows = json.loads(path.read_text())
    return pd.DataFrame(
        [
            {"entity": ENTITIES[r["countryiso3code"]], "year": int(r["date"]), "value": r["value"]}
            for r in rows
            if r["value"] is not None
        ]
    )


def load() -> dict:
    """Read every cached file into plain pandas objects."""
    raw = {sid: RAW_DIR / src["file"] for sid, src in SOURCES.items()}
    ecb = list(csv.DictReader(io.StringIO(raw["ecb_exr_usd"].read_text())))
    return {
        **{sid: _wb_frame(raw[sid]) for sid in WB_INDICATORS},
        "ecb_exr_usd": pd.Series({int(r["TIME_PERIOD"]): float(r["OBS_VALUE"]) for r in ecb}),
        "eurostat_ert_bil_eur_a": _eurostat_series(raw["eurostat_ert_bil_eur_a"]),
        "eurostat_nama_10_pc": _eurostat_series(raw["eurostat_nama_10_pc"]),
    }


# --- 3. Compute (pure) -------------------------------------------------------------------


def usd_per_eur(ecb: pd.Series, ecu: pd.Series) -> pd.DataFrame:
    """Annual USD per EUR: ECB reference rate from 1999, ECU rate before. Columns year, rate, source_id."""
    ecb_part = ecb[ecb.index >= ECB_FROM].rename("rate").to_frame().assign(source_id="ecb_exr_usd")
    ecu_part = ecu[ecu.index < ECB_FROM].rename("rate").to_frame()
    ecu_part = ecu_part.assign(source_id="eurostat_ert_bil_eur_a")
    out = pd.concat([ecu_part, ecb_part]).rename_axis("year").reset_index()
    return out.sort_values("year").reset_index(drop=True)


def usd_to_eur(usd: pd.DataFrame, rates: pd.DataFrame, source_id: str) -> pd.DataFrame:
    """Divide USD values by that year's USD-per-EUR rate; source_id records both inputs."""
    out = usd.merge(rates, on="year", how="inner")
    return out.assign(
        value=out["value"] / out["rate"], source_id=source_id + ";" + out["source_id"]
    ).drop(columns="rate")


def build(data: dict) -> pd.DataFrame:
    """Assemble the tidy B3 table."""
    rates = usd_per_eur(data["ecb_exr_usd"], data["eurostat_ert_bil_eur_a"])
    first, last = min(YEARS), max(YEARS)

    gdp_pc = usd_to_eur(data["wb_ny_gdp_pcap_cd"], rates, "wb_ny_gdp_pcap_cd")
    eurostat_pc = data["eurostat_nama_10_pc"]
    eurostat_pc = eurostat_pc[eurostat_pc.index >= EUROSTAT_FROM]
    gdp_pc = gdp_pc[~((gdp_pc["entity"] == "EU27") & gdp_pc["year"].isin(eurostat_pc.index))]
    gdp_pc = pd.concat(
        [
            gdp_pc,
            pd.DataFrame(
                {
                    "entity": "EU27",
                    "year": eurostat_pc.index,
                    "value": eurostat_pc.to_numpy(),
                    "source_id": "eurostat_nama_10_pc",
                }
            ),
        ],
        ignore_index=True,
    ).assign(measure="gdp_per_capita_eur")

    remit_usd = data["wb_bx_trf_pwkr_cd_dt"]
    remit = usd_to_eur(remit_usd, rates, "wb_bx_trf_pwkr_cd_dt").assign(
        measure="remittances_received_eur"
    )

    ratio = remit_usd.merge(data["wb_ny_gdp_mktp_cd"], on=["entity", "year"], suffixes=("", "_gdp"))
    ratio = ratio.assign(
        value=100 * ratio["value"] / ratio["value_gdp"],
        source_id="wb_bx_trf_pwkr_cd_dt;wb_ny_gdp_mktp_cd",
        measure="remittances_pct_gdp",
    ).drop(columns="value_gdp")

    out = pd.concat([gdp_pc, remit, ratio], ignore_index=True)
    out = out[out["year"].between(first, last)]
    out = out.assign(
        value=out["value"].round(4),
        unit=out["measure"].map(MEASURES),
        estimated=False,
        year=out["year"].astype(int),
    )
    cols = ["entity", "year", "measure", "value", "unit", "estimated", "source_id"]
    return out[cols].sort_values(["measure", "entity", "year"]).reset_index(drop=True)


def merge_sources(existing: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Upsert rows by source_id so each brief can add to the shared sources.csv."""
    if existing is None or existing.empty:
        return new.reset_index(drop=True)
    kept = existing[~existing["source_id"].isin(new["source_id"])]
    return pd.concat([kept, new], ignore_index=True).sort_values("source_id").reset_index(drop=True)


# --- 4. Write ----------------------------------------------------------------------------


def write(table: pd.DataFrame) -> None:
    out = table.copy()
    out["estimated"] = out["estimated"].map({True: "TRUE", False: "FALSE"})
    out.to_csv(OUT_CSV, index=False)

    manifest = json.loads(MANIFEST.read_text())
    new = pd.DataFrame(
        [
            {
                "source_id": sid,
                "name": src["name"],
                "url": src["url"],
                "licence": src["licence"],
                "downloaded_utc": manifest[sid],
            }
            for sid, src in SOURCES.items()
        ]
    )
    existing = pd.read_csv(SOURCES_CSV) if SOURCES_CSV.exists() else None
    merge_sources(existing, new).to_csv(SOURCES_CSV, index=False)


def summary(table: pd.DataFrame) -> str:
    return (
        f"rows={len(table)} years={table['year'].min()}-{table['year'].max()} "
        f"entities={table['entity'].nunique()} estimated={int(table['estimated'].sum())}"
    )


if __name__ == "__main__":
    download(refresh="--refresh" in sys.argv)
    result = build(load())
    write(result)
    print(summary(result))
