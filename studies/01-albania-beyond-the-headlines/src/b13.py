"""B13 — Albania population density map, Kontur 400m H3 hexagons (release 2023-11-01).

Run:  uv run python studies/01-albania-beyond-the-headlines/src/b13.py [--refresh]

Steps (kept separate): download() caches the gzipped GeoPackage in data/raw/ -> load() reads
it -> build() reprojects and adds area and density (pure, tested) -> write() writes the
GeoJSON and sources.csv.

Output is GeoJSON, not GeoPackage: Tableau's spatial-file connector reads GeoJSON, Shapefile,
KML, TopoJSON, MapInfo and File Geodatabase, but not .gpkg. GeoJSON must be WGS84 (EPSG:4326),
so the Web Mercator (EPSG:3857) source is reprojected. Hexagon area is measured in ETRS89-LAEA
(EPSG:3035, equal-area), because Web Mercator areas are inflated ~1.7x at Albania's latitude.
Every population value is modelled by Kontur, so every row is estimated = TRUE.
"""

import gzip
import io
import json
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

STUDY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = STUDY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_GEOJSON = DATA_DIR / "b13_population_hexagons.geojson"
SOURCES_CSV = DATA_DIR / "sources.csv"
MANIFEST = RAW_DIR / "b13_manifest.json"

SOURCE_ID = "kontur_population_al_20231101"
SOURCES = {
    SOURCE_ID: {
        "name": "Kontur Population: Albania, population for 400m H3 hexagons (resolution 8), "
        "release 2023-11-01, via HDX",
        "url": "https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/"
        "kontur_population_AL_20231101.gpkg.gz",
        "licence": "CC BY 4.0",
        "file": "b13_kontur_population_AL_20231101.gpkg.gz",
    },
}
H3_RESOLUTION = 8  # Kontur's "400m" hexagons; mean area ~0.74 km2
AREA_CRS = "EPSG:3035"
COLUMNS = ["h3", "population", "area_km2", "pop_per_km2", "estimated", "source_id", "geometry"]


# --- 1. Download -------------------------------------------------------------------------


def download(refresh: bool = False) -> None:
    """Fetch every source into data/raw/ unless already cached; record the download time."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for source_id, src in SOURCES.items():
        path = RAW_DIR / src["file"]
        if path.exists() and not refresh and source_id in manifest:
            continue
        resp = requests.get(src["url"], timeout=300)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        manifest[source_id] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(manifest, indent=2))


# --- 2. Read the cache -------------------------------------------------------------------


def load() -> gpd.GeoDataFrame:
    """Decompress the cached GeoPackage in memory and read its one layer."""
    raw = gzip.decompress((RAW_DIR / SOURCES[SOURCE_ID]["file"]).read_bytes())
    with warnings.catch_warnings():  # GDAL dislikes the in-memory file having no .gpkg name
        warnings.filterwarnings("ignore", message=".*non conformant file extension")
        return gpd.read_file(io.BytesIO(raw))


# --- 3. Compute (pure) -------------------------------------------------------------------


def h3_resolution(h3: pd.Series) -> pd.Series:
    """Resolution of an H3 cell index given as hex text: the second hex digit (bits 52-55)."""
    return h3.str[1].map(lambda c: int(c, 16))


def build(hexes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """WGS84 hexagons with population, equal-area km2 and people per km2."""
    if not h3_resolution(hexes["h3"]).eq(H3_RESOLUTION).all():
        raise ValueError(f"expected H3 resolution {H3_RESOLUTION} only")
    if hexes["h3"].duplicated().any():
        raise ValueError("duplicate H3 cells")
    area = hexes.geometry.to_crs(AREA_CRS).area / 1e6
    out = hexes.to_crs("EPSG:4326").assign(
        population=hexes["population"].round().astype(int),
        area_km2=area.round(4),
        pop_per_km2=(hexes["population"] / area).round(1),
        estimated=True,
        source_id=SOURCE_ID,
    )
    return out[COLUMNS].sort_values("h3").reset_index(drop=True)


def merge_sources(existing: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Upsert rows by source_id so each brief can add to the shared sources.csv."""
    if existing is None or existing.empty:
        return new.reset_index(drop=True)
    kept = existing[~existing["source_id"].isin(new["source_id"])]
    return pd.concat([kept, new], ignore_index=True).sort_values("source_id").reset_index(drop=True)


# --- 4. Write ----------------------------------------------------------------------------


def write(table: gpd.GeoDataFrame) -> None:
    # RFC 7946 GeoJSON: WGS84, counter-clockwise outer rings; 6 decimals is ~0.1 m.
    OUT_GEOJSON.unlink(missing_ok=True)
    table.to_file(
        OUT_GEOJSON, driver="GeoJSON", engine="pyogrio", RFC7946="YES", COORDINATE_PRECISION=6
    )

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
        f"hexagons={len(table)} population={table['population'].sum():,} "
        f"area_km2={table['area_km2'].sum():,.0f} max_pop_per_km2={table['pop_per_km2'].max():,.0f} "
        f"estimated={int(table['estimated'].sum())}"
    )


if __name__ == "__main__":
    download(refresh="--refresh" in sys.argv)
    result = build(load())
    write(result)
    print(summary(result))
