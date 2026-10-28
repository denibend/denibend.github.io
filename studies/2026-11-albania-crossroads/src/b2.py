"""B2 — Age and sex structure, Albania vs EU27, 1990–2025.

Run:  uv run python studies/2026-11-albania-crossroads/src/b2.py [--refresh]

Steps (kept separate): download() caches raw files in data/raw/ -> load() reads the cache
-> build() computes the tidy table (pure, tested) -> write() writes the CSV and sources.csv.

Method:
- Observed: Eurostat demo_pjangroup five-year groups on 1 January, summed into eight bands.
  Cells Eurostat flags as estimated ('e') stay estimated here.
- A year with a few missing five-year cells (EU27 2024): the sex total minus the known cells
  is split over the missing cells in proportion to their average size in the neighbouring
  complete years (estimated).
- A year with no age detail between two observed years (Albania 2022, 2024): band shares
  interpolated linearly from those years, times the year's official total (estimated).
- A year before the first observed one (Albania 1990–2001, EU27 1990–2000): band shares from
  UN World Population Prospects 2024, times the official Eurostat/INSTAT total (estimated).
  WPP gives the shape only: its Albanian levels predate the 2023 census and run ~400k high.
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
OUT_CSV = DATA_DIR / "b2_age_sex.csv"
SOURCES_CSV = DATA_DIR / "sources.csv"
MANIFEST = RAW_DIR / "b2_manifest.json"

YEARS = range(1990, 2026)
ENTITIES = {"AL": "Albania", "EU27_2020": "EU27"}
WPP_LOCATIONS = {8: "Albania", 1551: "EU27"}
SEXES = {"M": "Male", "F": "Female"}
MEASURE_PEOPLE, MEASURE_SHARE = "population", "share_of_total"
UNIT_PEOPLE, UNIT_SHARE = "people", "% of total population"

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
WPP_URL = (
    "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/"
    "WPP2024_PopulationByAge5GroupSex_Medium.csv.gz"
)

SOURCES = {
    "eurostat_demo_pjangroup": {
        "name": "Eurostat demo_pjangroup — population on 1 January by five-year age group and sex",
        "url": f"{EUROSTAT_API}/demo_pjangroup?geo=AL&geo=EU27_2020&format=JSON&lang=EN",
        "licence": "CC BY 4.0 (Eurostat reuse policy)",
        "file": "b2_eurostat_demo_pjangroup.json",
    },
    "eurostat_demo_gind": {
        "name": "Eurostat demo_gind — population on 1 January, Albania (INSTAT data)",
        "url": f"{EUROSTAT_API}/demo_gind?geo=AL&indic_de=JAN&format=JSON&lang=EN",
        "licence": "CC BY 4.0 (Eurostat reuse policy)",
        "file": "b2_eurostat_demo_gind.json",
    },
    "un_wpp_2024": {
        "name": "UN World Population Prospects 2024 — population by five-year age group and sex",
        "url": WPP_URL,
        "licence": "CC BY 3.0 IGO",
        "file": "b2_un_wpp_2024_age5.csv.gz",
    },
}

# Eurostat cells used: sixteen five-year groups plus one open 80+ cell.
FIVE_YEAR = [
    "Y_LT5",
    "Y5-9",
    "Y10-14",
    "Y15-19",
    "Y20-24",
    "Y25-29",
    "Y30-34",
    "Y35-39",
    "Y40-44",
    "Y45-49",
    "Y50-54",
    "Y55-59",
    "Y60-64",
    "Y65-69",
    "Y70-74",
    "Y75-79",
]
CELLS = [*FIVE_YEAR, "Y_GE80"]
BANDS = ["0-14", "15-24", "25-34", "35-44", "45-54", "55-64", "65-79", "80+"]
CELL_BAND = dict(
    zip(CELLS, ["0-14"] * 3 + [b for b in BANDS[1:6] for _ in (0, 1)] + ["65-79"] * 3 + ["80+"])
)
WPP_BAND = {
    **{a: "0-14" for a in ["0-4", "5-9", "10-14"]},
    **{a: "15-24" for a in ["15-19", "20-24"]},
    **{a: "25-34" for a in ["25-29", "30-34"]},
    **{a: "35-44" for a in ["35-39", "40-44"]},
    **{a: "45-54" for a in ["45-49", "50-54"]},
    **{a: "55-64" for a in ["55-59", "60-64"]},
    **{a: "65-79" for a in ["65-69", "70-74", "75-79"]},
    **{a: "80+" for a in ["80-84", "85-89", "90-94", "95-99", "100+"]},
}
KEYS = ["entity", "year", "sex", "band"]


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
        # The UN server is slow (30 MB can take many minutes), so stream with a long timeout.
        with requests.get(src["url"], headers=headers, timeout=900, stream=True) as resp:
            resp.raise_for_status()
            with path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
        manifest[source_id] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(manifest, indent=2))


# --- 2. Read the cache -------------------------------------------------------------------


def _jsonstat_frame(path: Path) -> pd.DataFrame:
    """Eurostat JSON-stat -> one row per value, one column per dimension, plus status flag."""
    d = json.loads(path.read_text())
    dims, sizes = d["id"], d["size"]
    strides = np.cumprod([1, *sizes[::-1]])[:-1][::-1]
    labels = {
        dim: {pos: code for code, pos in d["dimension"][dim]["category"]["index"].items()}
        for dim in dims
    }
    status = d.get("status", {})
    rows = []
    for key, value in d["value"].items():
        flat = int(key)
        row = {
            dim: labels[dim][(flat // stride) % size]
            for dim, stride, size in zip(dims, strides, sizes)
        }
        rows.append(row | {"value": float(value), "flag": status.get(key, "")})
    return pd.DataFrame(rows)


def load() -> dict:
    """Read every cached file into plain pandas objects."""
    raw = {sid: RAW_DIR / src["file"] for sid, src in SOURCES.items()}

    pj = _jsonstat_frame(raw["eurostat_demo_pjangroup"])
    pj = pj.assign(entity=pj["geo"].map(ENTITIES), year=pj["time"].astype(int))
    # Use the open 80+ cell where Eurostat gives it, else build it from 80-84 and 85+.
    top = pj[pj["age"].isin(["Y80-84", "Y_GE85"])].groupby(["entity", "year", "sex"])
    built = top.agg(value=("value", "sum"), flag=("flag", "max"), n=("value", "size"))
    built = built[built.pop("n") == 2].reset_index().assign(age="Y_GE80")
    given = pj[pj["age"] == "Y_GE80"][["entity", "year", "sex", "age", "value", "flag"]]
    built = built.merge(given[["entity", "year", "sex"]], how="left", indicator=True)
    built = built[built.pop("_merge") == "left_only"]
    cells = pd.concat([pj[pj["age"].isin(FIVE_YEAR)], given, built], ignore_index=True)
    cells = cells[cells["sex"].isin(SEXES)]
    totals = pj[pj["age"] == "TOTAL"][["entity", "year", "sex", "value"]]

    gind = _jsonstat_frame(raw["eurostat_demo_gind"])
    al_total = pd.Series(gind["value"].to_numpy(), index=gind["time"].astype(int)).sort_index()

    wpp = pd.read_csv(
        raw["un_wpp_2024"],
        usecols=["LocID", "Time", "AgeGrp", "PopMale", "PopFemale"],
        low_memory=False,
    )
    wpp = wpp[wpp["LocID"].isin(WPP_LOCATIONS) & wpp["Time"].between(min(YEARS), max(YEARS))]
    wpp = wpp.melt(
        id_vars=["LocID", "Time", "AgeGrp"],
        value_vars=["PopMale", "PopFemale"],
        var_name="sex",
        value_name="value",
    )
    wpp = pd.DataFrame(
        {
            "entity": wpp["LocID"].map(WPP_LOCATIONS),
            "year": wpp["Time"],
            "sex": wpp["sex"].map({"PopMale": "M", "PopFemale": "F"}),
            "band": wpp["AgeGrp"].map(WPP_BAND),
            "value": wpp["value"] * 1000,  # WPP is in thousands
        }
    )
    wpp = wpp.groupby(KEYS, as_index=False)["value"].sum()

    return {
        "cells": cells[["entity", "year", "sex", "age", "value", "flag"]],
        "totals": totals,
        "al_total": al_total,
        "wpp": wpp,
    }


# --- 3. Compute (pure) -------------------------------------------------------------------


def fill_missing_cells(cells: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    """Complete entity-year-sex groups that miss a few cells but have a published total.

    The gap (total minus known cells) is split over the missing cells in proportion to their
    average share of that sex in the nearest complete year before and after. Adds a boolean
    `filled` column. Groups that cannot be completed are left as they are.
    """
    cells = cells.assign(filled=False)
    counts = cells.groupby(["entity", "year", "sex"])["age"].nunique()
    complete = counts[counts == len(CELLS)].reset_index()[["entity", "year", "sex"]]
    partial = counts[counts < len(CELLS)].reset_index()[["entity", "year", "sex"]]
    total_of = totals.set_index(["entity", "year", "sex"])["value"]
    added = []
    for entity, year, sex in partial.itertuples(index=False):
        if (entity, year, sex) not in total_of.index:
            continue
        have = cells[(cells["entity"] == entity) & (cells["year"] == year) & (cells["sex"] == sex)]
        missing = [c for c in CELLS if c not in set(have["age"])]
        ref_years = complete[(complete["entity"] == entity) & (complete["sex"] == sex)]["year"]
        before, after = ref_years[ref_years < year], ref_years[ref_years > year]
        neighbours = [y for y in (before.max(), after.min()) if pd.notna(y)]
        if not neighbours:
            continue
        ref = cells[
            (cells["entity"] == entity) & (cells["sex"] == sex) & cells["year"].isin(neighbours)
        ]
        ref_share = ref.assign(share=ref["value"] / ref.groupby("year")["value"].transform("sum"))
        weights = ref_share[ref_share["age"].isin(missing)].groupby("age")["share"].mean()
        gap = total_of[(entity, year, sex)] - have["value"].sum()
        for age in missing:
            value = gap * weights[age] / weights.sum()
            added.append(
                {
                    "entity": entity,
                    "year": year,
                    "sex": sex,
                    "age": age,
                    "value": value,
                    "flag": "",
                    "filled": True,
                }
            )
    return pd.concat([cells, pd.DataFrame(added)], ignore_index=True) if added else cells


def cells_to_bands(cells: pd.DataFrame) -> pd.DataFrame:
    """Sum cells into the eight bands; keep only complete entity-years (both sexes, all cells).

    A band is estimated if any of its cells was filled here or flagged 'e' by Eurostat.
    """
    per_year = cells.groupby(["entity", "year"])["age"].size()
    full = per_year[per_year == len(CELLS) * len(SEXES)].index
    cells = cells.set_index(["entity", "year"]).loc[full].reset_index()
    cells = cells.assign(
        band=cells["age"].map(CELL_BAND),
        est=cells["filled"] | cells["flag"].str.contains("e"),
    )
    return cells.groupby(KEYS, as_index=False).agg(value=("value", "sum"), estimated=("est", "any"))


def shares(bands: pd.DataFrame) -> pd.Series:
    """Each band's share of its entity-year total (both sexes), as a fraction, indexed by KEYS."""
    s = bands.set_index(KEYS)["value"]
    return s / s.groupby(level=["entity", "year"]).transform("sum")


