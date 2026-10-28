"""B14 — Europe population density map, Kontur 3km H3 hexagons (release 2023-11-01).

Run:  uv run python studies/01-albania-beyond-the-headlines/src/b14.py [--refresh]

Steps (kept separate): download() caches the sources in data/raw/ -> load() reads them
-> build() picks Europe's hexagons, names their country and adds area and density
(pure, tested) -> write() writes the GeoJSON and sources.csv.

Same method as B13, at H3 resolution 6 (~36-40 km2 per hexagon) instead of 8: Europe at 400m
would be ~3.5M hexagons and ~1.5 GB, past GitHub's 100 MB file limit and Tableau Public's comfort.

Europe = geographic Europe without Russia and Belarus (decided 2026-10-28; Turkey and the
Caucasus are outside it already):
- Countries: Natural Earth 1:10m, German point of view (Crimea in Ukraine, Kosovo separate,
  Cyprus one island) - the closest Natural Earth offers to the EU's view of borders.
- Kept: every country Natural Earth puts in Europe, except RUS and BLR, plus the island of
  Cyprus (EU member, incl. the UK Sovereign Base Areas; Natural Earth puts it in Asia).
- Cut out: parts of those countries that Natural Earth's map subunits put outside Europe
  (Canaries, Madeira, Azores, Ceuta, Melilla, French and Dutch overseas, Bouvet).
- A hexagon goes to the country holding most of its land. Hexagons that touch no land
  (islets missing at 1:10m) go to the nearest country within MAX_SEA_KM, or are dropped.

Output: compact GeoJSON (no spaces, 4 decimals = ~10 m) is ~79 MB, too big for the repo, so
the Tableau-ready .geojson is git-ignored and a zipped copy (~7 MB, byte-identical on rerun)
is the committed snapshot. Unzip it to get the .geojson back.
"""

import gzip
import json
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely

STUDY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = STUDY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_GEOJSON = DATA_DIR / "b14_europe_population_hexagons.geojson"  # git-ignored
OUT_ZIP = DATA_DIR / "b14_europe_population_hexagons.geojson.zip"  # committed
SOURCES_CSV = DATA_DIR / "sources.csv"
MANIFEST = RAW_DIR / "b14_manifest.json"

KONTUR = "kontur_population_20231101_r6"
NE_COUNTRIES = "natural_earth_10m_admin_0_countries_deu"
NE_SUBUNITS = "natural_earth_10m_admin_0_map_subunits"
NE_URL = "https://naciscdn.org/naturalearth/10m/cultural"
NE_LICENCE = "Public domain (Natural Earth terms of use)"
SOURCES = {
    KONTUR: {
        "name": "Kontur Population: Global population for 3km H3 hexagons (resolution 6), "
        "release 2023-11-01, via HDX",
        "url": "https://geodata-eu-central-1-kontur-public.s3.eu-central-1.amazonaws.com/"
        "kontur_datasets/kontur_population_20231101_r6.gpkg.gz",
        "licence": "CC BY 4.0",
        "file": "b14_kontur_population_20231101_r6.gpkg.gz",
    },
    NE_COUNTRIES: {
        "name": "Natural Earth 1:10m admin 0 countries, German point of view (country borders)",
        "url": f"{NE_URL}/ne_10m_admin_0_countries_deu.zip",
        "licence": NE_LICENCE,
        "file": "b14_ne_10m_admin_0_countries_deu.zip",
    },
    NE_SUBUNITS: {
        "name": "Natural Earth 1:10m admin 0 map subunits (to cut overseas parts)",
        "url": f"{NE_URL}/ne_10m_admin_0_map_subunits.zip",
        "licence": NE_LICENCE,
        "file": "b14_ne_10m_admin_0_map_subunits.zip",
    },
}
H3_RESOLUTION = 6
EXCLUDED = {"RUS", "BLR"}
ADDED = {"CYP", "ESB", "WSB"}  # Cyprus and the UK bases on it; Natural Earth says Asia
BBOX_4326 = (-32.0, 33.0, 46.0, 82.0)  # read window: everything Europe could reach
MAX_SEA_KM = 10
DECIMALS = 4
AREA_CRS = "EPSG:3035"
COLUMNS = [
    "h3",
    "country",
    "iso3",
    "population",
    "area_km2",
    "pop_per_km2",
    "estimated",
    "source_id",
    "geometry",
]


