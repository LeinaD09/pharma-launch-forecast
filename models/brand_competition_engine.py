"""
Patient-based Forecast Engine for Brand-vs-Brand Competition.

Use Case: GLP-1 RA market – Mounjaro (Lilly) vs. Ozempic/Wegovy (Novo Nordisk)

Architecture:
  Per indication, per month:
    Eligible Patients
      × Treatment Rate (S-curve ramp)
      × My Share (S-curve ramp)
      × Persistence Factor (steady-state average)
      × Price/Month (indication-specific, with annual erosion)
      = Revenue per Indication

  Sum across indications → Total Revenue → Supply Constraint → Profitability

Key design decisions:
- Patient-based (not TRx-based): each indication has its own patient pool
- Per-indication revenue streams: T2D, Adipositas, CV-Risiko, MASH
- Persistence as steady-state multiplier: avg_persistence = (1 + persistence_12m) / 2
- Share normalization: my + competitor + rest = 100%, rest ≥ 10%
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# PARAMETER CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class IndicationParams:
    """Parameters for a single indication (e.g. T2D, Adipositas)."""
    name: str                               # "T2D", "Adipositas", "CV-Risiko", "MASH"
    enabled: bool = True
    eligible_patients: int = 0              # Total patient pool in Germany
    treated_pct_start: float = 0.0          # Current % treated with GLP-1
    treated_pct_peak: float = 0.0           # Target % treated at peak
    months_to_peak_treatment: int = 36      # S-curve ramp for treatment adoption
    my_share_start: float = 0.0             # My brand's current share in this indication
    my_share_peak: float = 0.0              # My brand's target peak share
    months_to_peak_share: int = 36          # S-curve ramp for share gain
    competitor_share_start: float = 0.0     # Main competitor's start share
    competitor_share_peak: float = 0.0      # Main competitor's target peak share
    competitor_months_to_peak: int = 36     # Competitor's share ramp speed
    price_per_month: float = 300.0          # Indication-specific price
    competitor_price_per_month: float = 300.0  # Competitor's price for this indication
    persistence_12m: float = 0.70           # % still on therapy after 12 months
    gkv_covered: bool = True                # Covered by statutory health insurance
    launch_delay_months: int = 0            # Months before indication available


@dataclass
class BrandParams:
    """Brand-level parameters (not indication-specific)."""
    name: str = "Mounjaro (Tirzepatid)"
    company: str = "Eli Lilly"

    # Indications (configured externally)
    indications: list = field(default_factory=list)

    # Supply constraints
    supply_constrained: bool = False
    supply_capacity_monthly_patients: int = 200_000
    supply_normalization_month: int = 0

    # Pricing dynamics (applied to all indications)
    price_trend_annual: float = -0.03       # -3% annual price erosion
    amnog_price_cut_month: int = 0
    amnog_price_cut_pct: float = 0.0

    # Costs
    cogs_pct: float = 0.20
    sga_monthly_eur: float = 800_000
    medical_affairs_monthly_eur: float = 200_000


@dataclass
class MarketParams:
    """Global market parameters."""
    forecast_start_year: int = 2026


# ═══════════════════════════════════════════════════════════════════════
# CURVE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _share_shift_curve(
    t: int,
    current: float,
    target: float,
    months_to_peak: int,
    speed: float = 1.0,
) -> float:
    """S-curve transition from current to target value."""
    if months_to_peak <= 0:
        return target
    midpoint = months_to_peak / 2
    steepness = 4.0 / months_to_peak * speed
    sigmoid = 1 / (1 + np.exp(-steepness * (t - midpoint)))
    val = current + (target - current) * sigmoid
    return float(np.clip(val, 0, 1))


def _apply_price_erosion(
    base_price: float,
    t: int,
    price_trend_annual: float,
    amnog_month: int = 0,
    amnog_cut_pct: float = 0.0,
) -> float:
    """Apply annual price erosion and AMNOG cut. Floor at EUR 100."""
    years_in = t / 12
    price = base_price * (1 + price_trend_annual) ** years_in
    if amnog_month > 0 and t >= amnog_month:
        price *= (1 - amnog_cut_pct)
    return max(price, 100.0)


# ═══════════════════════════════════════════════════════════════════════
# DEFAULT INDICATION CONFIGS
# ═══════════════════════════════════════════════════════════════════════

def default_lilly_indications() -> list[IndicationParams]:
    """Default Mounjaro (Lilly) indications for the Base Case."""
    return [
        IndicationParams(
            name="T2D",
            enabled=True,
            eligible_patients=6_330_000,
            treated_pct_start=0.139,
            treated_pct_peak=0.22,
            months_to_peak_treatment=36,
            my_share_start=0.08,
            my_share_peak=0.25,
            months_to_peak_share=36,
            competitor_share_start=0.36,
            competitor_share_peak=0.30,
            competitor_months_to_peak=36,
            price_per_month=350.0,
            competitor_price_per_month=300.0,
            persistence_12m=0.70,
            gkv_covered=True,
        ),
        IndicationParams(
            name="Adipositas",
            enabled=True,
            eligible_patients=8_000_000,
            treated_pct_start=0.006,       # ~50K / 8M
            treated_pct_peak=0.015,        # 1.5% without GKV
            months_to_peak_treatment=36,
            my_share_start=0.0,
            my_share_peak=0.35,
            months_to_peak_share=36,
            competitor_share_start=0.04,
            competitor_share_peak=0.15,
            competitor_months_to_peak=36,
            price_per_month=300.0,
            competitor_price_per_month=277.0,
            persistence_12m=0.45,
            gkv_covered=False,
        ),
        IndicationParams(
            name="CV-Risiko",
            enabled=False,
            eligible_patients=2_000_000,
            treated_pct_start=0.0,
            treated_pct_peak=0.05,
            months_to_peak_treatment=36,
            my_share_start=0.0,
            my_share_peak=0.20,
            months_to_peak_share=36,
            competitor_share_start=0.0,
            competitor_share_peak=0.15,
            competitor_months_to_peak=36,
            price_per_month=350.0,
            competitor_price_per_month=300.0,
            persistence_12m=0.65,
            gkv_covered=True,
            launch_delay_months=6,
        ),
        IndicationParams(
            name="MASH",
            enabled=False,
            eligible_patients=1_500_000,
            treated_pct_start=0.0,
            treated_pct_peak=0.03,
            months_to_peak_treatment=36,
            my_share_start=0.0,
            my_share_peak=0.25,
            months_to_peak_share=36,
            competitor_share_start=0.0,
            competitor_share_peak=0.10,
            competitor_months_to_peak=36,
            price_per_month=350.0,
            competitor_price_per_month=300.0,
            persistence_12m=0.60,
            gkv_covered=True,
            launch_delay_months=18,
        ),
    ]


def default_novo_indications() -> list[IndicationParams]:
    """Default Ozempic/Wegovy (Novo) indications for the Base Case."""
    return [
        IndicationParams(
            name="T2D",
            enabled=True,
            eligible_patients=6_330_000,
            treated_pct_start=0.139,
            treated_pct_peak=0.22,
            months_to_peak_treatment=36,
            my_share_start=0.36,
            my_share_peak=0.30,
            months_to_peak_share=36,
            competitor_share_start=0.08,
            competitor_share_peak=0.25,
            competitor_months_to_peak=36,
            price_per_month=300.0,
            competitor_price_per_month=350.0,
            persistence_12m=0.70,
            gkv_covered=True,
        ),
        IndicationParams(
            name="Adipositas",
            enabled=True,
            eligible_patients=8_000_000,
            treated_pct_start=0.006,
            treated_pct_peak=0.015,
            months_to_peak_treatment=36,
            my_share_start=0.04,
            my_share_peak=0.15,
            months_to_peak_share=36,
            competitor_share_start=0.0,
            competitor_share_peak=0.35,
            competitor_months_to_peak=36,
            price_per_month=277.0,
            competitor_price_per_month=300.0,
            persistence_12m=0.45,
            gkv_covered=False,
        ),
        IndicationParams(
            name="CV-Risiko",
            enabled=False,
            eligible_patients=2_000_000,
            treated_pct_start=0.0,
            treated_pct_peak=0.05,
            months_to_peak_treatment=36,
            my_share_start=0.0,
            my_share_peak=0.15,
            months_to_peak_share=36,
            competitor_share_start=0.0,
            competitor_share_peak=0.20,
            competitor_months_to_peak=36,
            price_per_month=300.0,
            competitor_price_per_month=350.0,
            persistence_12m=0.65,
            gkv_covered=True,
            launch_delay_months=6,
        ),
        IndicationParams(
            name="MASH",
            enabled=False,
            eligible_patients=1_500_000,
            treated_pct_start=0.0,
            treated_pct_peak=0.03,
            months_to_peak_treatment=36,
            my_share_start=0.0,
            my_share_peak=0.10,
            months_to_peak_share=36,
            competitor_share_start=0.0,
            competitor_share_peak=0.25,
            competitor_months_to_peak=36,
            price_per_month=300.0,
            competitor_price_per_month=350.0,
            persistence_12m=0.60,
            gkv_covered=True,
            launch_delay_months=18,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════
# MAIN FORECAST FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def forecast_brand(
    brand: BrandParams,
    market: MarketParams = None,
    forecast_months: int = 60,
    start_date: str = "2026-01-01",
) -> pd.DataFrame:
    """
    Generate monthly patient-based forecast across all indications.

    Per indication, per month:
      patients = eligible × treatment_rate × my_share × persistence
      revenue  = patients × price/month (with erosion)

    Supply constraint applied to total across indications.
    """
    if market is None:
        market = MarketParams()

    start = pd.Timestamp(start_date)
    dates = pd.date_range(start, periods=forecast_months, freq="MS")

    rows = []
    cumulative_revenue = 0.0
    cumulative_profit = 0.0

    for i, date in enumerate(dates):
        t = i

        # Per-indication accumulation
        total_my_patients = 0.0
        total_my_revenue = 0.0
        total_comp_patients = 0.0
        total_comp_revenue = 0.0
        ind_details = {}

        for ind in brand.indications:
            if not ind.enabled or t < ind.launch_delay_months:
                ind_details[ind.name] = {
                    "patients": 0, "revenue": 0.0, "treated": 0,
                    "my_share": 0.0, "comp_share": 0.0,
                    "treatment_rate": 0.0, "comp_patients": 0, "comp_revenue": 0.0,
                }
                continue

            t_eff = t - ind.launch_delay_months

            # 1. Treatment rate ramp (S-curve)
            treatment_rate = _share_shift_curve(
                t_eff, ind.treated_pct_start,
                ind.treated_pct_peak, ind.months_to_peak_treatment,
            )

            # 2. Treated patients in this indication
            treated = ind.eligible_patients * treatment_rate

            # 3. My share ramp (S-curve)
            my_share = _share_shift_curve(
                t_eff, ind.my_share_start,
                ind.my_share_peak, ind.months_to_peak_share,
            )

            # 4. Competitor share ramp
            comp_share = _share_shift_curve(
                t_eff, ind.competitor_share_start,
                ind.competitor_share_peak, ind.competitor_months_to_peak,
            )

            # 5. Normalize shares: my + comp + rest = 1.0, rest >= 10%
            raw_sum = my_share + comp_share
            if raw_sum > 0.90:
                scale = 0.90 / raw_sum
                my_share *= scale
                comp_share *= scale

            # 6. My patients (raw)
            my_patients_raw = treated * my_share

            # 7. Persistence: steady-state average
            avg_persistence = (1.0 + ind.persistence_12m) / 2
            my_patients = my_patients_raw * avg_persistence

            # 8. Competitor patients (same persistence assumed)
            comp_patients = treated * comp_share * avg_persistence

            # 9. Price with erosion (indication-specific base price)
            my_price = _apply_price_erosion(
                ind.price_per_month, t,
                brand.price_trend_annual,
                brand.amnog_price_cut_month,
                brand.amnog_price_cut_pct,
            )
            comp_price = _apply_price_erosion(
                ind.competitor_price_per_month, t,
                brand.price_trend_annual,  # same erosion rate
            )

            # 10. Revenue
            my_rev = my_patients * my_price
            comp_rev = comp_patients * comp_price

            total_my_patients += my_patients
            total_my_revenue += my_rev
            total_comp_patients += comp_patients
            total_comp_revenue += comp_rev

            ind_details[ind.name] = {
                "patients": round(my_patients),
                "revenue": round(my_rev, 2),
                "treated": round(treated),
                "my_share": round(my_share, 4),
                "comp_share": round(comp_share, 4),
                "treatment_rate": round(treatment_rate, 4),
                "comp_patients": round(comp_patients),
                "comp_revenue": round(comp_rev, 2),
                "price": round(my_price, 2),
            }

        # Supply constraint on total patients
        demand_patients = round(total_my_patients)
        if brand.supply_constrained and t < brand.supply_normalization_month:
            actual_patients = min(demand_patients, brand.supply_capacity_monthly_patients)
        else:
            actual_patients = demand_patients
        supply_gap = demand_patients - actual_patients

        # If supply-constrained, scale revenue proportionally
        if demand_patients > 0 and actual_patients < demand_patients:
            supply_ratio = actual_patients / demand_patients
            total_my_revenue *= supply_ratio

        # Profitability
        revenue = round(total_my_revenue, 2)
        cogs = revenue * brand.cogs_pct
        gross_profit = revenue - cogs
        operating_profit = gross_profit - brand.sga_monthly_eur - brand.medical_affairs_monthly_eur

        cumulative_revenue += revenue
        cumulative_profit += operating_profit

        # Weighted average share (across indications, by patients)
        total_treated = sum(d["treated"] for d in ind_details.values())
        if total_treated > 0:
            weighted_my_share = sum(
                d["my_share"] * d["treated"] for d in ind_details.values()
            ) / total_treated
            weighted_comp_share = sum(
                d["comp_share"] * d["treated"] for d in ind_details.values()
            ) / total_treated
        else:
            weighted_my_share = 0.0
            weighted_comp_share = 0.0

        row = {
            "date": date,
            "month": date.strftime("%Y-%m"),
            "months_from_start": t,
            # Totals
            "my_patients": actual_patients,
            "my_patients_demand": demand_patients,
            "supply_gap": supply_gap,
            "my_revenue": revenue,
            "my_cogs": round(cogs, 2),
            "my_gross_profit": round(gross_profit, 2),
            "my_operating_profit": round(operating_profit, 2),
            "cumulative_revenue": round(cumulative_revenue, 2),
            "cumulative_profit": round(cumulative_profit, 2),
            # Competitor totals
            "comp_patients": round(total_comp_patients),
            "comp_revenue": round(total_comp_revenue, 2),
            # Weighted shares
            "my_share_weighted": round(weighted_my_share, 4),
            "comp_share_weighted": round(weighted_comp_share, 4),
        }

        # Per-indication columns
        for ind in brand.indications:
            d = ind_details.get(ind.name, {})
            key = ind.name.lower().replace("-", "").replace("/", "").replace(" ", "_")
            row[f"patients_{key}"] = d.get("patients", 0)
            row[f"revenue_{key}"] = d.get("revenue", 0.0)
            row[f"share_{key}"] = d.get("my_share", 0.0)
            row[f"comp_patients_{key}"] = d.get("comp_patients", 0)
            row[f"treated_{key}"] = d.get("treated", 0)
            row[f"treatment_rate_{key}"] = d.get("treatment_rate", 0.0)

        rows.append(row)

    return pd.DataFrame(rows)


def calculate_kpis_brand(df: pd.DataFrame, brand: BrandParams = None) -> dict:
    """Calculate summary KPIs for brand forecast."""
    if len(df) == 0:
        return {}

    year1 = df.head(12)

    # Time to #1
    leading = df[df["my_share_weighted"] > df["comp_share_weighted"]]
    overtake_month = int(leading.iloc[0]["months_from_start"]) if len(leading) > 0 else None

    # Peak patients
    peak_patients = int(df["my_patients"].max())

    # Per-indication breakdown
    patients_by_ind = {}
    revenue_by_ind = {}
    for col in df.columns:
        if col.startswith("patients_") and col != "patients_demand":
            ind_key = col.replace("patients_", "")
            patients_by_ind[ind_key] = int(df[col].max())
        if col.startswith("revenue_"):
            ind_key = col.replace("revenue_", "")
            revenue_by_ind[ind_key] = round(df[col].sum(), 2)

    return {
        "year1_revenue": round(year1["my_revenue"].sum(), 2),
        "year1_profit": round(year1["my_operating_profit"].sum(), 2),
        "total_5y_revenue": round(df["my_revenue"].sum(), 2),
        "total_5y_profit": round(df["my_operating_profit"].sum(), 2),
        "peak_monthly_revenue": round(df["my_revenue"].max(), 2),
        "peak_share": round(df["my_share_weighted"].max(), 4),
        "peak_patients": peak_patients,
        "share_month_12": round(df.iloc[11]["my_share_weighted"], 4) if len(df) > 11 else None,
        "share_month_36": round(df.iloc[35]["my_share_weighted"], 4) if len(df) > 35 else None,
        "share_month_60": round(df.iloc[-1]["my_share_weighted"], 4),
        "cumulative_revenue": round(df["cumulative_revenue"].iloc[-1], 2),
        "cumulative_profit": round(df["cumulative_profit"].iloc[-1], 2),
        "overtake_month": overtake_month,
        "avg_price": round(df["my_revenue"].sum() / max(df["my_patients"].sum(), 1), 2),
        "patients_by_indication": patients_by_ind,
        "revenue_by_indication": revenue_by_ind,
    }
