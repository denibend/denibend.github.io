"""B1 — Albanians by where they live, 1990–2026.

Run:  uv run python studies/2026-11-albania-crossroads/src/b1.py [--refresh]

Steps (kept separate): download() caches raw files in data/raw/ -> load_*() reads the cache
-> build() computes the tidy table (pure, tested) -> write() writes the CSV and sources.csv.

Concepts:
- Resident in Albania: INSTAT population on 1 January, taken from Eurostat demo_gind
  (Eurostat republishes INSTAT's series; INSTAT's own PxWeb database was unreachable).
- Albanians abroad: UN DESA International Migrant Stock = people born in Albania (or Albanian
  citizens where a destination only reports citizenship), mid-year, five-yearly waves.
  The 2024 edition drops the Albania-origin rows for Germany, UK and USA, so those three come
  from the 2020 edition; everything else from the 2024 edition.
- Between waves: linear interpolation (estimated). After the last wave: scaled by an annual
  Eurostat series where one exists (Italy: born in Albania; Germany: Albanian citizens),
  otherwise held flat at the last wave (estimated).
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

STUDY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = STUDY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_CSV = DATA_DIR / "b1_population_by_location.csv"
SOURCES_CSV = DATA_DIR / "sources.csv"
MANIFEST = RAW_DIR / "b1_manifest.json"

YEARS = range(1990, 2027)
UNIT = "people"
MEASURE_LOCATION = "people_by_location"
MEASURE_FOREIGN = "foreign_born_residents"
MEASURE_ADJUSTED = "people_by_location_census_adjusted"
# 1 Jan 2012 is the first point on the 2011-census basis; 1 Jan 2024 the first on the 2023 one.
BACKCAST_ANCHOR, CENSUS_BREAK = 2012, 2024

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
UN_FILES = "https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files"

SOURCES = {
    "eurostat_demo_gind": {
        "name": "Eurostat demo_gind — population on 1 January, Albania (INSTAT data)",
        "url": f"{EUROSTAT_API}/demo_gind?geo=AL&indic_de=JAN&format=JSON&lang=EN",
        "licence": "CC BY 4.0 (Eurostat reuse policy)",
        "file": "b1_eurostat_demo_gind.json",
    },
    "un_ims_2024": {
        "name": "UN DESA International Migrant Stock 2024 — destination and origin (Table 1)",
        "url": f"{UN_FILES}/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx",
        "licence": "CC BY 3.0 IGO",
        "file": "b1_un_ims_2024.xlsx",
    },
    "un_ims_2020": {
        "name": "UN DESA International Migrant Stock 2020 — destination and origin (Table 1)",
        "url": f"{UN_FILES}/undesa_pd_2020_ims_stock_by_sex_destination_and_origin.xlsx",
        "licence": "CC BY 3.0 IGO",
        "file": "b1_un_ims_2020.xlsx",
    },
    "eurostat_migr_pop3ctb": {
        "name": "Eurostat migr_pop3ctb — population born in Albania, Italy (ISTAT data)",
        "url": f"{EUROSTAT_API}/migr_pop3ctb?c_birth=AL&age=TOTAL&sex=T&geo=IT&format=JSON&lang=EN",
        "licence": "CC BY 4.0 (Eurostat reuse policy)",
        "file": "b1_eurostat_migr_pop3ctb.json",
    },
    "eurostat_migr_pop1ctz": {
        "name": "Eurostat migr_pop1ctz — Albanian citizens, Germany (Destatis data)",
        "url": f"{EUROSTAT_API}/migr_pop1ctz?citizen=AL&age=TOTAL&sex=T&geo=DE&format=JSON&lang=EN",
        "licence": "CC BY 4.0 (Eurostat reuse policy)",
        "file": "b1_eurostat_migr_pop1ctz.json",
    },
}

# UN location codes
ALBANIA, WORLD = 8, 900
ITALY, GREECE, GERMANY, UK, USA = 380, 300, 276, 826, 840

# Destinations: entity -> (UN code, UN edition, Eurostat index source for years after the last wave)
DESTINATIONS = {
    "Italy": (ITALY, "un_ims_2024", "eurostat_migr_pop3ctb"),
    "Greece": (GREECE, "un_ims_2024", None),
    "Germany": (GERMANY, "un_ims_2020", "eurostat_migr_pop1ctz"),
    "United Kingdom": (UK, "un_ims_2020", None),
    "United States": (USA, "un_ims_2020", None),
}


# --- 1. Download -------------------------------------------------------------------------


def download(refresh: bool = False) -> None:
    """Fetch every source into data/raw/ unless already cached; record the download time."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    headers = {"User-Agent": "Mozilla/5.0 (research portfolio; denibend.github.io)"}
    for source_id, src in SOURCES.items():
        path = RAW_DIR / src["file"]
        if path.exists() and not refresh and source_id in manifest:
            continue
        resp = requests.get(src["url"], headers=headers, timeout=120)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        manifest[source_id] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(manifest, indent=2))


