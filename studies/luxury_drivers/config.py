"""Study 01 settings: universe, factors and sample period."""

from pathlib import Path

STUDY_DIR = Path(__file__).parent
RAW_DIR = STUDY_DIR / "data" / "raw"

START = "2013-01-01"  # fetch a year early so the first 2014 returns have a prior price
SAMPLE_START = "2014-01-01"

# Yahoo ticker -> (display name, trading currency as quoted by Yahoo)
STOCKS = {
    "MC.PA": ("LVMH", "EUR"),
    "RMS.PA": ("Hermès", "EUR"),
    "KER.PA": ("Kering", "EUR"),
    "CFR.SW": ("Richemont", "CHF"),
    "MONC.MI": ("Moncler", "EUR"),
    "BRBY.L": ("Burberry", "GBp"),  # pence; converted to GBP before FX conversion
    "1913.HK": ("Prada", "HKD"),
    "BC.MI": ("Brunello Cucinelli", "EUR"),
}

# Positioning tiers (classification agreed with Denisa, 2026-10-23).
TIERS = {
    "Top tier": ["Hermès", "Brunello Cucinelli"],
    "Hard luxury": ["Richemont"],
    "Diversified group": ["LVMH"],
    "Aspirational / fashion-led": ["Kering", "Burberry", "Prada", "Moncler"],
}

# Factor series. Indices are price indices in local currency.
FACTORS = {
    "^STOXX": "STOXX Europe 600",
    "^HSI": "Hang Seng",
    "MCHI": "iShares MSCI China ETF (robustness)",
}

# Event study (daily): each stock's benchmark index. Prada is compared with the Hang Seng in
# local currency because its trading hours do not overlap with Europe's.
EVENT_MARKET = {"1913.HK": "^HSI"}
EVENT_MARKET_DEFAULT = "^STOXX"

# ECB reference rates: units of foreign currency per 1 EUR.
ECB_CURRENCIES = ["USD", "CHF", "GBP", "HKD", "CNY"]
