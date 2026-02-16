"""
Forecast engine for generic entry scenarios.

Supports two perspectives:
1. ORIGINATOR: Revenue-at-Risk analysis (defensive)
2. GENERIC: Market Opportunity analysis (offensive)

Core methodology:
- S-curve (logistic) uptake for generic penetration
- Exponential decay for originator erosion
- Aut-idem substitution modeling (pharmacy-level switching)
- Tender/Rabattvertrag volume modeling (GKV-specific)
- Multi-competitor share allocation
- Price erosion modeling with competitive dynamics
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════
# PARAMETER CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class OriginatorParams:
    """Parameters for originator (Revenue-at-Risk) perspective."""
    # Pre-LOE baseline
    baseline_monthly_trx: int = 1_764_000
    baseline_price_per_trx: float = 91.50
    baseline_market_share: float = 0.42

    # Erosion parameters
    price_reduction_pct: float = 0.15
    erosion_speed: float = 1.0
    floor_share: float = 0.12
    months_to_floor: int = 18
    market_growth_annual: float = 0.02

    # Aut-idem parameters
    aut_idem_enabled: bool = True
    aut_idem_quote_peak: float = 0.75     # Peak: 75% of new Rx get substituted
    aut_idem_ramp_months: int = 6         # Months until Festbetrag/aut-idem kicks in
    aut_idem_full_months: int = 12        # Months until peak substitution rate

    # Authorized Generic
    authorized_generic: bool = False
    ag_share_of_generics: float = 0.25        # Initial AG share of generic segment
    ag_price_discount: float = 0.30           # Initial AG price discount vs originator
    ag_share_decay_speed: float = 0.0         # 0=static, 1=moderate decay, 2=fast decay
    ag_discount_growth_speed: float = 0.0     # 0=static, 1=moderate growth, 2=fast growth


@dataclass
class GenericParams:
    """Parameters for generic entrant (Market Opportunity) perspective."""
    # Market context
    total_market_monthly_trx: int = 4_200_000
    originator_price_per_trx: float = 91.50

    # My generic product
    my_company_name: str = "Mein Generikum"
    launch_month_offset: int = 0
    price_discount_vs_originator: float = 0.45
    target_peak_share: float = 0.10
    months_to_peak: int = 18

    # Generika-Segment (Gesamtmarkt inkl. meines Produkts)
    generic_segment_peak_share: float = 0.55    # Peak share aller Generika zusammen
    generic_segment_months_to_peak: int = 24    # Monate bis der Generika-Markt seinen Peak erreicht

    # Costs & profitability
    cogs_pct_of_revenue: float = 0.25
    sga_monthly_eur: float = 150_000
    launch_investment_eur: float = 500_000
    fixed_costs_monthly_eur: float = 50_000
    market_growth_annual: float = 0.02

    # Aut-idem parameters
    aut_idem_enabled: bool = True
    aut_idem_quote_peak: float = 0.75
    aut_idem_ramp_months: int = 6         # Delay until Festbetrag active
    aut_idem_full_months: int = 12
    my_aut_idem_capture: float = 0.30     # My share of aut-idem substitutions

    # Tender parameters
    tender_enabled: bool = True
    tender_start_month: int = 3           # Months after launch until first tender

    # Individual Kasse tenders (name, covered_lives_mio, win_probability, volume_uplift)
    tender_kassen: list = None

    def __post_init__(self):
        if self.tender_kassen is None:
            self.tender_kassen = [
                {"name": "TK", "lives_mio": 11.5, "gkv_share": 0.158,
                 "win_prob": 0.50, "status": "Ziel"},
                {"name": "BARMER", "lives_mio": 8.7, "gkv_share": 0.119,
                 "win_prob": 0.40, "status": "Ziel"},
                {"name": "DAK", "lives_mio": 5.5, "gkv_share": 0.075,
                 "win_prob": 0.45, "status": "Ziel"},
                {"name": "AOK Bayern", "lives_mio": 4.6, "gkv_share": 0.063,
                 "win_prob": 0.30, "status": "Optional"},
                {"name": "AOK BaWü", "lives_mio": 4.5, "gkv_share": 0.062,
                 "win_prob": 0.30, "status": "Optional"},
                {"name": "AOK Nordwest", "lives_mio": 3.0, "gkv_share": 0.041,
                 "win_prob": 0.35, "status": "Optional"},
                {"name": "AOK Rhld/Hbg", "lives_mio": 2.9, "gkv_share": 0.040,
                 "win_prob": 0.35, "status": "Optional"},
                {"name": "IKK classic", "lives_mio": 3.0, "gkv_share": 0.041,
                 "win_prob": 0.25, "status": "Nachrangig"},
                {"name": "KKH", "lives_mio": 1.5, "gkv_share": 0.021,
                 "win_prob": 0.20, "status": "Nachrangig"},
                {"name": "hkk", "lives_mio": 0.9, "gkv_share": 0.012,
                 "win_prob": 0.20, "status": "Nachrangig"},
            ]


# ═══════════════════════════════════════════════════════════════════════
# CURVE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _logistic_curve(t: np.ndarray, midpoint: float, steepness: float) -> np.ndarray:
    """S-curve (logistic) function for uptake modeling."""
    return 1 / (1 + np.exp(-steepness * (t - midpoint)))


def _erosion_curve(
    t: np.ndarray,
    initial_share: float,
    floor_share: float,
    months_to_floor: int,
    speed: float = 1.0,
) -> np.ndarray:
    """Exponential decay curve for originator share erosion."""
    decay_rate = -np.log(0.05) / months_to_floor * speed
    share_range = initial_share - floor_share
    erosion = share_range * (1 - np.exp(-decay_rate * t))
    return initial_share - erosion


def _aut_idem_curve(
    t: int,
    ramp_months: int,
    full_months: int,
    peak_quote: float,
) -> float:
    """
    Model aut-idem substitution rate over time.

    Timeline:
    - t=0 to ramp_months: No substitution (Festbetrag not yet active)
    - ramp_months to full_months: Linear ramp-up
    - After full_months: Plateau at peak_quote

    In reality, aut-idem becomes relevant once:
    1. Generic is in Festbetragsgruppe (G-BA decision, ~3-6 months)
    2. Pharmacies are mandated to substitute (SGB V §129)
    3. Physicians haven't marked "aut idem" exclusion on Rx
    """
    if t < ramp_months:
        return 0.0
    elif t < full_months:
        progress = (t - ramp_months) / (full_months - ramp_months)
        return peak_quote * progress
    else:
        return peak_quote


def _tender_volume_boost(
    t: int,
    params: GenericParams,
) -> tuple[float, dict]:
    """
    Calculate expected volume boost from GKV Rabattverträge.

    Returns:
        (boost_factor, details_dict)

    Logic:
    - Each Kasse has a GKV market share (% of total insured)
    - Win probability × GKV share = expected volume contribution
    - Sum across all Kassen = total expected boost
    - Ramp-up after tender_start_month
    """
    if not params.tender_enabled or t < params.tender_start_month:
        return 1.0, {"tender_active": False, "expected_uplift": 0}

    months_active = t - params.tender_start_month
    # Ramp up over 6 months as contracts are negotiated
    ramp = min(1.0, months_active / 6)

    total_expected_share = 0.0
    kasse_details = []
    for kasse in params.tender_kassen:
        if kasse["status"] == "Nachrangig" and months_active < 12:
            continue  # Lower priority Kassen join later
        expected = kasse["gkv_share"] * kasse["win_prob"]
        total_expected_share += expected
        kasse_details.append({
            "name": kasse["name"],
            "expected_volume_share": expected,
        })

    # Tender boost: if we win e.g. 20% of GKV market through tenders,
    # those patients MUST get our product (exclusive contract)
    # This adds on top of organic share
    boost = 1.0 + total_expected_share * ramp * 2.5  # 2.5x multiplier for exclusivity effect

    return boost, {
        "tender_active": True,
        "expected_uplift": total_expected_share * ramp,
        "kasse_count": len(kasse_details),
    }


# ═══════════════════════════════════════════════════════════════════════
# ORIGINATOR FORECAST
# ═══════════════════════════════════════════════════════════════════════

def forecast_originator(
    params: OriginatorParams,
    forecast_months: int = 60,
    loe_date: str = "2026-05-01",
) -> pd.DataFrame:
    """Generate monthly forecast from ORIGINATOR perspective."""
    # BUG-E6 fix: Fixed seed for reproducible pre-LOE noise
    rng = np.random.default_rng(42)

    loe = pd.Timestamp(loe_date)
    start_date = loe - pd.DateOffset(months=12)
    dates = pd.date_range(start_date, periods=12 + forecast_months, freq="MS")

    rows = []
    for i, date in enumerate(dates):
        months_since_loe = (date.year - loe.year) * 12 + (date.month - loe.month)
        is_post_loe = months_since_loe >= 0

        months_from_start = i
        market_growth = (1 + params.market_growth_annual / 12) ** months_from_start
        total_market_trx = params.baseline_monthly_trx / params.baseline_market_share * market_growth

        if not is_post_loe:
            share = params.baseline_market_share + rng.normal(0, 0.003)
            share = np.clip(share, params.baseline_market_share - 0.02,
                          params.baseline_market_share + 0.02)
            price = params.baseline_price_per_trx
            trx = int(total_market_trx * share)
            generic_trx = 0
            generic_share = 0.0
            aut_idem_rate = 0.0
        else:
            t = months_since_loe

            # Base erosion curve
            share = _erosion_curve(
                np.array([t]),
                params.baseline_market_share,
                params.floor_share,
                params.months_to_floor,
                params.erosion_speed,
            )[0]

            # Aut-idem acceleration: increases erosion speed
            aut_idem_rate = 0.0
            if params.aut_idem_enabled:
                aut_idem_rate = _aut_idem_curve(
                    t, params.aut_idem_ramp_months,
                    params.aut_idem_full_months, params.aut_idem_quote_peak
                )
                # Aut-idem pulls additional share from originator
                # Effect: each substitutable Rx has aut_idem_rate chance of switching
                additional_erosion = (share - params.floor_share) * aut_idem_rate * 0.3
                share = max(params.floor_share, share - additional_erosion)

            # Price pressure
            price_reduction = params.price_reduction_pct * min(1.0, t / 6)
            price = params.baseline_price_per_trx * (1 - price_reduction)

            trx = int(total_market_trx * share)

            generic_share = params.baseline_market_share - share
            # 0.85 factor: not all lost originator share goes to generics;
            # ~15% is absorbed by other originators (Xarelto, Lixiana) or market shifts
            generic_share = max(0, generic_share * 0.85)
            generic_trx = int(total_market_trx * generic_share)

        price = round(price, 2)
        revenue = trx * price
        counterfactual_trx = int(total_market_trx * params.baseline_market_share)
        counterfactual_revenue = counterfactual_trx * params.baseline_price_per_trx
        revenue_at_risk = max(0, counterfactual_revenue - revenue) if is_post_loe else 0

        ag_revenue = 0
        ag_trx = 0
        ag_share_current = 0.0
        ag_discount_current = 0.0
        if params.authorized_generic and is_post_loe and months_since_loe >= 0:
            # Dynamic AG share: decays over time as independent generics gain ground
            # decay_factor: speed=0 → 1.0 (static), speed=1 → ~0.37 at 20mo, speed=2 → ~0.14 at 20mo
            ag_share_current = params.ag_share_of_generics * np.exp(
                -params.ag_share_decay_speed * 0.05 * months_since_loe
            )
            ag_share_current = max(0.02, ag_share_current)  # Floor: 2% minimum share

            # Dynamic AG discount: grows over time as price pressure increases
            # Discount approaches 100% asymptotically; speed=0 → static
            if params.ag_discount_growth_speed > 0:
                ag_discount_current = 1.0 - (1.0 - params.ag_price_discount) * np.exp(
                    -params.ag_discount_growth_speed * 0.03 * months_since_loe
                )
                ag_discount_current = min(0.85, ag_discount_current)  # Cap: max 85% discount
            else:
                ag_discount_current = params.ag_price_discount

            ag_trx = int(generic_trx * ag_share_current)
            ag_price = round(params.baseline_price_per_trx * (1 - ag_discount_current), 2)
            ag_revenue = ag_trx * ag_price

        rows.append({
            "date": date,
            "month": date.strftime("%Y-%m"),
            "months_since_loe": months_since_loe,
            "is_post_loe": is_post_loe,
            "total_market_trx": int(total_market_trx),
            "originator_trx": trx,
            "originator_share": round(share, 4),
            "originator_price": price,
            "originator_revenue": round(revenue, 2),
            "generic_segment_trx": generic_trx,
            "generic_segment_share": round(generic_share, 4),
            "aut_idem_rate": round(aut_idem_rate, 4),
            "counterfactual_revenue": round(counterfactual_revenue, 2),
            "revenue_at_risk": round(revenue_at_risk, 2),
            "cumulative_revenue_at_risk": 0,
            "ag_trx": ag_trx,
            "ag_share_current": round(ag_share_current, 4),
            "ag_discount_current": round(ag_discount_current, 4),
            "ag_revenue": round(ag_revenue, 2),
            "total_originator_revenue": round(revenue + ag_revenue, 2),
        })

    df = pd.DataFrame(rows)
    df["cumulative_revenue_at_risk"] = df["revenue_at_risk"].cumsum()
    return df


# ═══════════════════════════════════════════════════════════════════════
# GENERIC FORECAST
# ═══════════════════════════════════════════════════════════════════════

def forecast_generic(
    params: GenericParams,
    forecast_months: int = 60,
    loe_date: str = "2026-05-01",
) -> pd.DataFrame:
    """Generate monthly forecast from GENERIC ENTRANT perspective."""
    loe = pd.Timestamp(loe_date)
    launch_date = loe + pd.DateOffset(months=params.launch_month_offset)
    dates = pd.date_range(loe, periods=forecast_months, freq="MS")

    rows = []
    cumulative_revenue = 0
    cumulative_profit = 0

    for i, date in enumerate(dates):
        months_since_loe = i
        months_since_launch = (date.year - launch_date.year) * 12 + (date.month - launch_date.month)
        is_launched = months_since_launch >= 0

        market_growth = (1 + params.market_growth_annual / 12) ** i
        total_market_trx = params.total_market_monthly_trx * market_growth

        # Generika-Segment S-curve (used in both branches)
        seg_midpoint = params.generic_segment_months_to_peak / 2
        seg_steepness = 4.0 / params.generic_segment_months_to_peak * 1.2

        if not is_launched:
            my_share = 0.0
            my_trx = 0
            my_price = 0
            my_revenue = 0
            aut_idem_rate = 0.0
            aut_idem_trx = 0
            tender_boost = 1.0
            tender_trx = 0
            organic_trx = 0
            total_generic_share = float(_logistic_curve(
                np.array([months_since_loe]),
                midpoint=seg_midpoint, steepness=seg_steepness
            )[0]) * params.generic_segment_peak_share
        else:
            t = months_since_launch

            # === ORGANIC UPTAKE (base S-curve) ===
            midpoint = params.months_to_peak / 2
            steepness = 4.0 / params.months_to_peak * 1.5
            uptake = float(_logistic_curve(np.array([t]), midpoint, steepness)[0])

            # Organic share: target_peak_share represents the user's estimate
            # of achievable peak market share (already accounts for competition).
            # Cap at segment peak to ensure consistency.
            effective_peak = min(params.target_peak_share, params.generic_segment_peak_share)
            organic_share = effective_peak * uptake * 0.5  # 50% from organic
            organic_trx = int(total_market_trx * organic_share)

            # === AUT-IDEM COMPONENT ===
            aut_idem_rate = 0.0
            aut_idem_trx = 0
            if params.aut_idem_enabled:
                aut_idem_rate = _aut_idem_curve(
                    t, params.aut_idem_ramp_months,
                    params.aut_idem_full_months, params.aut_idem_quote_peak
                )
                # Aut-idem drives substitution at pharmacy level
                # Total substitutable Rx × aut-idem rate × my capture share
                originator_remaining = total_market_trx * 0.42 * max(0.3, 1.0 - uptake)
                aut_idem_trx = int(
                    originator_remaining * aut_idem_rate * params.my_aut_idem_capture
                )

            # === TENDER COMPONENT ===
            tender_boost_factor, tender_details = _tender_volume_boost(t, params)
            tender_trx = int(organic_trx * (tender_boost_factor - 1.0))

            # === TOTAL ===
            my_trx = organic_trx + aut_idem_trx + tender_trx
            my_share = my_trx / total_market_trx if total_market_trx > 0 else 0

            # Price
            additional_price_erosion = min(0.15, t * 0.003)
            my_price = params.originator_price_per_trx * (
                1 - params.price_discount_vs_originator - additional_price_erosion
            )
            my_price = round(max(my_price, 20.0), 2)

            my_revenue = my_trx * my_price

            total_generic_share = float(_logistic_curve(
                np.array([months_since_loe]),
                midpoint=seg_midpoint, steepness=seg_steepness
            )[0]) * params.generic_segment_peak_share

        # Profitability
        cogs = my_revenue * params.cogs_pct_of_revenue if is_launched else 0
        sga = params.sga_monthly_eur if is_launched else params.sga_monthly_eur * 0.5
        fixed = params.fixed_costs_monthly_eur
        # Launch investment in first month
        launch_cost = params.launch_investment_eur if (is_launched and months_since_launch == 0) else 0
        gross_profit = my_revenue - cogs
        operating_profit = gross_profit - sga - fixed - launch_cost

        cumulative_revenue += my_revenue
        cumulative_profit += operating_profit

        rows.append({
            "date": date,
            "month": date.strftime("%Y-%m"),
            "months_since_loe": months_since_loe,
            "months_since_launch": months_since_launch if is_launched else None,
            "is_launched": is_launched,
            "total_market_trx": int(total_market_trx),
            "total_generic_share": round(total_generic_share, 4),
            # Volume decomposition
            "organic_trx": organic_trx if is_launched else 0,
            "aut_idem_trx": aut_idem_trx if is_launched else 0,
            "tender_trx": tender_trx if is_launched else 0,
            "my_trx": my_trx,
            "my_share": round(my_share, 4),
            "aut_idem_rate": round(aut_idem_rate, 4),
            # Revenue & Profit
            "my_price": my_price,
            "my_revenue": round(my_revenue, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "sga": round(sga, 2),
            "fixed_costs": round(fixed, 2),
            "launch_cost": round(launch_cost, 2),
            "operating_profit": round(operating_profit, 2),
            "cumulative_revenue": round(cumulative_revenue, 2),
            "cumulative_profit": round(cumulative_profit, 2),
            "breakeven_reached": cumulative_profit > 0,
        })

    df = pd.DataFrame(rows)
    return df


# ═══════════════════════════════════════════════════════════════════════
# KPI CALCULATORS
# ═══════════════════════════════════════════════════════════════════════

def calculate_kpis_originator(df: pd.DataFrame) -> dict:
    post_loe = df[df["is_post_loe"]]
    pre_loe = df[~df["is_post_loe"]]

    peak_monthly_revenue = pre_loe["originator_revenue"].max()
    year1_post = post_loe.head(12)
    year1_revenue = year1_post["originator_revenue"].sum()
    pre_loe_annual_revenue = pre_loe.tail(12)["originator_revenue"].sum()

    return {
        "peak_monthly_revenue": peak_monthly_revenue,
        "pre_loe_annual_revenue": pre_loe_annual_revenue,
        "year1_post_loe_revenue": year1_revenue,
        "year1_revenue_decline_pct": (1 - year1_revenue / pre_loe_annual_revenue) * 100 if pre_loe_annual_revenue > 0 else 0,
        "total_revenue_at_risk_5y": post_loe["revenue_at_risk"].sum(),
        "cumulative_revenue_at_risk": post_loe["cumulative_revenue_at_risk"].iloc[-1] if len(post_loe) > 0 else 0,
        "share_at_month_12": post_loe.iloc[11]["originator_share"] if len(post_loe) > 11 else None,
        "share_at_month_24": post_loe.iloc[23]["originator_share"] if len(post_loe) > 23 else None,
        "share_at_month_60": post_loe.iloc[-1]["originator_share"] if len(post_loe) > 0 else None,
    }


def calculate_kpis_generic(df: pd.DataFrame) -> dict:
    launched = df[df["is_launched"]]

    if len(launched) == 0:
        return {"status": "Not yet launched"}

    breakeven_rows = launched[launched["cumulative_profit"] > 0]
    breakeven_month = breakeven_rows.iloc[0]["months_since_loe"] if len(breakeven_rows) > 0 else None

    year1 = launched.head(12)
    peak_monthly = launched["my_revenue"].max()

    # Volume decomposition
    total_organic = launched["organic_trx"].sum()
    total_aut_idem = launched["aut_idem_trx"].sum()
    total_tender = launched["tender_trx"].sum()
    total_all = total_organic + total_aut_idem + total_tender

    return {
        "year1_revenue": year1["my_revenue"].sum(),
        "year1_profit": year1["operating_profit"].sum(),
        "total_5y_revenue": launched["my_revenue"].sum(),
        "total_5y_profit": launched["operating_profit"].sum(),
        "peak_monthly_revenue": peak_monthly,
        "peak_share": launched["my_share"].max(),
        "breakeven_month": breakeven_month,
        "cumulative_revenue": launched["cumulative_revenue"].iloc[-1],
        "cumulative_profit": launched["cumulative_profit"].iloc[-1],
        "avg_price": launched[launched["my_price"] > 0]["my_price"].mean(),
        # Volume decomposition
        "volume_organic_pct": total_organic / total_all if total_all > 0 else 0,
        "volume_aut_idem_pct": total_aut_idem / total_all if total_all > 0 else 0,
        "volume_tender_pct": total_tender / total_all if total_all > 0 else 0,
    }