# --- 1. Download -------------------------------------------------------------------------


def download(refresh: bool = False) -> None:
    """Fetch every source into data/raw/ unless already cached; record the download time.

    The Kontur GeoPackage is also unzipped, because GDAL needs random access to read it.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for source_id, src in SOURCES.items():
        path = RAW_DIR / src["file"]
        if path.exists() and not refresh and source_id in manifest:
            continue
        with requests.get(src["url"], timeout=600, stream=True) as resp:
            resp.raise_for_status()
            with path.open("wb") as f:
                shutil.copyfileobj(resp.raw, f)
        manifest[source_id] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    gpkg = _kontur_gpkg()
    if refresh or not gpkg.exists():
        with gzip.open(RAW_DIR / SOURCES[KONTUR]["file"]) as src, gpkg.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    MANIFEST.write_text(json.dumps(manifest, indent=2))


def _kontur_gpkg() -> Path:
    return RAW_DIR / SOURCES[KONTUR]["file"].removesuffix(".gz")


# --- 2. Read the cache -------------------------------------------------------------------


def load() -> dict:
    """Kontur hexagons inside the read window, and the two Natural Earth layers."""
    window = gpd.GeoSeries.from_xy([BBOX_4326[0], BBOX_4326[2]], [BBOX_4326[1], BBOX_4326[3]])
    bbox = tuple(window.set_crs("EPSG:4326").to_crs("EPSG:3857").total_bounds)
    return {
        "hexes": gpd.read_file(_kontur_gpkg(), bbox=bbox),
        "countries": gpd.read_file(RAW_DIR / SOURCES[NE_COUNTRIES]["file"]),
        "subunits": gpd.read_file(RAW_DIR / SOURCES[NE_SUBUNITS]["file"]),
    }


# --- 3. Compute (pure) -------------------------------------------------------------------


def h3_resolution(h3: pd.Series) -> pd.Series:
    """Resolution of an H3 cell index given as hex text: the second hex digit (bits 52-55)."""
    return h3.str[1].map(lambda c: int(c, 16))


def europe_countries(countries: gpd.GeoDataFrame, subunits: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Countries kept as Europe (iso3, country, geometry), with their non-European parts cut out."""
    keep = countries["ADM0_A3"].isin(ADDED) | (
        (countries["CONTINENT"] == "Europe") & ~countries["ADM0_A3"].isin(EXCLUDED)
    )
    europe = countries.loc[keep, ["ADM0_A3", "ADMIN", "geometry"]]
    europe = europe.rename(columns={"ADM0_A3": "iso3", "ADMIN": "country"})
    away = subunits[
        subunits["ADM0_A3"].isin(europe["iso3"])
        & ~subunits["ADM0_A3"].isin(ADDED)
        & (subunits["CONTINENT"] != "Europe")
    ].to_crs(europe.crs)
    if not away.empty:
        europe = europe.assign(geometry=europe.geometry.difference(away.union_all()))
    return europe[~europe.geometry.is_empty].reset_index(drop=True)


def assign_country(hexes: gpd.GeoDataFrame, land: gpd.GeoDataFrame) -> pd.DataFrame:
    """Each hexagon's country: most land area wins; no land -> nearest within MAX_SEA_KM.

    hexes: h3 + geometry; land: iso3 + geometry for every country that could touch them.
    Both in the same metric CRS. Returns h3, iso3 (hexagons left unassigned are absent).
    """
    hexes, land = (
        hexes.reset_index(drop=True),
        land.reset_index(drop=True),
    )  # rows looked up by label
    pairs = gpd.sjoin(hexes[["h3", "geometry"]], land[["iso3", "geometry"]], predicate="intersects")
    pairs = pairs.reset_index().rename(columns={"index": "hex_row"})
    shared = pairs["h3"].duplicated(keep=False)
    one = pairs.loc[~shared, ["h3", "iso3"]]

    border = pairs[shared]
    hex_geom = hexes.geometry.loc[border["hex_row"]].reset_index(drop=True)
    land_geom = land.geometry.loc[border["index_right"]].reset_index(drop=True)
    border = border.assign(land_area=hex_geom.intersection(land_geom).area.to_numpy())
    best = border.sort_values(["h3", "land_area"], ascending=[True, False]).drop_duplicates("h3")

    at_sea = hexes[~hexes["h3"].isin(pairs["h3"])]
    near = gpd.sjoin_nearest(
        at_sea[["h3", "geometry"]], land[["iso3", "geometry"]], max_distance=MAX_SEA_KM * 1000
    ).drop_duplicates("h3")
    return pd.concat([one, best[["h3", "iso3"]], near[["h3", "iso3"]]], ignore_index=True)


