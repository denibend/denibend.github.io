"""Tests for the Albania B2 calculations (cell filling, banding, shape interpolation)."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# The study folder name has hyphens, so load the script by path rather than by import.
_PATH = Path(__file__).resolve().parents[1] / "studies/2026-11-albania-crossroads/src/b2.py"
_spec = importlib.util.spec_from_file_location("albania_b2", _PATH)
b2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b2)


def _cells(year: int, values: dict | None = None, drop: tuple = (), flag: dict | None = None):
    """One entity-year of cells for both sexes; every cell 10 unless overridden."""
    values, flag = values or {}, flag or {}
    return pd.DataFrame(
        [
            {
                "entity": "X",
                "year": year,
                "sex": sex,
                "age": age,
                "value": float(values.get(age, 10)),
                "flag": flag.get(age, ""),
            }
            for sex in ("M", "F")
            for age in b2.CELLS
            if age not in drop
        ]
    )


def test_fill_missing_cells_splits_gap_by_neighbour_weights():
    cells = pd.concat(
        [
            _cells(2023, {"Y30-34": 10, "Y45-49": 30}),
            _cells(2024, drop=("Y30-34", "Y45-49")),
            _cells(2025, {"Y30-34": 10, "Y45-49": 30}),
        ]
    )
    # 15 known cells of 10 = 150; published total 200 leaves a gap of 50, split 10:30.
    totals = pd.DataFrame({"entity": "X", "year": 2024, "sex": ["M", "F"], "value": 200.0})
    out = b2.fill_missing_cells(cells, totals)
    got = out[(out["year"] == 2024) & (out["sex"] == "M")].set_index("age")
    assert got.loc["Y30-34", "value"] == pytest.approx(12.5)
    assert got.loc["Y45-49", "value"] == pytest.approx(37.5)
    assert got["filled"].sum() == 2


def test_cells_to_bands_sums_and_flags():
    out = b2.cells_to_bands(_cells(2020, flag={"Y80-84": "", "Y_GE80": "e"}).assign(filled=False))
    m = out[out["sex"] == "M"].set_index("band")
    assert m.loc["0-14", "value"] == 30 and m.loc["65-79", "value"] == 30
    assert m.loc["15-24", "value"] == 20 and m.loc["80+", "value"] == 10
    assert m.loc["80+", "estimated"] and not m.loc["0-14", "estimated"]


def test_cells_to_bands_drops_incomplete_years():
    cells = _cells(2020, drop=("Y5-9",)).assign(filled=False)
    assert b2.cells_to_bands(cells).empty


def test_interpolate_shape_midpoint():
    def bands(year, young):
        return pd.DataFrame(
            {
                "entity": "X",
                "year": year,
                "sex": ["M", "M"],
                "band": ["0-14", "80+"],
                "value": [young, 100 - young],
            }
        )

    observed = pd.concat([bands(2020, 40.0), bands(2022, 20.0)])
    shape = b2.interpolate_shape(observed, "X", 2021)
    assert shape[("M", "0-14")] == pytest.approx(0.30)
    assert shape.sum() == pytest.approx(1.0)
    assert b2.interpolate_shape(observed, "X", 2019) is None
