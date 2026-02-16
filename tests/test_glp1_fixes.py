"""Verification tests for patient-based GLP-1 forecast engine."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.brand_competition_engine import (
    IndicationParams, BrandParams, MarketParams,
    forecast_brand, calculate_kpis_brand,
    default_lilly_indications, default_novo_indications,
    _share_shift_curve,
)

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {detail}")


print("=== Patient-Based GLP-1 Engine Tests ===\n")

# --- Basic forecast (Lilly defaults) ---
brand = BrandParams(indications=default_lilly_indications())
df = forecast_brand(brand)
kpis = calculate_kpis_brand(df)

check("T01: 60 rows generated", len(df) == 60, f"got {len(df)}")
check("T02: Year1 revenue > 0", kpis["year1_revenue"] > 0)
check("T03: Peak patients > 0", kpis["peak_patients"] > 0)
check("T04: Peak share grows from start",
      kpis["peak_share"] > 0.08,
      f"peak_share={kpis['peak_share']}")

# --- T2D is the dominant indication ---
check("T05: T2D patients > Adipositas patients",
      kpis["patients_by_indication"]["t2d"] > kpis["patients_by_indication"]["adipositas"])
check("T06: T2D revenue > Adipositas revenue",
      kpis["revenue_by_indication"]["t2d"] > kpis["revenue_by_indication"]["adipositas"])

# --- Disabled indications contribute 0 ---
check("T07: CV-Risiko patients = 0 (disabled)",
      kpis["patients_by_indication"].get("cvrisiko", 0) == 0)
check("T08: MASH patients = 0 (disabled)",
      kpis["patients_by_indication"].get("mash", 0) == 0)

# --- Enabling CV increases total revenue ---
inds_cv = default_lilly_indications()
inds_cv[2].enabled = True  # CV-Risiko
brand_cv = BrandParams(indications=inds_cv)
df_cv = forecast_brand(brand_cv)
kpis_cv = calculate_kpis_brand(df_cv)
check("T09: Enabling CV increases total 5Y revenue",
      kpis_cv["total_5y_revenue"] > kpis["total_5y_revenue"],
      f"with_cv={kpis_cv['total_5y_revenue']:,.0f} vs base={kpis['total_5y_revenue']:,.0f}")

# --- Enabling MASH increases total revenue ---
inds_mash = default_lilly_indications()
inds_mash[3].enabled = True  # MASH
brand_mash = BrandParams(indications=inds_mash)
df_mash = forecast_brand(brand_mash)
kpis_mash = calculate_kpis_brand(df_mash)
check("T10: Enabling MASH increases total 5Y revenue",
      kpis_mash["total_5y_revenue"] > kpis["total_5y_revenue"])

# --- Persistence reduces patients ---
inds_high_p = default_lilly_indications()
inds_high_p[0].persistence_12m = 0.95  # High persistence
brand_hp = BrandParams(indications=inds_high_p)
df_hp = forecast_brand(brand_hp)

inds_low_p = default_lilly_indications()
inds_low_p[0].persistence_12m = 0.40  # Low persistence
brand_lp = BrandParams(indications=inds_low_p)
df_lp = forecast_brand(brand_lp)

check("T11: Higher persistence = more T2D patients",
      df_hp["patients_t2d"].iloc[-1] > df_lp["patients_t2d"].iloc[-1],
      f"high={df_hp['patients_t2d'].iloc[-1]:,}, low={df_lp['patients_t2d'].iloc[-1]:,}")

# --- Per-indication prices flow through ---
inds_custom = default_lilly_indications()
inds_custom[0].price_per_month = 500.0  # Expensive T2D
brand_exp = BrandParams(indications=inds_custom)
df_exp = forecast_brand(brand_exp)
kpis_exp = calculate_kpis_brand(df_exp)
check("T12: Higher T2D price -> higher T2D revenue",
      kpis_exp["revenue_by_indication"]["t2d"] > kpis["revenue_by_indication"]["t2d"])

# --- Adipositas GKV vs no-GKV (treatment rate difference) ---
inds_gkv = default_lilly_indications()
inds_gkv[1].treated_pct_peak = 0.05  # GKV: 5%
brand_gkv = BrandParams(indications=inds_gkv)
df_gkv = forecast_brand(brand_gkv)
kpis_gkv = calculate_kpis_brand(df_gkv)
check("T13: Higher adipo treatment rate -> more adipo revenue",
      kpis_gkv["revenue_by_indication"]["adipositas"] > kpis["revenue_by_indication"]["adipositas"])

# --- Supply constraint caps total patients ---
brand_supply = BrandParams(
    indications=default_lilly_indications(),
    supply_constrained=True,
    supply_capacity_monthly_patients=50_000,
    supply_normalization_month=24,
)
df_supply = forecast_brand(brand_supply)
check("T14: Supply constraint limits patients at month 6",
      df_supply.iloc[6]["supply_gap"] > 0,
      f"supply_gap={df_supply.iloc[6]['supply_gap']}")
check("T15: Supply constraint lifts after normalization month",
      df_supply.iloc[30]["supply_gap"] == 0)

# --- Share normalization: my + comp always <= 90% (rest >= 10%) ---
# Extreme case: both claim 55%
inds_ext = default_lilly_indications()
inds_ext[0].my_share_peak = 0.55
inds_ext[0].competitor_share_peak = 0.50
inds_ext[0].months_to_peak_share = 12
inds_ext[0].competitor_months_to_peak = 12
brand_ext = BrandParams(indications=inds_ext)
df_ext = forecast_brand(brand_ext)
# Check T2D shares sum
max_share_sum = max(
    df_ext["share_t2d"].iloc[i] + df_ext.iloc[i].get("comp_patients_t2d", 0)
    for i in range(len(df_ext))
)
# Actually check via the raw share columns
all_ok = True
for i in range(len(df_ext)):
    my_s = df_ext.iloc[i]["share_t2d"]
    # comp_share not directly accessible, but weighted shares are
    # Let's check weighted shares instead
    total_w = df_ext.iloc[i]["my_share_weighted"] + df_ext.iloc[i]["comp_share_weighted"]
    if total_w > 0.91:  # Allow small rounding tolerance
        all_ok = False
        break
check("T16: Weighted shares sum <= 90% (extreme case)", all_ok,
      f"max_weighted={total_w:.3f}" if not all_ok else "")

# --- Competitor share evolution (Novo declines in Lilly view) ---
comp_start = df.iloc[0]["comp_share_weighted"]
comp_end = df.iloc[-1]["comp_share_weighted"]
check("T17: Competitor share declines (Novo from 36% -> 30%)",
      comp_end < comp_start,
      f"start={comp_start:.3f}, end={comp_end:.3f}")

# --- Price erosion ---
inds_erosion = default_lilly_indications()
brand_erosion = BrandParams(indications=inds_erosion, price_trend_annual=-0.10)
df_erosion = forecast_brand(brand_erosion)
# Revenue per patient should decrease
rev_per_pat_start = df_erosion.iloc[0]["my_revenue"] / max(df_erosion.iloc[0]["my_patients"], 1)
rev_per_pat_end = df_erosion.iloc[-1]["my_revenue"] / max(df_erosion.iloc[-1]["my_patients"], 1)
check("T18: Price erosion reduces revenue per patient",
      rev_per_pat_end < rev_per_pat_start,
      f"start={rev_per_pat_start:.0f}, end={rev_per_pat_end:.0f}")

# --- Profitability chain ---
row0 = df.iloc[0]
expected_cogs = row0["my_revenue"] * 0.20  # default cogs_pct
check("T19: COGS = revenue * cogs_pct",
      abs(row0["my_cogs"] - expected_cogs) < 1.0)

expected_op = row0["my_gross_profit"] - 800_000 - 200_000  # SGA + medical
check("T20: Operating profit = gross - SGA - medical",
      abs(row0["my_operating_profit"] - expected_op) < 1.0)

# --- KPI keys ---
check("T21: KPIs have all expected keys",
      all(k in kpis for k in [
          "year1_revenue", "total_5y_revenue", "peak_share",
          "overtake_month", "avg_price", "peak_patients",
          "patients_by_indication", "revenue_by_indication",
      ]))

# --- Novo perspective works too ---
brand_novo = BrandParams(
    name="Ozempic", company="Novo Nordisk",
    indications=default_novo_indications(),
)
df_novo = forecast_brand(brand_novo)
kpis_novo = calculate_kpis_brand(df_novo)
check("T22: Novo forecast generates 60 rows", len(df_novo) == 60)
check("T23: Novo year1 revenue > 0", kpis_novo["year1_revenue"] > 0)
check("T24: Novo peak share > Lilly start share (Novo starts higher)",
      kpis_novo["peak_share"] > 0.25,
      f"novo_peak={kpis_novo['peak_share']:.3f}")

# --- Launch delay: CV starts after delay ---
inds_delay = default_lilly_indications()
inds_delay[2].enabled = True
inds_delay[2].launch_delay_months = 12
brand_delay = BrandParams(indications=inds_delay)
df_delay = forecast_brand(brand_delay)
check("T25: CV patients = 0 before launch delay",
      df_delay.iloc[5]["patients_cvrisiko"] == 0)
check("T26: CV patients > 0 after launch delay",
      df_delay.iloc[20]["patients_cvrisiko"] > 0)

# --- S-curve function ---
check("T27: S-curve at t=0 close to start",
      abs(_share_shift_curve(0, 0.10, 0.50, 36) - 0.10) < 0.06)
check("T28: S-curve at t=peak close to target",
      abs(_share_shift_curve(60, 0.10, 0.50, 36) - 0.50) < 0.02)
check("T29: S-curve at midpoint ~ halfway",
      abs(_share_shift_curve(18, 0.10, 0.50, 36) - 0.30) < 0.05)

# --- Price floor ---
inds_floor = default_lilly_indications()
inds_floor[0].price_per_month = 110.0
brand_floor = BrandParams(indications=inds_floor, price_trend_annual=-0.50)
df_floor = forecast_brand(brand_floor)
# Check revenue_t2d to infer price (revenue / patients)
last = df_floor.iloc[-1]
if last["patients_t2d"] > 0:
    implied_price = last["revenue_t2d"] / last["patients_t2d"]
    check("T30: Price floor at EUR 100", implied_price >= 99.0,
          f"implied_price={implied_price:.2f}")
else:
    check("T30: Price floor at EUR 100", False, "no patients")


print(f"\n{'='*40}")
print(f"PASS: {PASS}  |  FAIL: {FAIL}")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print(f"{FAIL} TEST(S) FAILED")
    sys.exit(1)
