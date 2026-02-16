"""
Eye Care Franchise – Specialty Ophthalmology Portfolio Launch Engine
====================================================================
Models sequential market entry of multiple specialty products into
the German ophthalmology market over a 7-year horizon.

What makes this model unique:
  - PORTFOLIO sequencing: 3 products launch at different times
  - AMNOG pricing simulation: free pricing → G-BA assessment → negotiated price
  - Facharzt adoption curve: S-curve diffusion across 6,600+ ophthalmologists
  - Field force scaling: Aussendienst + MSL build-up tied to launch sequence
  - Competitive dynamics: iKervis, Vevizye, OTC artificial tears
  - Cross-product synergies: shared field force, KOL relationships

Product Portfolio:
  P1: RYZUMVI (phentolamine) – Mydriasis reversal   [near-term, 2026]
  P2: MR-141 (phentolamine)  – Presbyopia            [mid-term, 2027]
  P3: Tyrvaya (varenicline)  – Dry Eye Disease        [long-term, 2029]

Market data (Germany):
  - 8,250+ ophthalmologists, 6,600 in GKV vertragsärztliche Versorgung
  - Dry eye: ~10M affected, 1.5-1.9M diagnosed, only 36% get Rx
  - Dry eye market DE: ~EUR 430M (Rx+OTC), CAGR 5.7%
  - iKervis (Santen): EUR 120-135/month, severe keratitis only
  - Vevizye (Novaliq/Thea): EU-approved Oct 2024, moderate-to-severe
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════
# PRODUCT DEFINITION
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProductParams:
    """Parameters for a single specialty ophthalmology product."""
    name: str = "Product"
    code: str = "P1"                       # short code for DataFrame columns
    indication: str = "Indication"
    launch_month: int = 1                  # month from model start (1 = month 1)

    # ─── Target population ──────────────────────────────────────
    eligible_patients: int = 100_000       # patients who could use this product
    market_growth_annual: float = 0.02     # annual growth of eligible population (e.g. 2%)
    current_treatment_rate: float = 0.50   # % currently treated (for this indication)
    addressable_pct: float = 0.30          # % of eligible we can realistically reach

    # ─── Adoption ───────────────────────────────────────────────
    peak_market_share: float = 0.15        # max share of treated patients
    adoption_speed: int = 24               # months to reach ~80% of peak share
    # Facharzt adoption: how many of 6,600 ophthalmologists prescribe
    peak_prescribers: int = 2_000          # prescribing ophthalmologists at peak
    prescriber_ramp_months: int = 18       # months to reach peak prescriber count

    # ─── Pricing (AMNOG lifecycle) ──────────────────────────────
    launch_price_monthly: float = 150.0    # EUR/month, free pricing phase
    amnog_month: int = 6                   # month when AMNOG assessment happens
    amnog_price_cut_pct: float = 0.20      # expected price reduction post-AMNOG
    amnog_benefit_rating: str = "gering"   # kein/gering/betraecht./erheblich
    # Post-AMNOG price evolution
    price_erosion_annual: float = -0.02    # annual price erosion after AMNOG

    # ─── Treatment pattern ──────────────────────────────────────
    doses_per_month: float = 30.0          # doses/month (e.g. daily eye drops)
    avg_treatment_months: float = 12.0     # average treatment duration
    compliance_rate: float = 0.70          # real-world compliance

    # ─── Costs ──────────────────────────────────────────────────
    cogs_pct: float = 0.15                 # COGS as % of net revenue
    royalty_pct: float = 0.05              # royalties/licensing fees

    # ─── Competitive pressure ───────────────────────────────────
    competitors: int = 2                   # number of direct competitors
    competitive_pressure_annual: float = -0.02  # annual share erosion from competition


@dataclass
class CompetitorProduct:
    """A competitor product in the market."""
    name: str = "Competitor"
    company: str = "Company"
    monthly_price: float = 130.0
    market_share: float = 0.10
    indication: str = "Indication"
    launch_year: int = 2015
    strength: str = "Established"           # qualitative assessment


# ═══════════════════════════════════════════════════════════════════
# FIELD FORCE & GO-TO-MARKET
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FieldForceParams:
    """Field force and go-to-market investment parameters."""
    # ─── Aussendienst (Sales Reps) ──────────────────────────────
    reps_at_launch: int = 15               # initial sales reps
    reps_peak: int = 45                    # peak sales reps
    reps_ramp_months: int = 18             # months to reach peak
    rep_annual_cost: float = 120_000       # EUR/year fully loaded
    rep_target_calls_month: int = 80       # calls per rep per month

    # ─── MSL (Medical Science Liaisons) ─────────────────────────
    msls_at_launch: int = 5
    msls_peak: int = 12
    msl_annual_cost: float = 150_000       # EUR/year fully loaded
    msl_ramp_months: int = 12

    # ─── Marketing & Medical ────────────────────────────────────
    launch_marketing_monthly: float = 400_000   # EUR/month during launch phase
    maintenance_marketing_monthly: float = 150_000  # EUR/month post-launch
    launch_phase_months: int = 12          # months of heavy launch investment
    congress_annual_budget: float = 200_000  # DOG, AAD etc.
    kol_program_annual: float = 150_000    # Advisory boards, speaker programs
    digital_marketing_monthly: float = 50_000  # Digital channels

    # ─── Synergy: shared infrastructure across products ─────────
    synergy_factor_p2: float = 0.70        # P2 launch costs = 70% of standalone
    synergy_factor_p3: float = 0.80        # P3 launch costs = 80% (less synergy: different segment)


# ═══════════════════════════════════════════════════════════════════
# MARKET CONTEXT
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MarketParams:
    """German ophthalmology market parameters."""
    total_ophthalmologists: int = 8_250
    gkv_ophthalmologists: int = 6_600

    # Dry eye market
    dry_eye_patients_diagnosed: int = 1_700_000
    dry_eye_rx_treatment_rate: float = 0.36
    dry_eye_market_total_eur: float = 430_000_000  # Rx + OTC
    dry_eye_rx_share: float = 0.35          # Rx % of total dry eye market
    dry_eye_growth_rate: float = 0.057      # CAGR 5.7%

    # OTC artificial tears
    otc_tears_market_eur: float = 280_000_000
    otc_tears_growth_rate: float = 0.04

    # Total ophthalmic Rx market
    ophthalmic_rx_market_eur: float = 1_200_000_000  # total Rx ophthalmology DE


# ═══════════════════════════════════════════════════════════════════
# DEFAULT PRODUCT CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════

def default_ryzumvi() -> ProductParams:
    """RYZUMVI – Mydriasis reversal (near-term)."""
    return ProductParams(
        name="RYZUMVI", code="ryzumvi",
        indication="Mydriase-Reversal (Pupillenerweiterung rueckgaengig)",
        launch_month=1,
        eligible_patients=800_000,     # dilated exams/year where reversal wanted
        current_treatment_rate=0.0,     # no product exists for this in DE
        addressable_pct=0.25,           # 25% of eligible exams
        peak_market_share=0.50,         # first-in-class, no competition
        adoption_speed=18,
        peak_prescribers=3_000,         # ophthalmologists doing exams
        prescriber_ramp_months=15,
        launch_price_monthly=25.0,      # per-use pricing, ~EUR 25 per treatment
        amnog_month=7,                  # AMNOG cut starts at absolute month 7; free pricing M1-M6
        amnog_price_cut_pct=0.10,       # unique product → mild cut
        amnog_benefit_rating="gering",
        price_erosion_annual=-0.01,
        doses_per_month=1.0,            # per-procedure, not chronic
        avg_treatment_months=1.0,       # one-time use per exam
        compliance_rate=1.0,            # administered by physician
        cogs_pct=0.20,
        royalty_pct=0.08,               # Ocuphire royalty
        market_growth_annual=0.02,      # ophthalmology procedures grow ~2% p.a.
        competitors=0,
        competitive_pressure_annual=0.0,
    )

def default_mr141() -> ProductParams:
    """MR-141 – Presbyopia (mid-term)."""
    return ProductParams(
        name="MR-141 (Presbyopie)", code="mr141",
        indication="Presbyopie (Altersweitsichtigkeit)",
        launch_month=18,               # ~1.5 years after P1
        eligible_patients=15_000_000,   # presbyopia prevalence 40+ in DE
        current_treatment_rate=0.0,     # no Rx treatment, only reading glasses
        addressable_pct=0.02,           # very conservative: 2% of presbyopes
        peak_market_share=0.40,         # limited competition initially
        adoption_speed=24,
        peak_prescribers=2_500,
        prescriber_ramp_months=18,
        launch_price_monthly=45.0,      # chronic daily use
        amnog_month=24,                 # 6 months after launch
        amnog_price_cut_pct=0.25,       # lifestyle-adjacent → harder negotiation
        amnog_benefit_rating="gering",
        price_erosion_annual=-0.03,
        doses_per_month=30.0,           # daily eye drop
        avg_treatment_months=24.0,      # chronic
        compliance_rate=0.60,           # lifestyle → lower compliance
        cogs_pct=0.15,
        royalty_pct=0.05,
        market_growth_annual=0.03,      # presbyopia prevalence growing ~3% (aging population)
        competitors=1,                  # Vuity (AbbVie) or similar
        competitive_pressure_annual=-0.03,
    )

def default_tyrvaya() -> ProductParams:
    """Tyrvaya – Dry Eye Disease (long-term, requires EMA filing)."""
    return ProductParams(
        name="Tyrvaya (Trockenes Auge)", code="tyrvaya",
        indication="Trockenes Auge (Keratoconjunctivitis sicca)",
        launch_month=42,               # ~3.5 years from start (EMA + AMNOG)
        eligible_patients=1_700_000,    # diagnosed DED patients in DE
        current_treatment_rate=0.36,
        addressable_pct=0.12,           # moderate-severe, Rx-eligible
        peak_market_share=0.20,         # competitive: iKervis, Vevizye
        adoption_speed=30,
        peak_prescribers=3_500,         # DED is high-volume
        prescriber_ramp_months=24,
        launch_price_monthly=140.0,     # benchmark: iKervis EUR 120-135
        amnog_month=48,                 # 6 months after launch
        amnog_price_cut_pct=0.15,       # novel MOA → moderate cut
        amnog_benefit_rating="gering",
        price_erosion_annual=-0.02,
        doses_per_month=60.0,           # BID nasal spray
        avg_treatment_months=18.0,      # chronic but some discontinuation
        compliance_rate=0.65,
        cogs_pct=0.18,
        royalty_pct=0.0,                # fully owned (Oyster Point)
        market_growth_annual=0.057,     # dry eye market CAGR 5.7%
        competitors=3,                  # iKervis, Vevizye, generics
        competitive_pressure_annual=-0.03,
    )


# ═══════════════════════════════════════════════════════════════════
# MATHEMATICAL PRIMITIVES
# ═══════════════════════════════════════════════════════════════════

def _logistic_ramp(month: int, launch_month: int, peak: float,
                   speed_months: int) -> float:
    """S-curve adoption from launch month."""
    t = month - launch_month
    if t < 0:
        return 0.0
    if speed_months <= 0:
        return peak
    midpoint = speed_months * 0.45
    steepness = 6.0 / speed_months
    return peak / (1.0 + np.exp(-steepness * (t - midpoint)))


def _amnog_price(month: int, launch_month: int, launch_price: float,
                 amnog_month: int, cut_pct: float,
                 erosion_annual: float) -> float:
    """Price evolution through AMNOG lifecycle."""
    t = month - launch_month
    if t < 0:
        return 0.0
    # Phase 1: Free pricing (first 6 months post-launch)
    amnog_t = amnog_month - launch_month
    if t < amnog_t:
        return launch_price
    # Phase 2: Post-AMNOG negotiated price
    post_amnog_months = t - amnog_t
    negotiated_price = launch_price * (1 - cut_pct)
    # Phase 3: Gradual erosion
    years_post = post_amnog_months / 12.0
    return negotiated_price * (1 + erosion_annual) ** years_post


def _field_force_cost(month: int, ff: FieldForceParams,
                      products_launched: int,
                      launch_months: Optional[List[int]] = None) -> dict:
    """Calculate field force costs for a given month.

    Each product launch triggers its own heavy-marketing phase
    (launch_phase_months long). Synergy discounts apply to P2/P3.
    Outside any active launch window → maintenance marketing.
    """
    # Reps ramp
    if ff.reps_ramp_months > 0:
        rep_progress = min(1.0, month / ff.reps_ramp_months)
    else:
        rep_progress = 1.0
    reps = ff.reps_at_launch + (ff.reps_peak - ff.reps_at_launch) * rep_progress
    rep_cost_monthly = reps * ff.rep_annual_cost / 12

    # MSL ramp
    if ff.msl_ramp_months > 0:
        msl_progress = min(1.0, month / ff.msl_ramp_months)
    else:
        msl_progress = 1.0
    msls = ff.msls_at_launch + (ff.msls_peak - ff.msls_at_launch) * msl_progress
    msl_cost_monthly = msls * ff.msl_annual_cost / 12

    # Marketing: each launch gets its own heavy-phase window
    # Check if we are within any product's launch window
    in_launch_phase = False
    active_launch_idx = 0  # which product's launch phase we're in (0-based)
    if launch_months:
        for idx, lm in enumerate(launch_months):
            if lm <= month < lm + ff.launch_phase_months:
                in_launch_phase = True
                active_launch_idx = idx
                break

    if in_launch_phase:
        # Synergy: P1 = 100%, P2 = synergy_factor_p2, P3+ = synergy_factor_p3
        if active_launch_idx == 0:
            synergy = 1.0
        elif active_launch_idx == 1:
            synergy = ff.synergy_factor_p2
        else:
            synergy = ff.synergy_factor_p3
        marketing = ff.launch_marketing_monthly * synergy
    else:
        # Outside any launch window → maintenance
        if products_launched > 0:
            marketing = ff.maintenance_marketing_monthly
        else:
            marketing = 0

    # Congress & KOL (annual, spread monthly)
    congress_monthly = ff.congress_annual_budget / 12
    kol_monthly = ff.kol_program_annual / 12
    digital = ff.digital_marketing_monthly

    total = rep_cost_monthly + msl_cost_monthly + marketing + congress_monthly + kol_monthly + digital

    return {
        "reps": round(reps),
        "msls": round(msls),
        "rep_cost": round(rep_cost_monthly),
        "msl_cost": round(msl_cost_monthly),
        "marketing": round(marketing),
        "congress_kol": round(congress_monthly + kol_monthly),
        "digital": round(digital),
        "total_gtm_cost": round(total),
    }


# ═══════════════════════════════════════════════════════════════════
# FORECAST ENGINE
# ═══════════════════════════════════════════════════════════════════

def forecast_ophthalmology(
    products: Optional[List[ProductParams]] = None,
    field_force: Optional[FieldForceParams] = None,
    market: Optional[MarketParams] = None,
    forecast_months: int = 84,  # 7 years
) -> pd.DataFrame:
    """Run the specialty ophthalmology portfolio launch forecast.

    Returns DataFrame with monthly data for each product and portfolio totals.
    """
    if products is None:
        products = [default_ryzumvi(), default_mr141(), default_tyrvaya()]
    if field_force is None:
        field_force = FieldForceParams()
    if market is None:
        market = MarketParams()

    rows = []
    cum = {"revenue": 0.0, "profit": 0.0, "gtm_cost": 0.0}

    # Sorted launch months for GTM cost calculation
    launch_months_sorted = sorted(p.launch_month for p in products)

    for m in range(1, forecast_months + 1):
        row_data = {"month": m}

        # Count how many products have launched by this month
        products_launched = sum(1 for p in products if m >= p.launch_month)

        # ─── Field Force & GTM costs ────────────────────────────
        if products_launched > 0:
            ff_data = _field_force_cost(m, field_force, products_launched,
                                        launch_months_sorted)
        else:
            ff_data = {k: 0 for k in ["reps", "msls", "rep_cost", "msl_cost",
                                       "marketing", "congress_kol", "digital", "total_gtm_cost"]}

        row_data.update({f"ff_{k}": v for k, v in ff_data.items()})

        # ─── Per-product metrics ────────────────────────────────
        total_revenue = 0.0
        total_patients = 0
        total_prescribers = 0

        for p in products:
            prefix = p.code

            if m < p.launch_month:
                # Product not yet launched
                for suffix in ["patients", "prescribers", "price", "revenue",
                               "gross_revenue", "net_revenue", "share", "launched"]:
                    row_data[f"{prefix}_{suffix}"] = 0
                continue

            row_data[f"{prefix}_launched"] = 1

            # Market share (S-curve + competitive erosion)
            base_share = _logistic_ramp(
                m, p.launch_month, p.peak_market_share, p.adoption_speed
            )
            years_since_launch = (m - p.launch_month) / 12.0
            competitive_erosion = max(0, 1.0 + p.competitive_pressure_annual * years_since_launch)
            effective_share = base_share * competitive_erosion
            row_data[f"{prefix}_share"] = effective_share

            # Prescriber count derived from market share
            # Share ramp progress (0→1) drives prescriber ramp to peak_prescribers.
            # Changing peak_market_share scales the absolute number of prescribers too:
            #   default peak_share → peak_prescribers; different peak_share → proportional.
            # We use the raw S-curve progress (base_share / peak_market_share) for shape,
            # then scale peak_prescribers by (peak_market_share / default_peak_share).
            # This way: higher peak share → more adopting doctors.
            default_peak_shares = {"ryzumvi": 0.50, "mr141": 0.40, "tyrvaya": 0.20}
            default_ps = default_peak_shares.get(p.code, 0.20)
            share_ratio = p.peak_market_share / default_ps if default_ps > 0 else 1.0
            if p.peak_market_share > 0:
                ramp_progress = base_share / p.peak_market_share  # 0→1 as S-curve fills
            else:
                ramp_progress = 0.0
            prescribers = ramp_progress * competitive_erosion * p.peak_prescribers * share_ratio
            row_data[f"{prefix}_prescribers"] = round(prescribers)
            total_prescribers += round(prescribers)

            # Patient volume (eligible population grows annually)
            years_into_model = (m - 1) / 12.0
            eligible_now = p.eligible_patients * (1.0 + p.market_growth_annual) ** years_into_model
            treatable = eligible_now * p.addressable_pct
            if p.current_treatment_rate > 0:
                # Some patients already treated → compete for them
                treated_pool = eligible_now * p.current_treatment_rate * p.addressable_pct
            else:
                treated_pool = treatable
            patients = treated_pool * effective_share * p.compliance_rate
            row_data[f"{prefix}_patients"] = round(patients)
            total_patients += round(patients)

            # Pricing (AMNOG lifecycle)
            price = _amnog_price(
                m, p.launch_month, p.launch_price_monthly,
                p.amnog_month, p.amnog_price_cut_pct, p.price_erosion_annual
            )
            row_data[f"{prefix}_price"] = round(price, 2)

            # Revenue
            gross_revenue = patients * price
            net_revenue = gross_revenue * (1 - p.cogs_pct - p.royalty_pct)
            row_data[f"{prefix}_gross_revenue"] = round(gross_revenue)
            row_data[f"{prefix}_net_revenue"] = round(net_revenue)
            row_data[f"{prefix}_revenue"] = round(gross_revenue)
            total_revenue += gross_revenue

        # ─── Portfolio totals ───────────────────────────────────
        gtm_cost = ff_data["total_gtm_cost"]
        total_net_revenue = sum(
            row_data.get(f"{p.code}_net_revenue", 0) for p in products
        )
        portfolio_profit = total_net_revenue - gtm_cost

        row_data["total_revenue"] = round(total_revenue)
        row_data["total_patients"] = total_patients
        row_data["total_prescribers"] = total_prescribers
        row_data["total_gtm_cost"] = gtm_cost
        row_data["portfolio_profit"] = round(portfolio_profit)
        row_data["products_launched"] = products_launched

        cum["revenue"] += total_revenue
        cum["profit"] += portfolio_profit
        cum["gtm_cost"] += gtm_cost

        row_data["cumulative_revenue"] = round(cum["revenue"])
        row_data["cumulative_profit"] = round(cum["profit"])
        row_data["cumulative_gtm_cost"] = round(cum["gtm_cost"])

        # MVZ share: growing channel (base ~34% of GKV ophthalmologists, +8% p.a.)
        years_into_model = (m - 1) / 12.0
        mvz_base = 2_250 / market.gkv_ophthalmologists  # ~34%
        row_data["mvz_share"] = min(mvz_base * (1.08 ** years_into_model), 0.70)

        # ROI
        row_data["roi"] = cum["profit"] / cum["gtm_cost"] if cum["gtm_cost"] > 0 else 0

        rows.append(row_data)

    return pd.DataFrame(rows)


def calculate_kpis_ophthalmology(df: pd.DataFrame,
                                  products: Optional[List[ProductParams]] = None) -> dict:
    """Calculate portfolio KPIs."""
    if products is None:
        products = [default_ryzumvi(), default_mr141(), default_tyrvaya()]

    last = df.iloc[-1]
    y1 = df[df["month"] <= 12]
    y3 = df[df["month"] <= 36]

    kpis = {
        "total_7y_revenue": last["cumulative_revenue"],
        "total_7y_profit": last["cumulative_profit"],
        "total_7y_gtm_cost": last["cumulative_gtm_cost"],
        "final_roi": last["roi"],
        "peak_monthly_revenue": df["total_revenue"].max(),
        "peak_revenue_month": int(df.loc[df["total_revenue"].idxmax(), "month"]),
        "products_launched_final": int(last["products_launched"]),
        "total_prescribers_final": int(last["total_prescribers"]),
        "revenue_year1": y1["total_revenue"].sum(),
        "revenue_year3": y3["total_revenue"].sum(),
    }

    # Per-product KPIs
    for p in products:
        prefix = p.code
        col_rev = f"{prefix}_revenue"
        col_pat = f"{prefix}_patients"
        if col_rev in df.columns:
            kpis[f"{prefix}_total_revenue"] = df[col_rev].sum()
            kpis[f"{prefix}_peak_patients"] = int(df[col_pat].max())
            kpis[f"{prefix}_peak_revenue_month"] = round(df[col_rev].max())
            # Revenue share of portfolio
            total_rev = df["total_revenue"].sum()
            kpis[f"{prefix}_revenue_share"] = df[col_rev].sum() / total_rev if total_rev > 0 else 0

    # Break-even month (cumulative profit > 0)
    breakeven = df[df["cumulative_profit"] > 0]
    kpis["breakeven_month"] = int(breakeven.iloc[0]["month"]) if len(breakeven) > 0 else None

    return kpis
