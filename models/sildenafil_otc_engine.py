"""
Sildenafil Rx-to-OTC Switch Forecast Engine (Viatris / Viagra)
================================================================
Advanced Rx-to-OTC model with omnichannel distribution modeling.
All volumes in TABLETS (1 tablet = 1 application, 50mg).

Key differences vs. generic PPI switch model (Use Case 3):
  - Patient already pays 100% Rx (ED not covered by GKV) -> low price friction
  - Massive treatment gap: ~70% of ED patients never see a doctor (shame barrier)
  - OTC removes stigma barrier -> huge market expansion (UK ref: 63% new patients)
  - Apothekenpflichtig: stationaere Apotheke vs. Online-Apotheke
  - Brand premium: Viagra vs. generic sildenafil OTC pricing power
  - Competitor dynamics: Tadalafil (Cialis) remains Rx-only -> competitive moat

Reference case: UK Viagra Connect (launched March 2018)
  - 50mg OTC, pharmacy-only, GBP 5/tablet
  - Year 1: ~GBP 16M retail, 63% new-to-therapy patients
  - NHS Rx prescriptions ALSO increased (no cannibalization of Rx channel)
  - Signif. more GP/pharmacy visits post-switch (Lee et al. 2021, n=1,162)

Epidemiology (Germany):
  - ~5M men with moderate-to-complete ED (Braun et al. 2000)
  - Prevalence 19.2% in men 30-80 (Braun et al. 2000; Cologne Male Survey)
  - 1 in 4 newly diagnosed <40 years (Capogrosso et al. 2013)
  - Only ~30% in medical treatment (May et al. 2007; Arnold 2023)

Market data (Germany):
  - ~2.6M PDE5 packs/year; Sildenafil 55-65% share
  - Viagra brand: ~10% of sildenafil volume (rest generics)
  - Generic Rx: EUR 0.95-2.30/tablet; Viagra brand: EUR 8-14/tablet
  - BfArM SVA rejected 3x (2022, 2023, 2025) but BMG wants switch

Key sources:
  - Arnold M (2023). Public-Health-Impact eines moeglichen OTC-Switches von
    Sildenafil 50 mg. Hauptstadtkongress Berlin, inav-Gutachten (Viatris).
  - Lee et al. (2021). UK real-world study, n=1,162 (PMC)
  - Braun et al. (2000). Cologne Male Survey -- ED prevalence DE
  - May et al. (2007). Cottbus Survey, n=10,000 -- treatment rate ~30%
  - Capogrosso et al. (2013). 1 in 4 new ED patients <40 years
  - MHRA (2017). Public Assessment Report Viagra Connect BTC reclassification
  - Gordijn et al. (2022). NI pharmacy consultations for OTC sildenafil
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
    share_of_otc: float = 0.55           # % of OTC volume through this channel
    share_trend_annual: float = -0.02    # annual shift (neg = losing share)
    margin_pct: float = 0.42            # pharmacy/platform margin
    distribution_cost_pct: float = 0.06  # logistics
    discretion_factor: float = 0.8       # 1.0 = max discretion, affects stigma-driven demand


# ===================================================================
# MAIN MODEL PARAMETERS
# ===================================================================

@dataclass
class SildenafilOtcParams:
    """Parameters for Sildenafil Rx-to-OTC switch forecast.

    All volumes are in TABLETS (1 tablet = 1 application = 50mg sildenafil).
    Prices are per tablet. Revenue = tablets x price_per_tablet.
    """

    # --- Product ------------------------------------------------
    product_name: str = "Viagra Connect 50mg"
    company: str = "Viatris"
    molecule: str = "Sildenafil"
    otc_dosage: str = "50mg"
    switch_year: int = 2027  # hypothetical switch date

    # --- Epidemiology -------------------------------------------
    ed_prevalence_men: int = 5_000_000     # men with moderate-to-complete ED (DE)
    treatment_rate: float = 0.30           # currently treated (May et al. 2007; Arnold 2023)
    # --- Rx channel (pre-switch) --------------------------------
    # 217K packs/month x 4 tablets/pack = 868K tablets/month
    rx_tablets_per_month: int = 868_000    # sildenafil Rx tablets/month
    rx_price_brand: float = 11.19          # Viagra brand per tablet (pharmacy retail)
    rx_price_generic: float = 1.50         # average generic per tablet (pharmacy retail)
    rx_brand_share: float = 0.10           # Viagra brand % of sildenafil volume
    rx_manufacturer_share: float = 0.52    # manufacturer share of Rx retail price
    # (retail - wholesale margin ~8% - pharmacy margin ~40% = ~52% ex-factory)
    # Note: rx_decline is no longer an independent parameter.
    # It is DERIVED from otc_from_rx_migration (= otc_tablets * (1 - new_patient_share)).
    # This ensures consistency: tablets that migrate from Rx to OTC are subtracted
    # from rx_tablets, not modeled via a separate exponential curve.

    # --- OTC channel --------------------------------------------
    otc_price_per_tablet: float = 5.99     # Viagra Connect OTC per tablet
    # 350K packs/month x 6 tablets/pack = 2.1M tablets/month
    otc_peak_tablets_per_month: int = 2_100_000  # peak OTC tablets/month (all channels)
    otc_ramp_months: int = 18              # months to reach peak

    # --- Market expansion (the core thesis) ---------------------
    new_patient_share: float = 0.63        # UK reference: 63% were new-to-therapy
    tablets_per_patient_per_month: float = 4.0  # avg tablets/patient/month (for treatment gap calc)

    # --- Brand vs. Generic OTC ----------------------------------
    brand_otc_share: float = 0.25          # Viagra Connect vs generic OTC sildenafil
    brand_otc_share_trend: float = -0.03   # annual erosion from generic OTC entrants
    brand_price_premium: float = 1.8       # brand is 1.8x generic OTC price

    # --- Price dynamics -----------------------------------------
    price_elasticity: float = -0.5         # lower than PPI: ED patients less price-sensitive
    price_trend_annual: float = -0.03      # generic competition drives prices down
    # Note: lower elasticity because patients already pay 100% for Rx

    # --- Omnichannel distribution -------------------------------
    # Sildenafil OTC would be apothekenpflichtig (pharmacy-only) in DE,
    # like UK Viagra Connect.  No Drogerie/Supermarkt channel.
    channels: list = field(default_factory=lambda: [
        ChannelParams(
            name="Stationaere Apotheke",
            share_of_otc=0.55,
            share_trend_annual=-0.02,   # ABDA ZDF 2024: OTC online +1.5-2 pp/yr (2019-2024)
            margin_pct=0.42,
            distribution_cost_pct=0.06,
            discretion_factor=0.70,     # lower: face-to-face = more stigma
        ),
        ChannelParams(
            name="Online-Apotheke",
            share_of_otc=0.45,
            share_trend_annual=0.02,    # ABDA ZDF 2024: ~+1.5-2 pp/yr general OTC
            margin_pct=0.30,            # lower margin, competitive pricing
            distribution_cost_pct=0.10, # shipping costs
            discretion_factor=1.0,      # maximum: anonymous ordering
        ),
    ])

    # --- Competitor (Tadalafil stays Rx) ------------------------
    # 120K packs/month x 4 tablets/pack = 480K tablets/month
    tadalafil_rx_tablets_monthly: int = 480_000  # Tadalafil Rx tablets/month
    tadalafil_switch_to_sildenafil_otc: float = 0.12  # % Tadalafil users switching to OTC Sildenafil
    tadalafil_migration_months: int = 24

    # --- Seasonality (ED: less seasonal than PPI) ---------------
    seasonality: list = field(default_factory=lambda: [
        0.90, 1.05, 1.00, 1.00, 1.05, 1.10,   # Jan-Jun (Feb=Valentine's, Jun=summer)
        1.05, 1.00, 0.95, 0.95, 0.95, 1.00,    # Jul-Dec
    ])

    # --- Marketing ----------------------------------------------
    marketing_monthly_eur: float = 500_000   # DTC brand building, cost only (no volume effect)
    marketing_maintenance_factor: float = 0.5  # reduce to 50% after ramp phase
    marketing_ramp_months: int = 18            # full spend for first 18 months, then maintenance

    # --- Costs --------------------------------------------------
    cogs_pct: float = 0.12                   # low COGS for established molecule
    # Channel-specific margins are in ChannelParams

    # --- Forecast -----------------------------------------------
    forecast_months: int = 60


# ===================================================================
# MATHEMATICAL PRIMITIVES
# ===================================================================

def _logistic(t: float, peak: float, midpoint: float, steepness: float) -> float:
    """Generic logistic S-curve."""
    x = -steepness * (t - midpoint)
    x = np.clip(x, -500, 500)
    return peak / (1.0 + np.exp(x))


def _otc_ramp(month: int, peak: int, ramp_months: int) -> float:
    """Logistic ramp for OTC volume (tablets)."""
    if ramp_months <= 0:
        return float(peak)
    midpoint = ramp_months * 0.45
    steepness = 6.0 / ramp_months
    x = -steepness * (month - midpoint)
    x = np.clip(x, -500, 500)
    return peak / (1.0 + np.exp(x))



def _channel_share(base_share: float, trend: float, month: int) -> float:
    """Channel share evolution over time."""
    return max(0.0, min(1.0, base_share + trend * (month / 12.0)))


# ===================================================================
# FORECAST ENGINE
# ===================================================================

def forecast_sildenafil_otc(
    params: SildenafilOtcParams,
    forecast_months: Optional[int] = None,
) -> pd.DataFrame:
    """Run the Sildenafil Rx-to-OTC switch forecast with omnichannel modeling.

    All volumes are in TABLETS (1 tablet = 1 application).
    Revenue = tablets x price_per_tablet (no pack_size conversion needed).

    Returns DataFrame with monthly data including:
    - Rx channel performance (tablets + revenue)
    - OTC channel by distribution channel (Apotheke, Online)
    - Brand vs. generic OTC split
    - Tadalafil migration
    - Profitability (marketing as cost only, no volume feedback)
    """
    months = forecast_months if forecast_months is not None else params.forecast_months

    rows = []
    cum = {
        "otc_revenue": 0.0, "rx_revenue": 0.0, "total_revenue": 0.0,
        "profit": 0.0, "marketing": 0.0,
    }

    for m in range(1, months + 1):
        year_frac = m / 12.0
        season_idx = (m - 1) % 12
        season_factor = params.seasonality[season_idx]

        # --- OTC Volume (total, in tablets) --------------------
        otc_base = _otc_ramp(m, params.otc_peak_tablets_per_month, params.otc_ramp_months)
        otc_seasonal = otc_base * season_factor

        # Price effect (compound, consistent with otc_price_now calculation)
        price_change = (1 + params.price_trend_annual) ** year_frac - 1.0
        price_vol_effect = 1.0 + (price_change * params.price_elasticity)
        otc_total_tablets = max(0, otc_seasonal * price_vol_effect)

        # --- Tadalafil migration bonus -------------------------
        tada_migration = _logistic(
            m, params.tadalafil_rx_tablets_monthly * params.tadalafil_switch_to_sildenafil_otc,
            params.tadalafil_migration_months * 0.5,
            6.0 / params.tadalafil_migration_months
        )
        otc_total_tablets += tada_migration

        # --- Volume decomposition (needed before Rx calc) ------
        otc_total_tablets_pre = round(otc_total_tablets)
        otc_from_tadalafil_pre = round(min(tada_migration, otc_total_tablets_pre))
        otc_excl_tada_pre = otc_total_tablets_pre - otc_from_tadalafil_pre
        otc_from_rx_migration_pre = otc_excl_tada_pre - round(otc_excl_tada_pre * params.new_patient_share)

        # --- Rx Channel ----------------------------------------
        # Rx tablets: baseline MINUS those that migrated to OTC.
        # This ensures consistency — tablets can't be in both pools.
        rx_tablets_base = max(0.0, params.rx_tablets_per_month - otc_from_rx_migration_pre)
        rx_tablets = rx_tablets_base * season_factor
        # Rx revenue = manufacturer share of retail (ex-factory),
        # consistent with OTC which also uses manufacturer revenue.
        rx_avg_retail_price = (
            params.rx_brand_share * params.rx_price_brand +
            (1 - params.rx_brand_share) * params.rx_price_generic
        )
        rx_revenue = rx_tablets * rx_avg_retail_price * params.rx_manufacturer_share

        # --- Omnichannel distribution --------------------------
        # Calculate share for each channel with time evolution
        raw_shares = []
        for ch in params.channels:
            raw_shares.append(_channel_share(ch.share_of_otc, ch.share_trend_annual, m))
        # Normalize to sum to 1.0
        share_sum = sum(raw_shares)
        norm_shares = [s / share_sum for s in raw_shares] if share_sum > 0 else raw_shares

        channel_data = {}
        total_otc_manufacturer_revenue = 0.0
        total_otc_retail_revenue = 0.0

        # Apply discretion bonus to channel weights, then re-normalize
        # so total volume stays at otc_total_tablets (bonus shifts mix, not inflates)
        weighted_shares = []
        for i, ch in enumerate(params.channels):
            discretion_bonus = 1.0 + (ch.discretion_factor - 0.7) * 0.15
            weighted_shares.append(norm_shares[i] * discretion_bonus)
        ws_sum = sum(weighted_shares)
        disc_shares = [s / ws_sum for s in weighted_shares] if ws_sum > 0 else norm_shares

        # Current OTC price with erosion (compute once per month)
        otc_price_now = params.otc_price_per_tablet * (
            1 + params.price_trend_annual
        ) ** year_frac

        for i, ch in enumerate(params.channels):
            ch_share = disc_shares[i]
            ch_tablets = otc_total_tablets * ch_share

            # Revenue = tablets x price_per_tablet (direct, no pack_size)
            ch_retail_rev = ch_tablets * otc_price_now

            # Manufacturer revenue = retail - channel margin - distribution
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

        otc_total_tablets_adj = round(otc_total_tablets)

        # --- Brand vs. Generic OTC -----------------------------
        brand_share = max(0.10, params.brand_otc_share + params.brand_otc_share_trend * year_frac)
        otc_brand_tablets = round(otc_total_tablets_adj * brand_share)
        otc_generic_tablets = otc_total_tablets_adj - otc_brand_tablets  # ensures sum == total

        # Brand premium: Viagra Connect sells at a premium vs. generic OTC.
        generic_price = otc_price_now
        brand_price = otc_price_now * params.brand_price_premium
        brand_rev_bonus = otc_brand_tablets * (brand_price - generic_price)
        avg_mfr_pct = total_otc_manufacturer_revenue / total_otc_retail_revenue if total_otc_retail_revenue > 0 else 0.52
        brand_mfr_bonus = brand_rev_bonus * avg_mfr_pct
        total_otc_manufacturer_revenue += brand_mfr_bonus
        total_otc_retail_revenue += brand_rev_bonus
        # Distribute brand premium proportionally across channels
        for ch_name, ch_data in channel_data.items():
            if total_otc_retail_revenue > 0:
                ch_fraction = ch_data["retail_revenue"] / (total_otc_retail_revenue - brand_rev_bonus)
            else:
                ch_fraction = 0.5
            ch_data["retail_revenue"] = round(ch_data["retail_revenue"] + brand_rev_bonus * ch_fraction)
            ch_data["manufacturer_revenue"] = round(ch_data["manufacturer_revenue"] + brand_mfr_bonus * ch_fraction)

        # --- Volume decomposition (final, uses same values as pre-calc) ---
        otc_from_tadalafil = otc_from_tadalafil_pre
        otc_from_new_patients = round(otc_excl_tada_pre * params.new_patient_share)
        otc_from_rx_migration = otc_excl_tada_pre - otc_from_new_patients

        # --- Total tablets (no double-counting) ----------------
        total_tablets = rx_tablets + otc_total_tablets_adj

        # --- Marketing (cost only, no volume effect) -----------
        marketing_spend = params.marketing_monthly_eur
        if m > params.marketing_ramp_months:
            marketing_spend *= params.marketing_maintenance_factor

        # --- Profitability -------------------------------------
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

        # --- Treatment gap metric (derived from OTC volume) -----
        # Derive active new OTC patients from actual volume, not independently.
        # new_patients_tablets = otc_from_new_patients (tablets this month)
        # active_new_patients = tablets / tablets_per_patient_per_month
        if params.tablets_per_patient_per_month > 0:
            active_new_patients = otc_from_new_patients / params.tablets_per_patient_per_month
        else:
            active_new_patients = 0
        treatment_rate_new = params.treatment_rate + (
            active_new_patients / params.ed_prevalence_men
        )

        rows.append({
            "month": m,
            "date": pd.Timestamp(params.switch_year, 1, 1) + pd.DateOffset(months=m - 1),

            # Rx
            "rx_tablets": round(rx_tablets),
            "rx_revenue": round(rx_revenue),

            # OTC total
            "otc_tablets": round(otc_total_tablets_adj),
            "otc_price_per_tablet": round(otc_price_now, 2),
            "otc_retail_revenue": round(total_otc_retail_revenue),
            "otc_manufacturer_revenue": round(total_otc_manufacturer_revenue),

            # OTC by channel (apothekenpflichtig: Apotheke + Online only)
            "ch_apotheke_tablets": channel_data.get(params.channels[0].name, {}).get("tablets", 0) if len(params.channels) > 0 else 0,
            "ch_apotheke_revenue": channel_data.get(params.channels[0].name, {}).get("manufacturer_revenue", 0) if len(params.channels) > 0 else 0,
            "ch_apotheke_share": channel_data.get(params.channels[0].name, {}).get("share", 0) if len(params.channels) > 0 else 0,
            "ch_online_tablets": channel_data.get(params.channels[1].name, {}).get("tablets", 0) if len(params.channels) > 1 else 0,
            "ch_online_revenue": channel_data.get(params.channels[1].name, {}).get("manufacturer_revenue", 0) if len(params.channels) > 1 else 0,
            "ch_online_share": channel_data.get(params.channels[1].name, {}).get("share", 0) if len(params.channels) > 1 else 0,

            # Brand vs Generic OTC
            "otc_brand_tablets": otc_brand_tablets,
            "otc_generic_tablets": otc_generic_tablets,
            "otc_brand_share": brand_share,

            # Volume decomposition (all in tablets)
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

            # Treatment gap (derived from OTC volume)
            "treatment_rate_effective": treatment_rate_new,
            "active_new_patients": round(active_new_patients),
        })

    return pd.DataFrame(rows)


def calculate_kpis_sildenafil(df: pd.DataFrame) -> dict:
    """Calculate KPIs from Sildenafil OTC forecast."""
    last = df.iloc[-1]
    y1 = df[df["month"] <= 12]

    # Crossover month -- revenue (OTC mfr revenue > Rx revenue)
    crossover = df[df["otc_manufacturer_revenue"] > df["rx_revenue"]]
    crossover_month = int(crossover.iloc[0]["month"]) if len(crossover) > 0 else None

    # Crossover month -- tablets (OTC tablets > Rx tablets)
    crossover_tabs = df[df["otc_tablets"] > df["rx_tablets"]]
    crossover_month_tablets = int(crossover_tabs.iloc[0]["month"]) if len(crossover_tabs) > 0 else None

    # Peak OTC
    peak_idx = df["otc_tablets"].idxmax()
    peak_otc_tablets = int(df.loc[peak_idx, "otc_tablets"])
    peak_otc_month = int(df.loc[peak_idx, "month"])

    # Rx decline (season-adjusted: compare Year 1 total vs. last-12-months total)
    rx_y1 = df[df["month"] <= 12]["rx_tablets"].sum()
    rx_last12 = df[df["month"] > (df["month"].max() - 12)]["rx_tablets"].sum()
    rx_decline_pct = (rx_y1 - rx_last12) / rx_y1 if rx_y1 > 0 else 0

    # Channel shares at month 12
    m12 = df[df["month"] == 12]
    m24 = df[df["month"] == 24]

    # Online share evolution
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
        "rx_decline_total": rx_decline_pct,
        "otc_share_m12": float(m12["otc_share_tablets"].iloc[0]) if len(m12) > 0 else 0,
        "otc_share_m24": float(m24["otc_share_tablets"].iloc[0]) if len(m24) > 0 else 0,
        "brand_share_m12": float(m12["otc_brand_share"].iloc[0]) if len(m12) > 0 else 0,
        "brand_share_m24": float(m24["otc_brand_share"].iloc[0]) if len(m24) > 0 else 0,
        "online_share_m12": online_share_m12,
        "online_share_m24": online_share_m24,
        "treatment_rate_final": last["treatment_rate_effective"],
        "peak_new_patients": int(df["active_new_patients"].max()),
    }
