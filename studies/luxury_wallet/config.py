"""Study 02 settings: series codes and source parameters."""

from pathlib import Path

STUDY_DIR = Path(__file__).parent
RAW_DIR = STUDY_DIR / "data" / "raw"

# BEA personal consumption expenditures, monthly. For each category: current dollars (…RC) and the
# Fisher price index (…RG); real spending = nominal / price index. The chained-dollar series for the
# detailed categories only start in 2007, so deflating ourselves gives the full history from 1959.
BEA_CATEGORIES = {
    "jewelry_watches": "DJRY",
    "clothing_footwear": "DCLO",
    "luggage": "DLUG",
    "accommodations": "DACC",
    "air_transport": "DAIT",
    "package_tours": "DHOL",
    "food_services": "DFSE",
    "recreation_services": "DRCA",
    "goods": "DGDS",
    "services": "DSER",
    "total_pce": "DPCE",
}

# FRED: income, saving, aggregate wealth, prices (all public-domain US government series).
FRED_SERIES = {
    "DSPIC96": "Real disposable personal income (chained 2017 $, monthly)",
    "PSAVERT": "Personal saving rate (%, monthly)",
    "TNWBSHNO": "Households and nonprofits: net worth (millions $, quarterly)",
    "PCEPI": "PCE price index (monthly)",
    "USSTHPI": "FHFA all-transactions house price index (quarterly)",
}

# ECB Distributional Wealth Accounts: household net wealth by wealth group.
ECB_DWA_AREAS = ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "I9"]  # I9 = euro area aggregate
# Bottom 50%, deciles 6-9 (summed later into the "middle 40%") and the top decile.
ECB_DWA_GROUPS = ["B50", "D6", "D7", "D8", "D9", "D10"]
# Wealth by asset type, all households: equity & fund shares (F5) and housing (NUN).
ECB_DWA_ASSETS = ["F5", "NUN"]

# Eurostat datasets (filters passed as query parameters to the statistics API).
EUROSTAT_GEOS = ["EU27_2020", "DE", "FR", "IT", "ES", "NL", "BE", "AT"]
EUROSTAT_QUERIES = {
    "spending_by_purpose": (
        "nama_10_cp18",
        {
            "unit": ["CP_MEUR", "PD20_EUR"],
            "coicop18": [
                "TOTAL",
                "CP03",
                "CP031",
                "CP09",
                "CP094",
                "CP098",
                "CP11",
                "CP111",
                "CP112",
                "CP13",
                "CP132",
            ],
            "geo": EUROSTAT_GEOS,
            "sinceTimePeriod": "2015",
        },
    ),
    "household_income": (
        "nasa_10_nf_tr",
        {
            "unit": "CP_MEUR",
            "sector": "S14_S15",
            "direct": "RECV",
            "na_item": "B6G",
            "geo": EUROSTAT_GEOS,
            "sinceTimePeriod": "2010",
        },
    ),
    # Quarterly, seasonally and calendar adjusted (SCA). P312 = semi-durable goods (clothing,
    # footwear, travel goods...); jewellery & watches are classed as durable (P311), with cars.
    "spending_by_durability_q": (
        "namq_10_fcs",
        {
            "unit": ["CLV20_MEUR", "CP_MEUR"],
            "s_adj": "SCA",
            "na_item": ["P31_S14", "P311_S14", "P312_S14", "P313_S14", "P314_S14"],
            "geo": EUROSTAT_GEOS,
            "sinceTimePeriod": "2008-Q1",
        },
    ),
    "household_income_q": (
        "nasq_10_nf_tr",
        {
            "unit": "CP_MEUR",
            "s_adj": "SCA",
            "na_item": "B6G",
            "sector": "S14_S15",
            "direct": "RECV",
            "geo": EUROSTAT_GEOS,
            "sinceTimePeriod": "2008-Q1",
        },
    ),
    "budget_structure_by_quintile": (
        "hbs_str_t223",
        {"coicop": ["CP03", "CP09", "CP096", "CP11", "CP12"], "geo": EUROSTAT_GEOS},
    ),
    "consumer_confidence": (
        "ei_bsco_m",
        {
            "indic": "BS-CSMCI",
            "s_adj": "SA",
            "unit": "BAL",
            "geo": ["EU27_2020", "EA20"],
            "sinceTimePeriod": "2010-01",
        },
    ),
    "tourist_nights": (
        "tour_occ_nim",
        {
            "c_resid": ["DOM", "FOR"],
            "unit": "NR",
            "nace_r2": "I551-I553",
            "geo": ["EU27_2020", "FR", "IT", "ES", "DE"],
            "sinceTimePeriod": "2012-01",
        },
    ),
}

# Hong Kong Census & Statistics Department, table 620-67002: retail sales value by outlet type.
HK_RETAIL_TABLE = "620-67002"
HK_OUTLETS = ["Jewellery, watches and clocks, and valuable gifts", "Total"]
