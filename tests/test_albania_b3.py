"""Tests for the Albania B3 calculations (exchange-rate splice and USD -> EUR conversion)."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# The study folder name has hyphens, so load the script by path rather than by import.
_PATH = Path(__file__).resolve().parents[1] / "studies/01-albania-beyond-the-headlines/src/b3.py"
_spec = importlib.util.spec_from_file_location("albania_b3", _PATH)
b3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b3)


def test_usd_per_eur_uses_ecu_before_1999_and_ecb_after():
    ecb = pd.Series({1999: 1.07, 2000: 0.92})
    ecu = pd.Series({1997: 1.13, 1998: 1.12, 1999: 9.99, 2000: 9.99})
    out = b3.usd_per_eur(ecb, ecu).set_index("year")
    assert out["rate"].tolist() == [1.13, 1.12, 1.07, 0.92]
    assert out.loc[1998, "source_id"] == "eurostat_ert_bil_eur_a"
    assert out.loc[1999, "source_id"] == "ecb_exr_usd"


def test_usd_to_eur_divides_by_rate_and_drops_years_without_rate():
    usd = pd.DataFrame({"entity": "X", "year": [1998, 1999, 2030], "value": [112.0, 107.0, 1.0]})
    rates = b3.usd_per_eur(pd.Series({1999: 1.07}), pd.Series({1998: 1.12}))
    out = b3.usd_to_eur(usd, rates, "wb").set_index("year")
    assert out["value"].tolist() == pytest.approx([100.0, 100.0])
    assert out.loc[1999, "source_id"] == "wb;ecb_exr_usd"


def test_build_ratio_and_eurostat_splice():
    def wb(values):
        return pd.DataFrame([{"entity": e, "year": y, "value": v} for (e, y), v in values.items()])

    data = {
        "ecb_exr_usd": pd.Series({1999: 2.0}),
        "eurostat_ert_bil_eur_a": pd.Series({1994: 2.0}),
        "eurostat_nama_10_pc": pd.Series({1999: 777.0}),
        "wb_ny_gdp_pcap_cd": wb(
            {("Albania", 1994): 10.0, ("EU27", 1994): 20.0, ("EU27", 1999): 999.0}
        ),
        "wb_ny_gdp_mktp_cd": wb({("Albania", 1999): 1000.0}),
        "wb_bx_trf_pwkr_cd_dt": wb({("Albania", 1999): 50.0}),
    }
    out = b3.build(data).set_index(["entity", "year", "measure"])["value"]
    assert out[("Albania", 1994, "gdp_per_capita_eur")] == 5.0
    assert out[("EU27", 1994, "gdp_per_capita_eur")] == 10.0
    assert out[("EU27", 1999, "gdp_per_capita_eur")] == 777.0  # Eurostat wins from 1995
    assert out[("Albania", 1999, "remittances_pct_gdp")] == 5.0
    assert out[("Albania", 1999, "remittances_received_eur")] == 25.0