# --- 2. Read the cache -------------------------------------------------------------------


def _eurostat_series(path: Path) -> pd.Series:
    """JSON-stat with one non-time dimension filtered to a single value -> Series by year."""
    d = json.loads(path.read_text())
    time_index = d["dimension"]["time"]["category"]["index"]
    year_of = {pos: int(year) for year, pos in time_index.items()}
    n_time = len(time_index)
    values = {year_of[int(k) % n_time]: float(v) for k, v in d["value"].items()}
    return pd.Series(values).sort_index()


def _un_table1(path: Path) -> pd.DataFrame:
    """UN IMS Table 1 -> long frame: dest, origin, year, value (both sexes)."""
    df = pd.read_excel(path, sheet_name="Table 1", header=10)
    # Both-sexes columns are the first block of integer year headers; males/females repeat
    # the years and pandas renames those to strings like "1990.1".
    year_cols = [c for c in df.columns if isinstance(c, int)]
    df = df.rename(
        columns={"Location code of destination": "dest", "Location code of origin": "origin"}
    )
    long = df[["dest", "origin", *year_cols]].melt(
        id_vars=["dest", "origin"], var_name="year", value_name="value"
    )
    long = long.dropna(subset=["value"])
    return long.astype({"dest": int, "origin": int, "year": int, "value": float})


def load() -> dict:
    """Read every cached file into plain pandas objects."""
    raw = {sid: RAW_DIR / src["file"] for sid, src in SOURCES.items()}
    return {
        "resident": _eurostat_series(raw["eurostat_demo_gind"]),
        "un_ims_2024": _un_table1(raw["un_ims_2024"]),
        "un_ims_2020": _un_table1(raw["un_ims_2020"]),
        "eurostat_migr_pop3ctb": _eurostat_series(raw["eurostat_migr_pop3ctb"]),
        "eurostat_migr_pop1ctz": _eurostat_series(raw["eurostat_migr_pop1ctz"]),
    }


# --- 3. Compute (pure) -------------------------------------------------------------------


def un_waves(table: pd.DataFrame, dest: int, origin: int) -> pd.Series:
    """Stock of `origin`-born people in `dest`, one value per UN wave year."""
    sel = table[(table["dest"] == dest) & (table["origin"] == origin)]
    return sel.set_index("year")["value"].sort_index()


def interpolate_waves(waves: pd.Series) -> pd.DataFrame:
    """Linear interpolation between wave years. Wave years are observed, the rest estimated."""
    years = np.arange(waves.index.min(), waves.index.max() + 1)
    values = np.interp(years, waves.index.to_numpy(), waves.to_numpy())
    return pd.DataFrame({"year": years, "value": values, "estimated": ~np.isin(years, waves.index)})


def extend(
    base_year: int, base_value: float, years: list[int], index: pd.Series | None = None
) -> pd.DataFrame:
    """Carry a level past its last observation, estimated.

    With `index`, the level moves with that annual series (value = base * index[y] / index[base]);
    years beyond the index's last point use its last point. Without one, the level is held flat.
    """
    rows = []
    for year in years:
        ratio = 1.0
        if index is not None:
            ratio = index[min(year, index.index.max())] / index[base_year]
        rows.append({"year": year, "value": base_value * ratio, "estimated": True})
    return pd.DataFrame(rows, columns=["year", "value", "estimated"])


