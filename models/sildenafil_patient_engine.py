"""
Sildenafil Rx-to-OTC Switch – Patient-Based Forecast Engine
=============================================================
Best-practice patient-flow model.  Every volume number is derived
from a transparent patient funnel:

    Epidemiology (prevalence)
      → Treatment funnel (diagnosed, treated, untreated)
      → OTC addressable pool (stigma barrier reduction)
      → Patient uptake (logistic ramp to steady-state)
      → Tablets = patients × tablets_per_patient_per_month
      → Revenue = tablets × price

Key differences vs. volume-based engine (sildenafil_otc_engine.py):
  - OTC peak is COMPUTED from epidemiology, not a direct input
  - Treatment gap metric is derived from actual OTC patient volumes
  - Unused parameters (trial_rate, repeat_rate, addressable_otc_pct)
    are now active parts of the model
  - All patient counts are explicit and traceable

Reference: UK Viagra Connect (launched March 2018)
  - 63% new-to-therapy patients (Lee et al. 2021)
  - ~300K patients in Year 1
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd


# ===================================================================
# CHANNEL DEFINITIONS
# ===================================================================

@dataclass
class ChannelParams:
    """Parameters for a single distribution channel."""
    name: str = "Stationaere Apotheke"
    share_of_otc: float = 0.55
    share_trend_annual: float = -0.02
    margin_pct: float = 0.42
    distribution_cost_pct: float = 0.06
    discretion_factor: float = 0.8


# ===================================================================
# MAIN MODEL PARAMETERS
# ===================================================================

@dataclass
class SildenafilPatientParams:
    """Patient-based parameters for Sildenafil Rx-to-OTC switch.

    The model flows:  patients → tablets → revenue
    All volumes in TABLETS (1 tablet = 1 application = 50mg).
    """

    # --- Product ------------------------------------------------
    product_name: str = "Viagra Connect 50mg"
    company: str = "Viatris"
    molecule: str = "Sildenafil"
    switch_year: int = 2027

    # --- Epidemiology (Patient Pool) ----------------------------
    ed_prevalence_men: int = 5_000_000      # men with moderate-to-complete ED (DE)
    treatment_rate: float = 0.30            # currently in medical treatment (30%)
    # → treated = 1,500,000 | untreated = 3,500,000

    # --- Patient Funnel -----------------------------------------
    # What % of the untreated pool is addressable via OTC?
    # Not everyone will buy: some have contraindications, some won't
    # self-select, some prefer doctor relationship.
    addressable_pct: float = 0.15           # 15% of untreated would buy OTC at steady state
    # → addressable pool = 3,500,000 × 15% = 525,000 patients

    # How fast does the addressable pool get activated?
    uptake_ramp_months: int = 18            # logistic ramp to reach ~95% of addressable
    # Note: this is equivalent to the old otc_ramp_months

    # --- Patient Behavior ---------------------------------------
    tablets_per_patient_per_month: float = 4.0   # avg. usage frequency
    # → peak OTC tablets = 525,000 × 4 = 2,100,000 /month

    # --- Patient Source Mix -------------------------------------
    new_patient_share: float = 0.63         # UK reference: 63% new-to-therapy
    # remainder = Rx migration (patients switching from Rx to OTC)

    # --- Rx channel (pre-switch) --------------------------------
    rx_patients_monthly: int = 217_000      # patients receiving Rx sildenafil/month
    rx_tablets_per_patient: float = 4.0     # → 217K × 4 = 868K tablets/month
    rx_price_brand: float = 11.19           # Viagra brand per tablet
    rx_price_generic: float = 1.50          # generic per tablet
    rx_brand_share: float = 0.10            # Viagra brand % of Rx volume
    rx_decline_rate: float = 0.08           # Rx decline from OTC cannibalization
    rx_decline_months: int = 36

    # --- OTC pricing --------------------------------------------
    otc_price_per_tablet: float = 5.99
    price_elasticity: float = -0.5
    price_trend_annual: float = -0.03

    # --- Tadalafil migration -----------------------------------
    tadalafil_patients_monthly: int = 120_000  # Tadalafil Rx patients/month
    tadalafil_tablets_per_patient: float = 4.0  # → 480K tablets
    tadalafil_switch_pct: float = 0.12         # 12% switch to sildenafil OTC
    tadalafil_migration_months: int = 24

    # --- Brand vs. Generic OTC ---------------------------------
    brand_otc_share: float = 0.25
    brand_otc_share_trend: float = -0.03
    brand_price_premium: float = 1.8

    # --- Omnichannel distribution ------------------------------
    channels: list = field(default_factory=lambda: [
        ChannelParams(
            name="Stationaere Apotheke",
            share_of_otc=0.55,
            share_trend_annual=-0.02,
            margin_pct=0.42,
            distribution_cost_pct=0.06,
            discretion_factor=0.70,
        ),
        ChannelParams(
            name="Online-Apotheke",
            share_of_otc=0.45,
            share_trend_annual=0.02,
            margin_pct=0.30,
            distribution_cost_pct=0.10,
            discretion_factor=1.0,
        ),
    ])

    # --- Seasonality -------------------------------------------
    seasonality: list = field(default_factory=lambda: [
        0.90, 1.05, 1.00, 1.00, 1.05, 1.10,
        1.05, 1.00, 0.95, 0.95, 0.95, 1.00,
    ])

    # --- Marketing (cost only) ---------------------------------
    marketing_monthly_eur: float = 500_000
    marketing_maintenance_factor: float = 0.5
    marketing_ramp_months: int = 18

    # --- Costs -------------------------------------------------
    cogs_pct: float = 0.12

    # --- Forecast ----------------------------------------------
    forecast_months: int = 60


# ===================================================================
# MATHEMATICAL PRIMITIVES
# ===================================================================

def _logistic(t: float, peak: float, midpoint: float, steepness: float) -> float:
    """Generic logistic S-curve."""
    x = -steepness * (t - midpoint)
    x = np.clip(x, -500, 500)
    return peak / (1.0 + np.exp(x))


def _patient_uptake(month: int, addressable_patients: int, ramp_months: int) -> float:
    """Logistic ramp for patient uptake (returns active OTC patients)."""
    if ramp_months <= 0:
        return float(addressable_patients)
    midpoint = ramp_months * 0.45
    steepness = 6.0 / ramp_months
    x = -steepness * (month - midpoint)
    x = np.clip(x, -500, 500)
    return addressable_patients / (1.0 + np.exp(x))


def _rx_effect(month: int, initial: float, decline_rate: float, decline_months: int) -> float:
    """Rx volume with slow exponential decline."""
    if decline_months <= 0 or decline_rate <= 0:
        return float(initial)
    decline_rate = min(decline_rate, 0.99)
    floor = initial * (1.0 - decline_rate)
    k = np.log(20.0) / decline_months
    return floor + (initial - floor) * np.exp(-k * month)


def _channel_share(base_share: float, trend: float, month: int) -> float:
    """Channel share evolution over time."""
    return max(0.0, min(1.0, base_share + trend * (month / 12.0)))


# ===================================================================
# FORECAST ENGINE
# ===================================================================

def forecast_sildenafil_patient(
    params: SildenafilPatientParams,
    forecast_months: Optional[int] = None,
) -> pd.DataFrame:
    """Run the patient-based Sildenafil Rx-to-OTC forecast.

    Flow:  Epidemiology → Patients → Tablets → Revenue

    Returns DataFrame with monthly data including patient counts,
    tablet volumes, channel splits, and profitability.
    """
    months = forecast_months or params.forecast_months

    # --- Derive key quantities from patient pool ----------------
    untreated = params.ed_prevalence_men * (1 - params.treatment_rate)
    addressable_patients = int(untreated * params.addressable_pct)
    # Peak OTC tablets (computed, not input!)
    otc_peak_tablets = addressable_patients * params.tablets_per_patient_per_month

    # Rx baseline in tablets
    rx_tablets_baseline = params.rx_patients_monthly * params.rx_tablets_per_patient

    # Tadalafil migration in tablets
    tada_peak_tablets = (params.tadalafil_patients_monthly
                         * params.tadalafil_tablets_per_patient
                         * params.tadalafil_switch_pct)

    rows = []
    cum = {
        "otc_revenue": 0.0, "rx_revenue": 0.0, "total_revenue": 0.0,
        "profit": 0.0, "marketing": 0.0,
    }

    for m in range(1, months + 1):
        year_frac = m / 12.0
        season_idx = (m - 1) % 12
        season_factor = params.seasonality[season_idx]

        # ============================================================
        # STEP 1: PATIENT COUNTS
        # ============================================================

        # Active OTC patients (from untreated pool, logistic ramp)
        otc_patients_active = _patient_uptake(
            m, addressable_patients, params.uptake_ramp_months
        )

        # Tadalafil migration patients
        tada_migration_patients = _logistic(
            m,
            params.tadalafil_patients_monthly * params.tadalafil_switch_pct,
            params.tadalafil_migration_months * 0.5,
            6.0 / params.tadalafil_migration_months,
        )

        # Split active OTC patients by source
        otc_new_patients = otc_patients_active * params.new_patient_share
        otc_rxmigration_patients = otc_patients_active * (1 - params.new_patient_share)

        # Rx patients (declining)
        rx_patients = _rx_effect(
            m, params.rx_patients_monthly,
            params.rx_decline_rate, params.rx_decline_months,
        )

        # Total patients in treatment
        total_patients = rx_patients + otc_patients_active + tada_migration_patients

        # ============================================================
        # STEP 2: TABLETS (patients × usage frequency)
        # ============================================================

        # OTC tablets from patient pool
        otc_base_tablets = otc_patients_active * params.tablets_per_patient_per_month
        otc_seasonal = otc_base_tablets * season_factor

        # Price-volume effect
        price_change = (1 + params.price_trend_annual) ** year_frac - 1.0
        price_vol_effect = 1.0 + (price_change * params.price_elasticity)
        otc_total_tablets = max(0, otc_seasonal * price_vol_effect)

        # Tadalafil migration tablets
        tada_tablets = tada_migration_patients * params.tadalafil_tablets_per_patient
        otc_total_tablets += tada_tablets

        # Rx tablets
        rx_tablets = rx_patients * params.rx_tablets_per_patient * season_factor

        # Volume decomposition (in tablets)
        otc_total_tablets_adj = round(otc_total_tablets)
        otc_from_tadalafil = round(min(tada_tablets, otc_total_tablets_adj))
        otc_excl_tada = otc_total_tablets_adj - otc_from_tadalafil
        otc_from_new_patients = round(otc_excl_tada * params.new_patient_share)
        otc_from_rx_migration = otc_excl_tada - otc_from_new_patients

        total_tablets = rx_tablets + otc_total_tablets_adj

        # ============================================================
        # STEP 3: CHANNEL DISTRIBUTION
        # ============================================================

        raw_shares = []
        for ch in params.channels:
            raw_shares.append(_channel_share(ch.share_of_otc, ch.share_trend_annual, m))
        share_sum = sum(raw_shares)
        norm_shares = [s / share_sum for s in raw_shares] if share_sum > 0 else raw_shares

        # Discretion bonus (shifts mix, not total)
        weighted_shares = []
        for i, ch in enumerate(params.channels):
            discretion_bonus = 1.0 + (ch.discretion_factor - 0.7) * 0.15
            weighted_shares.append(norm_shares[i] * discretion_bonus)
        ws_sum = sum(weighted_shares)
        disc_shares = [s / ws_sum for s in weighted_shares] if ws_sum > 0 else norm_shares

        # OTC price with erosion
        otc_price_now = params.otc_price_per_tablet * (
            1 + params.price_trend_annual
        ) ** year_frac

        channel_data = {}
        total_otc_manufacturer_revenue = 0.0
        total_otc_retail_revenue = 0.0

        for i, ch in enumerate(params.channels):
            ch_share = disc_shares[i]
            ch_tablets = otc_total_tablets_adj * ch_share
            ch_retail_rev = ch_tablets * otc_price_now
            mfr_share = 1.0 - ch.margin_pct - ch.distribution_cost_pct
            ch_mfr_rev = ch_retail_rev * mfr_share
            total_otc_retail_revenue += ch_retail_rev
            total_otc_manufacturer_revenue += ch_mfr_rev
            channel_data[ch.name] = {
                "tablets": round(ch_tablets),
                "share": ch_share,
                "retail_revenue": round(ch_retail_rev),
                "manufacturer_revenue": round(ch_mfr_rev),
            }

        # ============================================================
        # STEP 4: BRAND vs. GENERIC
        # ============================================================

        brand_share = max(0.10, params.brand_otc_share + params.brand_otc_share_trend * year_frac)
        otc_brand_tablets = round(otc_total_tablets_adj * brand_share)
        otc_generic_tablets = otc_total_tablets_adj - otc_brand_tablets

        generic_price = otc_price_now
        brand_price = otc_price_now * params.brand_price_premium
        brand_rev_bonus = otc_brand_tablets * (brand_price - generic_price)
        avg_mfr_pct = (total_otc_manufacturer_revenue / total_otc_retail_revenue
                       if total_otc_retail_revenue > 0 else 0.52)
        total_otc_manufacturer_revenue += brand_rev_bonus * avg_mfr_pct
        total_otc_retail_revenue += brand_rev_bonus

        # ============================================================
        # STEP 5: Rx REVENUE
        # ============================================================

        rx_avg_price = (
            params.rx_brand_share * params.rx_price_brand +
            (1 - params.rx_brand_share) * params.rx_price_generic
        )
        rx_revenue = rx_tablets * rx_avg_price

        # ============================================================
        # STEP 6: PROFITABILITY
        # ============================================================

        marketing_spend = params.marketing_monthly_eur
        if m > params.marketing_ramp_months:
            marketing_spend *= params.marketing_maintenance_factor

        total_revenue = rx_revenue + total_otc_manufacturer_revenue
        rx_cogs = rx_revenue * params.cogs_pct
        otc_cogs = total_otc_manufacturer_revenue * params.cogs_pct
        rx_gross_profit = rx_revenue - rx_cogs
        otc_gross_profit = total_otc_manufacturer_revenue - otc_cogs
        cogs = rx_cogs + otc_cogs
        gross_profit = total_revenue - cogs
        operating_profit = gross_profit - marketing_spend

        cum["otc_revenue"] += total_otc_manufacturer_revenue
        cum["rx_revenue"] += rx_revenue
        cum["total_revenue"] += total_revenue
        cum["profit"] += operating_profit
        cum["marketing"] += marketing_spend
        # ============================================================
        # STEP 7: TREATMENT GAP (derived from actual patients!)
        # ============================================================

        # newly_treated = active OTC patients who are new-to-therapy
        # (i.e. otc_new_patients this month, NOT cumulative tablets).
        # These are patients currently in treatment who were previously
        # untreated — they raise the effective treatment rate.
        active_new_patients = round(otc_new_patients)
        treatment_rate_new = min(1.0, params.treatment_rate + (
            active_new_patients / params.ed_prevalence_men
        ))

        rows.append({
            "month": m,
            "date": pd.Timestamp(params.switch_year, 1, 1) + pd.DateOffset(months=m - 1),

            # Patient counts
            "otc_patients_active": round(otc_patients_active),
            "otc_new_patients": round(otc_new_patients),
            "otc_rxmigration_patients": round(otc_rxmigration_patients),
            "tada_migration_patients": round(tada_migration_patients),
            "rx_patients": round(rx_patients),
            "total_patients": round(total_patients),

            # Rx
            "rx_tablets": round(rx_tablets),
            "rx_revenue": round(rx_revenue),

            # OTC total
            "otc_tablets": otc_total_tablets_adj,
            "otc_price_per_tablet": round(otc_price_now, 2),
            "otc_retail_revenue": round(total_otc_retail_revenue),
            "otc_manufacturer_revenue": round(total_otc_manufacturer_revenue),

            # OTC by channel
            "ch_apotheke_tablets": channel_data.get(params.channels[0].name, {}).get("tablets", 0) if len(params.channels) > 0 else 0,
            "ch_apotheke_revenue": channel_data.get(params.channels[0].name, {}).get("manufacturer_revenue", 0) if len(params.channels) > 0 else 0,
            "ch_apotheke_share": channel_data.get(params.channels[0].name, {}).get("share", 0) if len(params.channels) > 0 else 0,
            "ch_online_tablets": channel_data.get(params.channels[1].name, {}).get("tablets", 0) if len(params.channels) > 1 else 0,
            "ch_online_revenue": channel_data.get(params.channels[1].name, {}).get("manufacturer_revenue", 0) if len(params.channels) > 1 else 0,
            "ch_online_share": channel_data.get(params.channels[1].name, {}).get("share", 0) if len(params.channels) > 1 else 0,

            # Brand vs Generic
            "otc_brand_tablets": otc_brand_tablets,
            "otc_generic_tablets": otc_generic_tablets,
            "otc_brand_share": brand_share,

            # Volume decomposition (tablets)
            "otc_from_new_patients": otc_from_new_patients,
            "otc_from_rx_migration": otc_from_rx_migration,
            "otc_from_tadalafil": otc_from_tadalafil,

            # Combined
            "total_tablets": round(total_tablets),
            "total_revenue": round(total_revenue),
            "otc_share_tablets": otc_total_tablets_adj / total_tablets if total_tablets > 0 else 0,

            # Seasonality
            "season_factor": season_factor,

            # Profitability
            "rx_gross_profit": round(rx_gross_profit),
            "otc_gross_profit": round(otc_gross_profit),
            "cogs": round(cogs),
            "marketing_spend": round(marketing_spend),
            "gross_profit": round(gross_profit),
            "operating_profit": round(operating_profit),

            # Cumulative
            "cumulative_total_revenue": round(cum["total_revenue"]),
            "cumulative_otc_revenue": round(cum["otc_revenue"]),
            "cumulative_rx_revenue": round(cum["rx_revenue"]),
            "cumulative_profit": round(cum["profit"]),
            "cumulative_marketing": round(cum["marketing"]),

            # Treatment gap (derived from actual OTC patients)
            "treatment_rate_effective": treatment_rate_new,
            "active_new_patients": active_new_patients,

            # Derived metrics for display
            "otc_peak_tablets_computed": round(otc_peak_tablets),
            "addressable_patients": addressable_patients,
        })

    return pd.DataFrame(rows)


def calculate_kpis_patient(df: pd.DataFrame) -> dict:
    """Calculate KPIs from patient-based forecast."""
    last = df.iloc[-1]
    y1 = df[df["month"] <= 12]

    # Crossover month -- revenue
    crossover = df[df["otc_manufacturer_revenue"] > df["rx_revenue"]]
    crossover_month = int(crossover.iloc[0]["month"]) if len(crossover) > 0 else None

    # Crossover month -- tablets
    crossover_tabs = df[df["otc_tablets"] > df["rx_tablets"]]
    crossover_month_tablets = int(crossover_tabs.iloc[0]["month"]) if len(crossover_tabs) > 0 else None

    # Peak OTC
    peak_idx = df["otc_tablets"].idxmax()
    peak_otc_tablets = int(df.loc[peak_idx, "otc_tablets"])
    peak_otc_month = int(df.loc[peak_idx, "month"])

    # Peak patients
    peak_pat_idx = df["otc_patients_active"].idxmax()
    peak_otc_patients = int(df.loc[peak_pat_idx, "otc_patients_active"])

    # Rx decline
    rx_y1 = df[df["month"] <= 12]["rx_tablets"].sum()
    rx_last12 = df[df["month"] > (df["month"].max() - 12)]["rx_tablets"].sum()
    rx_decline_pct = (rx_y1 - rx_last12) / rx_y1 if rx_y1 > 0 else 0

    m12 = df[df["month"] == 12]
    m24 = df[df["month"] == 24]

    online_share_m12 = float(m12["ch_online_share"].iloc[0]) if len(m12) > 0 else 0
    online_share_m24 = float(m24["ch_online_share"].iloc[0]) if len(m24) > 0 else 0

    return {
        "year1_otc_revenue": y1["otc_manufacturer_revenue"].sum(),
        "year1_rx_revenue": y1["rx_revenue"].sum(),
        "year1_total_revenue": y1["total_revenue"].sum(),
        "total_5y_revenue": last["cumulative_total_revenue"],
        "total_5y_otc_revenue": last["cumulative_otc_revenue"],
        "total_5y_rx_revenue": last["cumulative_rx_revenue"],
        "total_5y_profit": last["cumulative_profit"],
        "total_5y_marketing": last["cumulative_marketing"],
        "crossover_month": crossover_month,
        "crossover_month_tablets": crossover_month_tablets,
        "peak_otc_tablets": peak_otc_tablets,
        "peak_otc_month": peak_otc_month,
        "peak_otc_patients": peak_otc_patients,
        "rx_decline_total": rx_decline_pct,
        "otc_share_m12": float(m12["otc_share_tablets"].iloc[0]) if len(m12) > 0 else 0,
        "otc_share_m24": float(m24["otc_share_tablets"].iloc[0]) if len(m24) > 0 else 0,
        "brand_share_m12": float(m12["otc_brand_share"].iloc[0]) if len(m12) > 0 else 0,
        "brand_share_m24": float(m24["otc_brand_share"].iloc[0]) if len(m24) > 0 else 0,
        "online_share_m12": online_share_m12,
        "online_share_m24": online_share_m24,
        "treatment_rate_final": last["treatment_rate_effective"],
        "newly_treated_total": int(df["active_new_patients"].max()),
        "addressable_patients": last["addressable_patients"],
        "otc_peak_computed": last["otc_peak_tablets_computed"],
    }
