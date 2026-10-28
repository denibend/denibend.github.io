"""Tests for the Albania B14 calculations (Europe selection, country assignment, output)."""

import importlib.util
import json
from itertools import pairwise
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

# The study folder name has hyphens, so load the script by path rather than by import.
_PATH = Path(__file__).resolve().parents[1] / "studies/01-albania-beyond-the-headlines/src/b14.py"
_spec = importlib.util.spec_from_file_location("albania_b14", _PATH)
b14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b14)


def test_europe_countries_keeps_europe_drops_russia_adds_cyprus_cuts_overseas():
    countries = gpd.GeoDataFrame(
        {
            "ADM0_A3": ["ESP", "RUS", "CYP", "MAR"],
            "ADMIN": ["Spain", "Russia", "Cyprus", "Morocco"],
            "CONTINENT": ["Europe", "Europe", "Asia", "Africa"],
        },
        geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10), box(40, 0, 41, 1), box(0, -10, 10, -1)],
        crs="EPSG:4326",
    )
    subunits = gpd.GeoDataFrame(
        {"ADM0_A3": ["ESP"], "CONTINENT": ["Africa"]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:4326"
    )
    out = b14.europe_countries(countries, subunits).set_index("iso3")
    assert sorted(out.index) == ["CYP", "ESP"]
    assert out.loc["ESP", "geometry"].area == 100 - 4  # the "Canaries" are cut out


def test_assign_country_majority_land_then_nearest_within_reach():
    land = gpd.GeoDataFrame(
        {"iso3": ["AAA", "BBB"]},
        geometry=[box(0, 0, 10_000, 10_000), box(10_000, 0, 20_000, 10_000)],
    )
    hexes = gpd.GeoDataFrame(
        {"h3": ["inside", "border", "near_sea", "far_sea"]},
        geometry=[
            box(1000, 1000, 2000, 2000),  # all in AAA
            box(9_700, 1000, 10_700, 2000),  # 30% AAA, 70% BBB
            box(-6000, 1000, -5000, 2000),  # 5 km off AAA's coast
            box(-50_000, 1000, -49_000, 2000),  # 49 km out: dropped
        ],
    )
    out = b14.assign_country(hexes, land).set_index("h3")["iso3"]
    assert out.to_dict() == {"inside": "AAA", "border": "BBB", "near_sea": "AAA"}


def test_compact_geojson_rounds_and_orients_counter_clockwise():
    clockwise = Polygon([(0.123456, 0), (0, 1), (1, 1), (1, 0)])
    table = gpd.GeoDataFrame({"h3": ["x"]}, geometry=[clockwise], crs="EPSG:4326")
    feature = json.loads(b14.to_compact_geojson(table))["features"][0]
    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == [0.1235, 0.0]
    signed_area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in pairwise(ring))
    assert signed_area > 0  # counter-clockwise, as RFC 7946 asks
    assert "id" not in feature and pd.notna(feature["properties"]["h3"])
