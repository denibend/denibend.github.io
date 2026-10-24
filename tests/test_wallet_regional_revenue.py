"""Data-quality checks on the hand-collected regional revenue dataset."""

import pandas as pd
import pytest

from studies.luxury_wallet.prepare import REGIONAL_REVENUE_CSV, region_shares

VALID_GROUPS = {
    "Europe",
    "EMEA",
    "Americas",
    "Japan",
    "Asia-Pacific excl. Japan",
    "Asia-Pacific incl. Japan",
    "Other",
    "Total",
}


@pytest.fixture(scope="module")
def data():
    return pd.read_csv(REGIONAL_REVENUE_CSV)


def test_every_company_year_has_one_total_and_a_source(data):
    totals = data[data["region_group"] == "Total"].groupby(["company", "fiscal_year"]).size()
    assert (totals == 1).all()
    assert data["source_url"].str.startswith("http").all()


def test_regions_sum_to_reported_total(data):
    parts = data[data["region_group"] != "Total"].groupby(["company", "fiscal_year"])["value"].sum()
    totals = data[data["region_group"] == "Total"].set_index(["company", "fiscal_year"])["value"]
    gap = (parts / totals - 1).abs()
    assert (gap < 0.005).all(), gap[gap >= 0.005]


def test_groups_and_units_are_consistent(data):
    assert set(data["region_group"]) <= VALID_GROUPS
    assert (data.groupby(["company", "fiscal_year"])["unit"].nunique() == 1).all()


def test_core_years_cover_all_eight_companies(data):
    years = data.groupby("company")["fiscal_year"].apply(set)
    assert len(years) == 8
    assert all({2019, 2022, 2023, 2024, 2025} <= y for y in years)


def test_region_shares_sum_to_100(data):
    shares = region_shares(data)
    assert shares.sum(axis=1).sub(100).abs().max() < 0.5
