"""Tests for the Albania B1 calculations (interpolation, extension, source merging)."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# The study folder name has hyphens, so load the script by path rather than by import.
_PATH = Path(__file__).resolve().parents[1] / "studies/01-albania-beyond-the-headlines/src/b1.py"
_spec = importlib.util.spec_from_file_location("albania_b1", _PATH)
b1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b1)


def test_interpolate_waves_linear_and_flags():
    waves = pd.Series({2000: 100.0, 2005: 200.0})
    out = b1.interpolate_waves(waves)
    assert out["year"].tolist() == [2000, 2001, 2002, 2003, 2004, 2005]
    assert out["value"].tolist() == [100, 120, 140, 160, 180, 200]
    assert out["estimated"].tolist() == [False, True, True, True, True, False]


def test_extend_flat_without_index():
    out = b1.extend(2024, 50.0, [2025, 2026])
    assert out["value"].tolist() == [50.0, 50.0]
    assert out["estimated"].all()


def test_extend_scales_with_index_and_holds_after_its_end():
    index = pd.Series({2020: 10.0, 2021: 15.0, 2022: 20.0})
    out = b1.extend(2020, 100.0, [2021, 2022, 2023], index)
    assert out["value"].tolist() == pytest.approx([150.0, 200.0, 200.0])


def test_location_series_tags_extension_source():
    waves = pd.Series({2015: 10.0, 2020: 20.0})
    index = pd.Series({2020: 1.0, 2021: 2.0})
    out = b1.location_series(waves, 2021, "un", index, "es")
    assert out.loc[out["year"] == 2021, "value"].item() == pytest.approx(40.0)
    assert out.loc[out["year"] == 2021, "source_id"].item() == "un;es"
    assert out.loc[out["year"] == 2020, "source_id"].item() == "un"


def test_merge_sources_upserts_by_id():
    old = pd.DataFrame({"source_id": ["a", "b"], "name": ["old a", "b"]})
    new = pd.DataFrame({"source_id": ["a", "c"], "name": ["new a", "c"]})
    out = b1.merge_sources(old, new)
    assert out["source_id"].tolist() == ["a", "b", "c"]
    assert out.loc[out["source_id"] == "a", "name"].item() == "new a"


def test_census_backcast_spreads_gap_linearly():
    # Flat at 100 until a census resets 2024 to 88: gap 12, spread over 2013–2023.
    series = pd.Series({y: 100.0 for y in range(2010, 2024)} | {2024: 88.0, 2025: 87.0})
    out = b1.census_backcast(series, 2012, 2024).set_index("year")
    assert out.loc[2012, "value"] == 100.0 and not out.loc[2012, "estimated"]
    assert out.loc[2018, "value"] == pytest.approx(94.0)
    assert out.loc[2023, "value"] == pytest.approx(89.0)
    assert out.loc[2024, "value"] == 88.0 and not out.loc[2024, "estimated"]
    assert out["estimated"].sum() == 11
