"""
Synthetic market data generator for the Eliquis (Apixaban) generic entry scenario.

Based on publicly available market intelligence:
- Eliquis: ~14.2B USD global peak sales (2025), ~1.8B EUR in Germany
- EU patent expiry: May 2026
- Indication: Anticoagulant (NVAF, VTE treatment/prophylaxis)
- Key competitors: Xarelto (rivaroxaban), Edoxaban, Dabigatran
- Expected generic entrants: 5-8 in first 12 months (EU)
- Analyst consensus: -15% year 1, up to -92% by 2030 vs peak
"""

import pandas as pd
import numpy as np


def generate_eliquis_market_data() -> dict:
    """Generate realistic synthetic market data for the German anticoagulant market."""

    # --- Market Definition ---
    market = {
        "name": "Orale Antikoagulantien (NOAK/DOAK) – Deutschland",
        "indication": "Nicht-valvuläres Vorhofflimmern (NVAF), VTE-Behandlung & Prophylaxe",
        "total_market_trx_monthly": 4_200_000,  # ~4.2M TRx/Monat in DE (NOAK segment)
        "total_market_revenue_monthly_eur": 285_000_000,  # ~285M EUR/Monat
        "currency": "EUR",
        "geography": "Deutschland",
        "data_source": "Synthetisch (angelehnt an öffentliche Marktdaten)",
    }

    # --- Products in Market (pre-generic entry) ---
    products = {
        "Eliquis (Apixaban)": {
            "company": "BMS / Pfizer",
            "type": "Originator",
            "market_share_trx": 0.42,  # 42% volume share
            "market_share_revenue": 0.45,  # 45% value share (premium)
            "price_per_trx_eur": 91.50,  # Monatliche Therapiekosten
            "ddd_price_eur": 3.05,
            "patent_expiry": "2026-05",
            "launch_year": 2011,
        },
        "Xarelto (Rivaroxaban)": {
            "company": "Bayer",
            "type": "Originator",
            "market_share_trx": 0.35,
            "market_share_revenue": 0.36,
            "price_per_trx_eur": 87.80,
            "ddd_price_eur": 2.93,
            "patent_expiry": "2024-04",  # Already off-patent but limited generics
            "launch_year": 2008,
        },
        "Lixiana (Edoxaban)": {
            "company": "Daiichi Sankyo",
            "type": "Originator",
            "market_share_trx": 0.15,
            "market_share_revenue": 0.13,
            "price_per_trx_eur": 74.20,
            "ddd_price_eur": 2.47,
            "patent_expiry": "2031",
            "launch_year": 2015,
        },
        "Pradaxa (Dabigatran)": {
            "company": "Boehringer Ingelheim",
            "type": "Originator",
            "market_share_trx": 0.08,
            "market_share_revenue": 0.06,
            "price_per_trx_eur": 64.00,
            "ddd_price_eur": 2.13,
            "patent_expiry": "2025",
            "launch_year": 2008,
        },
    }

    # --- Historical quarterly data (8 quarters pre-LOE) ---
    quarters_history = pd.date_range("2024-Q1", periods=8, freq="QS")
    np.random.seed(42)

    history_rows = []
    for i, q in enumerate(quarters_history):
        # Slight market growth (~2% annually)
        growth_factor = 1 + (i * 0.005)
        total_trx_q = market["total_market_trx_monthly"] * 3 * growth_factor

        for product_name, p in products.items():
            # Small random fluctuation in share
            share_noise = np.random.normal(0, 0.005)
            share = max(0.01, p["market_share_trx"] + share_noise)
            trx = int(total_trx_q * share)
            revenue = trx * p["price_per_trx_eur"]

            history_rows.append({
                "quarter": f"{q.year}-Q{(q.month - 1) // 3 + 1}",
                "date": q,
                "product": product_name,
                "company": p["company"],
                "type": p["type"],
                "trx": trx,
                "revenue_eur": round(revenue, 2),
                "market_share_trx": round(share, 4),
                "price_per_trx_eur": p["price_per_trx_eur"],
            })

    historical_df = pd.DataFrame(history_rows)

    # --- Generic entrants configuration ---
    generic_entrants = [
        {
            "name": "Apixaban Zentiva",
            "company": "Zentiva (Sanofi)",
            "launch_quarter": "2026-Q2",
            "launch_month_offset": 0,  # Day 1 launch
            "expected_peak_share": 0.12,
            "price_discount_vs_originator": 0.40,  # 40% discount
        },
        {
            "name": "Apixaban Teva",
            "company": "Teva",
            "launch_quarter": "2026-Q2",
            "launch_month_offset": 1,
            "expected_peak_share": 0.10,
            "price_discount_vs_originator": 0.45,
        },
        {
            "name": "Apixaban STADA",
            "company": "STADA",
            "launch_quarter": "2026-Q3",
            "launch_month_offset": 3,
            "expected_peak_share": 0.09,
            "price_discount_vs_originator": 0.50,
        },
        {
            "name": "Apixaban Sandoz",
            "company": "Sandoz",
            "launch_quarter": "2026-Q3",
            "launch_month_offset": 4,
            "expected_peak_share": 0.08,
            "price_discount_vs_originator": 0.50,
        },
        {
            "name": "Apixaban Mylan",
            "company": "Viatris",
            "launch_quarter": "2026-Q4",
            "launch_month_offset": 6,
            "expected_peak_share": 0.07,
            "price_discount_vs_originator": 0.55,
        },
        {
            "name": "Apixaban AbZ",
            "company": "AbZ Pharma",
            "launch_quarter": "2027-Q1",
            "launch_month_offset": 9,
            "expected_peak_share": 0.05,
            "price_discount_vs_originator": 0.60,
        },
    ]

    # --- Scenario defaults ---
    scenarios = {
        "base": {
            "label": "Base Case",
            "originator_price_reduction": 0.15,  # 15% price cut by originator
            "generic_uptake_speed": 1.0,  # Normal speed
            "market_growth_annual": 0.02,  # 2% annual market growth
            "originator_retention_months": 18,  # Months until erosion plateaus
            "originator_floor_share": 0.12,  # Minimum share originator keeps
            "num_generic_entrants": 6,
        },
        "bull_generic": {
            "label": "Bull Case (Generika)",
            "originator_price_reduction": 0.10,
            "generic_uptake_speed": 1.3,  # Faster adoption
            "market_growth_annual": 0.03,
            "originator_retention_months": 12,
            "originator_floor_share": 0.08,
            "num_generic_entrants": 6,
        },
        "bear_generic": {
            "label": "Bear Case (Generika)",
            "originator_price_reduction": 0.20,
            "generic_uptake_speed": 0.7,  # Slower adoption
            "market_growth_annual": 0.01,
            "originator_retention_months": 24,
            "originator_floor_share": 0.18,
            "num_generic_entrants": 4,
        },
    }

    return {
        "market": market,
        "products": products,
        "historical": historical_df,
        "generic_entrants": generic_entrants,
        "scenarios": scenarios,
    }


# Convenience constants
ELIQUIS_PRICE_PER_TRX = 91.50
ELIQUIS_PEAK_SHARE = 0.42
ELIQUIS_MONTHLY_TRX_DE = 4_200_000 * 0.42  # ~1.76M TRx/month
LOE_DATE = "2026-05-01"