def location_series(
    waves: pd.Series, last_year: int, wave_source: str, index: pd.Series | None, index_source: str
) -> pd.DataFrame:
    """Waves -> interpolated annual series -> extended to `last_year`, with a source_id per row."""
    annual = interpolate_waves(waves).assign(source_id=wave_source)
    base_year = int(waves.index.max())
    later = list(range(base_year + 1, last_year + 1))
    if later:
        tail_source = f"{wave_source};{index_source}" if index is not None else wave_source
        tail = extend(base_year, float(waves[base_year]), later, index).assign(
            source_id=tail_source
        )
        annual = pd.concat([annual, tail], ignore_index=True)
    return annual


def census_backcast(series: pd.Series, anchor: int, break_year: int) -> pd.DataFrame:
    """Spread a census break linearly over the intercensal years, estimated.

    The gap is what `break_year` would have been had the year before it grown at its own pace,
    minus the published `break_year` value. Years strictly between `anchor` and `break_year`
    absorb a growing share of it; all other years keep the published value.
    """
    before = series[break_year - 1]
    gap = before * before / series[break_year - 2] - series[break_year]
    years = series.index.to_numpy()
    inside = (years > anchor) & (years < break_year)
    share = np.where(inside, (years - anchor) / (break_year - anchor), 0.0)
    return pd.DataFrame(
        {"year": years, "value": series.to_numpy() - gap * share, "estimated": inside}
    )


def build(data: dict) -> pd.DataFrame:
    """Assemble the tidy B1 table."""
    first, last = min(YEARS), max(YEARS)
    parts = []

    resident = data["resident"].loc[first:last]
    parts.append(
        pd.DataFrame(
            {
                "entity": "Resident in Albania",
                "year": resident.index,
                "measure": MEASURE_LOCATION,
                "value": resident.to_numpy(),
                "estimated": False,
                "source_id": "eurostat_demo_gind",
            }
        )
    )

    for entity, (code, edition, index_source) in DESTINATIONS.items():
        waves = un_waves(data[edition], code, ALBANIA)
        index = data[index_source] if index_source else None
        series = location_series(waves, last, edition, index, index_source)
        parts.append(series.assign(entity=entity, measure=MEASURE_LOCATION))

    # Rest of world = UN 2024 world total minus the named destinations it contains (Italy,
    # Greece). Germany, UK and USA have no Albania-origin rows in the 2024 edition, so they
    # are not inside its world total and must not be subtracted.
    un24 = data["un_ims_2024"]
    rest = un_waves(un24, WORLD, ALBANIA) - un_waves(un24, ITALY, ALBANIA)
    rest = rest - un_waves(un24, GREECE, ALBANIA)
    parts.append(
        location_series(rest, last, "un_ims_2024", None, "").assign(
            entity="Rest of world", measure=MEASURE_LOCATION
        )
    )

    foreign = un_waves(un24, ALBANIA, WORLD)
    parts.append(
        location_series(foreign, last, "un_ims_2024", None, "").assign(
            entity="Foreign-born residents in Albania", measure=MEASURE_FOREIGN
        )
    )

    # Census-adjusted variant: the same location stack, with the resident series' 2023-census
    # break spread back over 2012–2023. Pick one of the two measures in Tableau, never both.
    adjusted = census_backcast(resident, BACKCAST_ANCHOR, CENSUS_BREAK).assign(
        entity="Resident in Albania", source_id="eurostat_demo_gind"
    )
    abroad = [p for p in parts[1:] if (p["measure"] == MEASURE_LOCATION).all()]
    parts += [p.assign(measure=MEASURE_ADJUSTED) for p in [adjusted, *abroad]]

    out = pd.concat(parts, ignore_index=True)
    out = out[out["year"].between(first, last)]
    out["value"] = out["value"].round().astype(int)
    out["unit"] = UNIT
    out["year"] = out["year"].astype(int)
    out["estimated"] = out["estimated"].astype(bool)
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