def interpolate_shape(observed: pd.DataFrame, entity: str, year: int) -> pd.Series | None:
    """Band shares for `year`, linear between the nearest observed years on either side."""
    years = observed.loc[observed["entity"] == entity, "year"].unique()
    before, after = years[years < year], years[years > year]
    if not len(before) or not len(after):
        return None
    y0, y1 = before.max(), after.min()
    s = shares(observed[(observed["entity"] == entity) & observed["year"].isin([y0, y1])])
    s0 = s.xs(y0, level="year").droplevel("entity")
    s1 = s.xs(y1, level="year").droplevel("entity")
    return s0 + (s1 - s0) * (year - y0) / (y1 - y0)


def build(data: dict) -> pd.DataFrame:
    """Assemble the tidy B2 table: population and share of total per entity-year-sex-band."""
    cells = fill_missing_cells(data["cells"], data["totals"])
    observed = cells_to_bands(cells).assign(source_id="eurostat_demo_pjangroup")

    totals = data["totals"][data["totals"]["sex"] == "T"].set_index(["entity", "year"])["value"]
    wpp_shares = shares(data["wpp"])
    parts = [observed]
    for entity in ENTITIES.values():
        have = set(observed.loc[observed["entity"] == entity, "year"])
        for year in (y for y in YEARS if y not in have):
            total, total_source = totals.get((entity, year)), "eurostat_demo_pjangroup"
            if total is None and entity == "Albania":
                total, total_source = data["al_total"][year], "eurostat_demo_gind"
            shape, shape_source = (
                interpolate_shape(observed, entity, year),
                "eurostat_demo_pjangroup",
            )
            if shape is None:
                shape = wpp_shares.xs((entity, year), level=["entity", "year"])
                shape_source = "un_wpp_2024"
            source = (
                total_source if shape_source == total_source else f"{shape_source};{total_source}"
            )
            filled = (shape * total).rename("value").reset_index()
            parts.append(filled.assign(entity=entity, year=year, estimated=True, source_id=source))

    bands = pd.concat(parts, ignore_index=True)
    share = shares(bands).rename("share").reset_index()
    bands = bands.merge(share, on=KEYS)
    people = bands.assign(
        measure=MEASURE_PEOPLE, value=bands["value"].round().astype(int), unit=UNIT_PEOPLE
    )
    pct = bands.assign(
        measure=MEASURE_SHARE, value=(bands["share"] * 100).round(4), unit=UNIT_SHARE
    )
    out = pd.concat([people, pct], ignore_index=True)
    out = out.assign(sex=out["sex"].map(SEXES)).rename(columns={"band": "age_band"})
    cols = [
        "entity",
        "year",
        "sex",
        "age_band",
        "measure",
        "value",
        "unit",
        "estimated",
        "source_id",
    ]
    return (
        out[cols]
        .sort_values(["measure", "entity", "year", "sex", "age_band"])
        .reset_index(drop=True)
    )


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