def build(data: dict) -> gpd.GeoDataFrame:
    """Europe's hexagons in WGS84 with country, population, equal-area km2 and people per km2."""
    hexes = data["hexes"]
    if not h3_resolution(hexes["h3"]).eq(H3_RESOLUTION).all():
        raise ValueError(f"expected H3 resolution {H3_RESOLUTION} only")
    if hexes["h3"].duplicated().any():
        raise ValueError("duplicate H3 cells")

    window = gpd.GeoSeries.from_xy([BBOX_4326[0], BBOX_4326[2]], [BBOX_4326[1], BBOX_4326[3]])
    countries = data["countries"].cx[BBOX_4326[0] : BBOX_4326[2], BBOX_4326[1] : BBOX_4326[3]]
    europe = europe_countries(countries, data["subunits"])
    others = countries[~countries["ADM0_A3"].isin(europe["iso3"])]
    others = others.rename(columns={"ADM0_A3": "iso3"})[["iso3", "geometry"]]
    land = pd.concat([europe[["iso3", "geometry"]], others], ignore_index=True)
    land = land.clip(window.total_bounds).to_crs(AREA_CRS)

    # Assign in equal-area metres: Web Mercator doubles distances and areas at 60N.
    owner = assign_country(hexes[["h3", "geometry"]].to_crs(AREA_CRS), land)
    names = europe.set_index("iso3")["country"]
    kept = hexes.merge(owner[owner["iso3"].isin(names.index)], on="h3")
    area = kept.geometry.to_crs(AREA_CRS).area / 1e6
    out = kept.to_crs("EPSG:4326").assign(
        country=kept["iso3"].map(names),
        population=kept["population"].round().astype(int),
        area_km2=area.round(2),
        pop_per_km2=(kept["population"] / area).round(1),
        estimated=True,
        source_id=f"{KONTUR};{NE_COUNTRIES};{NE_SUBUNITS}",
    )
    return out[COLUMNS].sort_values(["iso3", "h3"]).reset_index(drop=True)


def merge_sources(existing: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Upsert rows by source_id so each brief can add to the shared sources.csv."""
    if existing is None or existing.empty:
        return new.reset_index(drop=True)
    kept = existing[~existing["source_id"].isin(new["source_id"])]
    return pd.concat([kept, new], ignore_index=True).sort_values("source_id").reset_index(drop=True)


# --- 4. Write ----------------------------------------------------------------------------


def to_compact_geojson(table: gpd.GeoDataFrame) -> str:
    """RFC 7946 GeoJSON (WGS84, counter-clockwise outer rings), rounded, without whitespace."""
    geom = shapely.transform(table.geometry.to_numpy(), lambda xy: np.round(xy, DECIMALS))
    out = table.set_geometry(gpd.GeoSeries(shapely.orient_polygons(geom), crs=table.crs))
    return out.to_json(drop_id=True, separators=(",", ":"))


def write(table: gpd.GeoDataFrame) -> None:
    text = to_compact_geojson(table)
    OUT_GEOJSON.write_text(text)
    # Fixed timestamp so an unchanged result gives a byte-identical zip (no new git blob).
    info = zipfile.ZipInfo(OUT_GEOJSON.name, date_time=(2023, 11, 1, 0, 0, 0))
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr(info, text, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

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


def summary(table: gpd.GeoDataFrame) -> str:
    return (
        f"hexagons={len(table)} countries={table['iso3'].nunique()} "
        f"population={table['population'].sum():,} area_km2={table['area_km2'].sum():,.0f} "
        f"estimated={int(table['estimated'].sum())}"
    )


if __name__ == "__main__":
    download(refresh="--refresh" in sys.argv)
    result = build(load())
    write(result)
    print(summary(result))
