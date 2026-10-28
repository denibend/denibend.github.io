"""Tests for the Albania B13 calculations (H3 checks, reprojection, equal-area density)."""

import importlib.util
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

# The study folder name has hyphens, so load the script by path rather than by import.
_PATH = Path(__file__).resolve().parents[1] / "studies/01-albania-beyond-the-headlines/src/b13.py"
_spec = importlib.util.spec_from_file_location("albania_b13", _PATH)
b13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b13)


def _hexes(h3s, pops):
    """1 km x 1 km squares near Tirana, drawn in equal-area metres, handed over in Web Mercator."""
    x, y = 5_150_000, 2_050_000  # EPSG:3035 metres, central Albania
    squares = [box(x + 2000 * i, y, x + 2000 * i + 1000, y + 1000) for i in range(len(h3s))]
    gdf = gpd.GeoDataFrame({"h3": h3s, "population": pops}, geometry=squares, crs="EPSG:3035")
    return gdf.to_crs("EPSG:3857")


def test_build_measures_true_area_and_density_in_wgs84():
    out = b13.build(_hexes(["881e000000fffff", "881e100000fffff"], [250.4, 1000.0]))
    assert out.crs.to_epsg() == 4326
    assert out["area_km2"].tolist() == pytest.approx([1.0, 1.0], abs=1e-3)
    assert out["pop_per_km2"].tolist() == pytest.approx([250.4, 1000.0], abs=0.2)
    assert out["population"].tolist() == [250, 1000]
    assert out["estimated"].all()


def test_build_rejects_wrong_resolution_and_duplicates():
    with pytest.raises(ValueError, match="resolution"):
        b13.build(_hexes(["871e000000fffff"], [1.0]))
    with pytest.raises(ValueError, match="duplicate"):
        b13.build(_hexes(["881e000000fffff", "881e000000fffff"], [1.0, 2.0]))
