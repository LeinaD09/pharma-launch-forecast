"""
Rigorous Quality Test Suite for Eliquis Patent-Expiry Forecast Engine
=====================================================================

Tests:
  PART 1 - Code & Calculations
    T1: Engine executes without error (both perspectives)
    T2: DataFrame schema correctness (columns, dtypes, no NaN in critical cols)
    T3: Revenue = TRx * Price identity checks
    T4: Cumulative sums are monotonically increasing
    T5: Profit chain: Revenue - COGS = Gross, Gross - SGA - Fixed - Launch = Operating
    T6: Volume decomposition: organic + aut_idem + tender = my_trx
    T7: No negative volumes or negative prices
    T8: Aut-idem curve correctness (unit test)
    T9: Erosion curve correctness (unit test)
    T10: Logistic curve correctness (unit test)
    T11: Tender boost correctness (unit test)

  PART 2 - Consistency & Coherence
    T12: Originator share monotonically decreasing post-LOE
    T13: Generic share monotonically increasing (with tolerance for rounding)
    T14: Originator floor_share is respected
    T15: Aut-idem rate respects timeline (0 before ramp, peak after full_months)
    T16: Revenue-at-risk = counterfactual - actual (non-negative)
    T17: KPI cross-validation (KPIs match DataFrame aggregates)
    T18: Market size consistency between originator & generic perspectives
    T19: Cross-file column consistency (engine columns used in app/excel)
    T20: Scenario comparison uses fresh defaults pattern check
    T21: Dead parameter detection
    T22: Authorized Generic logic check
    T23: Tender Kassen GKV shares sum check
    T24: market_data.py crash test

Run: python tests/test_eliquis_quality.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import traceback
import inspect
import ast

from models.forecast_engine import (
    OriginatorParams, GenericParams,
    forecast_originator, forecast_generic,
    calculate_kpis_originator, calculate_kpis_generic,
    _logistic_curve, _erosion_curve, _aut_idem_curve, _tender_share_of_volume,
)

PASS = 0
FAIL = 0
WARN = 0
results = []

def record(test_id, name, status, detail=""):
    global PASS, FAIL, WARN
    tag = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}[status]
    if status == "PASS":
        PASS += 1
    elif status == "FAIL":
        FAIL += 1
    else:
        WARN += 1
    results.append((test_id, name, tag, detail))
    marker = {"PASS": "+", "FAIL": "X", "WARN": "!"}[status]
    print(f"  [{marker}] {test_id} {name}: {detail}" if detail else f"  [{marker}] {test_id} {name}")


# ═══════════════════════════════════════════════════════════════════════
# Setup: generate DataFrames
# ═══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("ELIQUIS FORECAST ENGINE -- Rigorous Quality Test")
print("=" * 70)
print()

try:
    o_params = OriginatorParams()
    df_o = forecast_originator(o_params, forecast_months=60)
    kpis_o = calculate_kpis_originator(df_o)
    originator_ok = True
except Exception as e:
    originator_ok = False
    orig_err = str(e)

try:
    g_params = GenericParams()
    df_g = forecast_generic(g_params, forecast_months=60)
    kpis_g = calculate_kpis_generic(df_g)
    generic_ok = True
except Exception as e:
    generic_ok = False
    gen_err = str(e)

# ═══════════════════════════════════════════════════════════════════════
# PART 1: CODE & CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════
print("PART 1: CODE & BERECHNUNGEN")
print("-" * 40)

# --- T1: Execution ---
if originator_ok:
    record("T1a", "forecast_originator() ausfuehrbar", "PASS", f"{len(df_o)} Zeilen")
else:
    record("T1a", "forecast_originator() ausfuehrbar", "FAIL", orig_err)

if generic_ok:
    record("T1b", "forecast_generic() ausfuehrbar", "PASS", f"{len(df_g)} Zeilen")
else:
    record("T1b", "forecast_generic() ausfuehrbar", "FAIL", gen_err)

if not (originator_ok and generic_ok):
    print("\nKritischer Fehler: Engine kann nicht ausgefuehrt werden. Abbruch.")
    sys.exit(1)

# --- T2: Schema ---
expected_o_cols = {"date", "month", "months_since_loe", "is_post_loe", "total_market_trx",
                   "originator_trx", "originator_share", "originator_price", "originator_revenue",
                   "generic_segment_trx", "generic_segment_share", "aut_idem_rate",
                   "counterfactual_revenue", "revenue_at_risk", "cumulative_revenue_at_risk",
                   "ag_trx", "ag_share_current", "ag_discount_current", "ag_revenue",
                   "total_originator_revenue"}
missing_o = expected_o_cols - set(df_o.columns)
if not missing_o:
    record("T2a", "Originator Schema vollstaendig", "PASS", f"{len(df_o.columns)} Spalten")
else:
    record("T2a", "Originator Schema vollstaendig", "FAIL", f"Fehlend: {missing_o}")

expected_g_cols = {"date", "month", "months_since_loe", "months_since_launch", "is_launched",
                   "total_market_trx", "total_generic_share", "organic_trx", "aut_idem_trx",
                   "tender_trx", "my_trx", "my_share", "aut_idem_rate", "my_price", "my_revenue",
                   "cogs", "gross_profit", "sga", "fixed_costs", "launch_cost", "operating_profit",
                   "cumulative_revenue", "cumulative_profit", "breakeven_reached"}
missing_g = expected_g_cols - set(df_g.columns)
if not missing_g:
    record("T2b", "Generika Schema vollstaendig", "PASS", f"{len(df_g.columns)} Spalten")
else:
    record("T2b", "Generika Schema vollstaendig", "FAIL", f"Fehlend: {missing_g}")

# NaN check in critical columns
critical_o = ["originator_trx", "originator_share", "originator_revenue", "revenue_at_risk"]
nan_o = {c: int(df_o[c].isna().sum()) for c in critical_o if df_o[c].isna().any()}
if not nan_o:
    record("T2c", "Originator keine NaN in Kern-Spalten", "PASS")
else:
    record("T2c", "Originator keine NaN in Kern-Spalten", "FAIL", str(nan_o))

critical_g = ["my_trx", "my_share", "my_revenue", "operating_profit"]
nan_g = {c: int(df_g[c].isna().sum()) for c in critical_g if df_g[c].isna().any()}
if not nan_g:
    record("T2d", "Generika keine NaN in Kern-Spalten", "PASS")
else:
    record("T2d", "Generika keine NaN in Kern-Spalten", "FAIL", str(nan_g))

# --- T3: Revenue identity ---
# Originator: revenue = trx * price
rev_err_o = (df_o["originator_revenue"] - df_o["originator_trx"] * df_o["originator_price"]).abs().max()
if rev_err_o < 1.0:
    record("T3a", "Orig: Revenue = TRx * Preis", "PASS", f"max err: {rev_err_o:.2f}")
else:
    record("T3a", "Orig: Revenue = TRx * Preis", "FAIL", f"max err: {rev_err_o:.0f}")

# Generic: revenue = trx * price (for launched months only)
launched = df_g[df_g["is_launched"] & (df_g["my_trx"] > 0)]
if len(launched) > 0:
    rev_err_g = (launched["my_revenue"] - launched["my_trx"] * launched["my_price"]).abs().max()
    if rev_err_g < 1.0:
        record("T3b", "Gen: Revenue = TRx * Preis", "PASS", f"max err: {rev_err_g:.2f}")
    else:
        record("T3b", "Gen: Revenue = TRx * Preis", "FAIL", f"max err: {rev_err_g:.0f}")
else:
    record("T3b", "Gen: Revenue = TRx * Preis", "WARN", "Keine launched rows")

# --- T4: Cumulative monotonicity ---
cum_rar = df_o["cumulative_revenue_at_risk"]
if (cum_rar.diff().dropna() >= -0.01).all():
    record("T4a", "Orig: Kum. Revenue-at-Risk monoton steigend", "PASS")
else:
    record("T4a", "Orig: Kum. Revenue-at-Risk monoton steigend", "FAIL")

cum_rev_g = df_g["cumulative_revenue"]
if (cum_rev_g.diff().dropna() >= -0.01).all():
    record("T4b", "Gen: Kum. Umsatz monoton steigend", "PASS")
else:
    record("T4b", "Gen: Kum. Umsatz monoton steigend", "FAIL")

# --- T5: Profit chain ---
# gross_profit = my_revenue - cogs
gp_err = (df_g["gross_profit"] - (df_g["my_revenue"] - df_g["cogs"])).abs().max()
if gp_err < 1.0:
    record("T5a", "Gen: Bruttogewinn = Umsatz - COGS", "PASS", f"max err: {gp_err:.2f}")
else:
    record("T5a", "Gen: Bruttogewinn = Umsatz - COGS", "FAIL", f"max err: {gp_err:.0f}")

# operating_profit = gross_profit - sga - fixed_costs - launch_cost
op_calc = df_g["gross_profit"] - df_g["sga"] - df_g["fixed_costs"] - df_g["launch_cost"]
op_err = (df_g["operating_profit"] - op_calc).abs().max()
if op_err < 1.0:
    record("T5b", "Gen: Op.Profit = Brutto - SGA - Fix - Launch", "PASS", f"max err: {op_err:.2f}")
else:
    record("T5b", "Gen: Op.Profit = Brutto - SGA - Fix - Launch", "FAIL", f"max err: {op_err:.0f}")

# --- T6: Volume decomposition ---
launched_g = df_g[df_g["is_launched"]]
if len(launched_g) > 0:
    vol_sum = launched_g["organic_trx"] + launched_g["aut_idem_trx"] + launched_g["tender_trx"]
    vol_err = (vol_sum - launched_g["my_trx"]).abs().max()
    if vol_err < 2:
        record("T6", "Gen: organic + aut_idem + tender = my_trx", "PASS", f"max err: {vol_err}")
    else:
        record("T6", "Gen: organic + aut_idem + tender = my_trx", "FAIL", f"max err: {vol_err}")

# --- T7: No negatives ---
neg_o_trx = (df_o["originator_trx"] < 0).any()
neg_o_rev = (df_o["originator_revenue"] < 0).any()
neg_o_price = (df_o["originator_price"] < 0).any()
if not (neg_o_trx or neg_o_rev or neg_o_price):
    record("T7a", "Orig: Keine negativen TRx/Umsatz/Preis", "PASS")
else:
    record("T7a", "Orig: Keine negativen TRx/Umsatz/Preis", "FAIL",
           f"TRx neg:{neg_o_trx}, Rev neg:{neg_o_rev}, Price neg:{neg_o_price}")

neg_g_trx = (df_g["my_trx"] < 0).any()
neg_g_rev = (df_g["my_revenue"] < 0).any()
neg_g_price = (df_g[df_g["is_launched"]]["my_price"] < 0).any() if len(launched_g) > 0 else False
if not (neg_g_trx or neg_g_rev or neg_g_price):
    record("T7b", "Gen: Keine negativen TRx/Umsatz/Preis", "PASS")
else:
    record("T7b", "Gen: Keine negativen TRx/Umsatz/Preis", "FAIL",
           f"TRx neg:{neg_g_trx}, Rev neg:{neg_g_rev}, Price neg:{neg_g_price}")

# --- T8: _aut_idem_curve unit test ---
# Before ramp: should be 0
ai_before = _aut_idem_curve(t=3, ramp_months=6, full_months=12, peak_quote=0.75)
# At midpoint: should be partial
ai_mid = _aut_idem_curve(t=9, ramp_months=6, full_months=12, peak_quote=0.75)
# After full: should be peak
ai_after = _aut_idem_curve(t=20, ramp_months=6, full_months=12, peak_quote=0.75)

ai_ok = True
ai_details = []
if ai_before != 0.0:
    ai_ok = False; ai_details.append(f"t=3 erwartet 0.0, got {ai_before}")
if not (0.0 < ai_mid < 0.75):
    ai_ok = False; ai_details.append(f"t=9 erwartet 0<x<0.75, got {ai_mid}")
if ai_after != 0.75:
    ai_ok = False; ai_details.append(f"t=20 erwartet 0.75, got {ai_after}")
# Edge: ramp==full should not divide by zero
try:
    ai_edge = _aut_idem_curve(t=6, ramp_months=6, full_months=6, peak_quote=0.75)
    if ai_edge != 0.75:
        ai_details.append(f"WARN: ramp==full, t=ramp erwartet 0.75, got {ai_edge}")
except ZeroDivisionError:
    ai_ok = False; ai_details.append("ZeroDivisionError bei ramp_months==full_months")

if ai_ok and not ai_details:
    record("T8", "Aut-idem Kurve korrekt", "PASS")
elif ai_ok:
    record("T8", "Aut-idem Kurve korrekt", "WARN", "; ".join(ai_details))
else:
    record("T8", "Aut-idem Kurve korrekt", "FAIL", "; ".join(ai_details))

# --- T9: _erosion_curve unit test ---
t_arr = np.array([0, 18, 100])
erosion = _erosion_curve(t_arr, initial_share=0.42, floor_share=0.12, months_to_floor=18, speed=1.0)
e_ok = True
e_details = []
# At t=0, should be initial
if abs(erosion[0] - 0.42) > 0.001:
    e_ok = False; e_details.append(f"t=0: erwartet ~0.42, got {erosion[0]:.4f}")
# At t=months_to_floor, should be close to floor (within ~5% of range from floor)
if erosion[1] > 0.15:  # should be near 0.12
    e_ok = False; e_details.append(f"t=18: erwartet ~0.12-0.15, got {erosion[1]:.4f}")
# At t=100, should be at floor
if abs(erosion[2] - 0.12) > 0.005:
    e_ok = False; e_details.append(f"t=100: erwartet ~0.12, got {erosion[2]:.4f}")
# Monotonically decreasing
if not (erosion[0] >= erosion[1] >= erosion[2]):
    e_ok = False; e_details.append(f"Nicht monoton fallend: {erosion}")
if e_ok:
    record("T9", "Erosion-Kurve korrekt", "PASS", f"t=0:{erosion[0]:.3f}, t=18:{erosion[1]:.3f}, t=100:{erosion[2]:.3f}")
else:
    record("T9", "Erosion-Kurve korrekt", "FAIL", "; ".join(e_details))

# --- T10: _logistic_curve unit test ---
t_log = np.array([0.0, 5.0, 9.0, 20.0])
logistic = _logistic_curve(t_log, midpoint=9.0, steepness=0.5)
# At midpoint, should be 0.5
if abs(logistic[2] - 0.5) < 0.001:
    record("T10", "Logistic-Kurve: midpoint=0.5", "PASS", f"f(9)={logistic[2]:.4f}")
else:
    record("T10", "Logistic-Kurve: midpoint=0.5", "FAIL", f"f(9)={logistic[2]:.4f}, erwartet 0.5")

# --- T11: _tender_share_of_volume unit test ---
# Before tender_start: share should be 0.0
g_test = GenericParams(tender_enabled=True, tender_start_month=3)
share_before, _ = _tender_share_of_volume(t=1, params=g_test)
if share_before == 0.0:
    record("T11a", "Tender: share=0.0 vor Start", "PASS")
else:
    record("T11a", "Tender: share=0.0 vor Start", "FAIL", f"got {share_before}")

# After tender_start: share should be > 0.0 (reduced by exclusion + multi-award)
share_after, details = _tender_share_of_volume(t=20, params=g_test)
if share_after > 0.0:
    record("T11b", "Tender: share>0.0 nach Start", "PASS", f"share={share_after:.4f}")
else:
    record("T11b", "Tender: share>0.0 nach Start", "FAIL", f"share={share_after}")

# Disabled: should be 0.0
g_no_tender = GenericParams(tender_enabled=False)
share_disabled, _ = _tender_share_of_volume(t=20, params=g_no_tender)
if share_disabled == 0.0:
    record("T11c", "Tender: share=0.0 wenn deaktiviert", "PASS")
else:
    record("T11c", "Tender: share=0.0 wenn deaktiviert", "FAIL", f"got {share_disabled}")

# Higher exclusion rate → lower tender share
g_high_excl = GenericParams(tender_enabled=True, tender_start_month=3,
                            aut_idem_exclusion_rate=0.40, my_tender_share=0.33)
g_low_excl = GenericParams(tender_enabled=True, tender_start_month=3,
                           aut_idem_exclusion_rate=0.05, my_tender_share=0.33)
share_high, _ = _tender_share_of_volume(t=20, params=g_high_excl)
share_low, _ = _tender_share_of_volume(t=20, params=g_low_excl)
if share_low > share_high > 0:
    record("T11d", "Tender: hoehere Exclusion senkt Share", "PASS",
           f"low_excl={share_low:.4f} > high_excl={share_high:.4f}")
else:
    record("T11d", "Tender: hoehere Exclusion senkt Share", "FAIL",
           f"low_excl={share_low:.4f}, high_excl={share_high:.4f}")


# ═══════════════════════════════════════════════════════════════════════
# PART 2: KONSISTENZ & STIMMIGKEIT
# ═══════════════════════════════════════════════════════════════════════
print()
print("PART 2: KONSISTENZ & STIMMIGKEIT")
print("-" * 40)

# --- T12: Originator share decreasing post-LOE ---
post_loe = df_o[df_o["is_post_loe"]].copy()
# Use rolling window to smooth out noise (pre-LOE has random noise)
shares = post_loe["originator_share"].values
# Check general trend (allow minor fluctuations from rounding)
if len(shares) > 2:
    # First month should be > last month
    if shares[0] > shares[-1]:
        # Check no large upward jumps
        max_up_jump = np.max(np.diff(shares))
        if max_up_jump < 0.005:  # Allow tiny rounding jumps
            record("T12", "Orig: Share monoton fallend post-LOE", "PASS",
                   f"Start:{shares[0]:.3f} Ende:{shares[-1]:.3f}")
        else:
            record("T12", "Orig: Share monoton fallend post-LOE", "WARN",
                   f"Max Anstieg: {max_up_jump:.4f}")
    else:
        record("T12", "Orig: Share monoton fallend post-LOE", "FAIL",
               f"Start:{shares[0]:.3f} Ende:{shares[-1]:.3f}")

# --- T13: Generic volume increasing post-launch ---
launched_sorted = df_g[df_g["is_launched"]].sort_values("months_since_loe")
if len(launched_sorted) >= 12:
    first_12 = launched_sorted.head(12)["my_trx"].mean()
    last_12 = launched_sorted.tail(12)["my_trx"].mean()
    if last_12 > first_12:
        record("T13", "Gen: Volumen steigt ueber Zeit", "PASS",
               f"Erste 12M avg: {first_12:,.0f}, Letzte 12M avg: {last_12:,.0f}")
    else:
        record("T13", "Gen: Volumen steigt ueber Zeit", "FAIL",
               f"Erste 12M avg: {first_12:,.0f}, Letzte 12M avg: {last_12:,.0f}")

# --- T14: Floor share respected ---
min_share = post_loe["originator_share"].min()
if min_share >= o_params.floor_share - 0.001:
    record("T14", "Orig: Floor-Share eingehalten", "PASS",
           f"min={min_share:.4f} >= floor={o_params.floor_share}")
else:
    record("T14", "Orig: Floor-Share eingehalten", "FAIL",
           f"min={min_share:.4f} < floor={o_params.floor_share}")

# --- T15: Aut-idem rate timeline ---
# Month 0..ramp_months-1: should be 0
early_ai = df_g[df_g["is_launched"] & (df_g["months_since_launch"] < o_params.aut_idem_ramp_months)]
# Note: Using generic params aut-idem ramp
g_ramp = g_params.aut_idem_ramp_months
g_full = g_params.aut_idem_full_months
early_ai = df_g[df_g["is_launched"]].copy()
early_ai["msl"] = early_ai["months_since_launch"]
before_ramp = early_ai[early_ai["msl"] < g_ramp]
after_full = early_ai[early_ai["msl"] >= g_full]

ai_before_ok = True
if len(before_ramp) > 0:
    max_ai_before = before_ramp["aut_idem_rate"].max()
    if max_ai_before > 0.001:
        ai_before_ok = False

if ai_before_ok:
    record("T15a", "Gen: Aut-idem=0 vor Ramp-Start", "PASS")
else:
    record("T15a", "Gen: Aut-idem=0 vor Ramp-Start", "FAIL",
           f"max aut_idem_rate vor Ramp: {max_ai_before:.4f}")

if len(after_full) > 0:
    # After full_months, should be at peak
    peak_ai = after_full["aut_idem_rate"].iloc[-1]
    if abs(peak_ai - g_params.aut_idem_quote_peak) < 0.01:
        record("T15b", "Gen: Aut-idem bei Peak nach full_months", "PASS",
               f"actual={peak_ai:.3f}, expected={g_params.aut_idem_quote_peak}")
    else:
        record("T15b", "Gen: Aut-idem bei Peak nach full_months", "FAIL",
               f"actual={peak_ai:.3f}, expected={g_params.aut_idem_quote_peak}")

# --- T16: Revenue at risk non-negative ---
if (post_loe["revenue_at_risk"] >= -0.01).all():
    record("T16", "Orig: Revenue-at-Risk >= 0", "PASS")
else:
    min_rar = post_loe["revenue_at_risk"].min()
    record("T16", "Orig: Revenue-at-Risk >= 0", "FAIL", f"min={min_rar:.2f}")

# --- T17: KPI cross-validation ---
# Originator KPIs
year1_post = post_loe.head(12)
kpi_y1_rev = kpis_o["year1_post_loe_revenue"]
calc_y1_rev = year1_post["originator_revenue"].sum()
y1_diff = abs(kpi_y1_rev - calc_y1_rev)
if y1_diff < 1.0:
    record("T17a", "Orig KPI: Year1 Revenue konsistent", "PASS")
else:
    record("T17a", "Orig KPI: Year1 Revenue konsistent", "FAIL", f"diff={y1_diff:.0f}")

kpi_rar_5y = kpis_o["total_revenue_at_risk_5y"]
calc_rar_5y = post_loe["revenue_at_risk"].sum()
rar_diff = abs(kpi_rar_5y - calc_rar_5y)
if rar_diff < 1.0:
    record("T17b", "Orig KPI: Revenue-at-Risk 5J konsistent", "PASS")
else:
    record("T17b", "Orig KPI: Revenue-at-Risk 5J konsistent", "FAIL", f"diff={rar_diff:.0f}")

# Generic KPIs
gen_launched = df_g[df_g["is_launched"]]
kpi_y1_g = kpis_g["year1_revenue"]
calc_y1_g = gen_launched.head(12)["my_revenue"].sum()
y1g_diff = abs(kpi_y1_g - calc_y1_g)
if y1g_diff < 1.0:
    record("T17c", "Gen KPI: Year1 Revenue konsistent", "PASS")
else:
    record("T17c", "Gen KPI: Year1 Revenue konsistent", "FAIL", f"diff={y1g_diff:.0f}")

# Volume decomposition KPI
vol_org_kpi = kpis_g["volume_organic_pct"]
vol_ai_kpi = kpis_g["volume_aut_idem_pct"]
vol_tender_kpi = kpis_g["volume_tender_pct"]
vol_sum = vol_org_kpi + vol_ai_kpi + vol_tender_kpi
if abs(vol_sum - 1.0) < 0.005:
    record("T17d", "Gen KPI: Volumen-Dekomp. summiert ~100%", "PASS", f"sum={vol_sum:.4f}")
else:
    record("T17d", "Gen KPI: Volumen-Dekomp. summiert ~100%", "FAIL",
           f"sum={vol_sum:.4f} (org={vol_org_kpi:.3f}, ai={vol_ai_kpi:.3f}, tender={vol_tender_kpi:.3f})")

# Breakeven KPI
be_kpi = kpis_g.get("breakeven_month")
if be_kpi is not None:
    be_row = df_g[df_g["months_since_loe"] == be_kpi]
    if len(be_row) > 0 and be_row.iloc[0]["cumulative_profit"] > 0:
        record("T17e", "Gen KPI: Breakeven Monat korrekt", "PASS", f"M{be_kpi}")
    else:
        record("T17e", "Gen KPI: Breakeven Monat korrekt", "FAIL",
               f"M{be_kpi} aber cum_profit<=0")
else:
    record("T17e", "Gen KPI: Breakeven Monat korrekt", "WARN", "Kein Breakeven erreicht")

# --- T18: Market size consistency ---
# Both perspectives should use similar total market sizes
o_market_m1 = df_o[df_o["months_since_loe"] == 0]["total_market_trx"].iloc[0]
g_market_m1 = df_g[df_g["months_since_loe"] == 0]["total_market_trx"].iloc[0]

# Originator derives market from baseline_monthly_trx / baseline_market_share
expected_o_market = o_params.baseline_monthly_trx / o_params.baseline_market_share
# But originator includes 12mo growth already (starts 12mo before LOE with compounding)
# Generic starts at LOE with no pre-growth
# Check that at LOE month they are in same ballpark (10% tolerance for growth)
market_ratio = o_market_m1 / g_market_m1
if 0.9 < market_ratio < 1.1:
    record("T18", "Marktgroesse konsistent (Orig vs Gen bei LOE)", "PASS",
           f"Orig={o_market_m1:,.0f}, Gen={g_market_m1:,.0f}, ratio={market_ratio:.3f}")
else:
    record("T18", "Marktgroesse konsistent (Orig vs Gen bei LOE)", "WARN",
           f"Orig={o_market_m1:,.0f}, Gen={g_market_m1:,.0f}, ratio={market_ratio:.3f}")

# --- T19: Cross-file column consistency ---
# Check that columns referenced in app/main.py exist in engine output
app_path = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")
if os.path.exists(app_path):
    with open(app_path, "r", encoding="utf-8") as f:
        app_source = f.read()

    # Extract column references from the app (looking for df["col"] patterns)
    import re
    col_refs = set(re.findall(r'df\["([^"]+)"\]', app_source))

    # Known originator columns used in app
    o_col_refs = {c for c in col_refs if c in expected_o_cols or c.startswith("originator") or c.startswith("ag_") or c in ("date", "month", "months_since_loe", "is_post_loe", "counterfactual_revenue", "revenue_at_risk", "cumulative_revenue_at_risk", "aut_idem_rate", "total_market_trx", "generic_segment_share")}
    g_col_refs = {c for c in col_refs if c in expected_g_cols or c.startswith("my_") or c in ("date", "month", "organic_trx", "aut_idem_trx", "tender_trx", "cumulative_revenue", "cumulative_profit", "aut_idem_rate", "total_generic_share", "operating_profit", "cogs", "sga")}

    missing_in_engine_o = o_col_refs - set(df_o.columns)
    missing_in_engine_g = g_col_refs - set(df_g.columns)

    if not missing_in_engine_o:
        record("T19a", "App->Engine Spalten Orig konsistent", "PASS", f"{len(o_col_refs)} Refs geprueft")
    else:
        record("T19a", "App->Engine Spalten Orig konsistent", "FAIL", f"Fehlend: {missing_in_engine_o}")

    if not missing_in_engine_g:
        record("T19b", "App->Engine Spalten Gen konsistent", "PASS", f"{len(g_col_refs)} Refs geprueft")
    else:
        record("T19b", "App->Engine Spalten Gen konsistent", "FAIL", f"Fehlend: {missing_in_engine_g}")
else:
    record("T19a", "App->Engine Spalten konsistent", "WARN", "app/main.py nicht gefunden")

# --- T20: Scenario comparison pattern check ---
# Check build_excel_model.py for fresh-defaults pattern
excel_path = os.path.join(os.path.dirname(__file__), "..", "exports", "build_excel_model.py")
if os.path.exists(excel_path):
    with open(excel_path, "r", encoding="utf-8") as f:
        excel_source = f.read()

    # Look for OriginatorParams(**sp) or GenericParams(**gp) pattern
    # This is the "L1 pattern" - scenario uses fresh defaults + overrides
    # This means non-overridden params revert to defaults instead of user's sidebar values
    has_fresh_orig = "OriginatorParams(**" in excel_source
    has_fresh_gen = "GenericParams(**" in excel_source

    if has_fresh_orig or has_fresh_gen:
        record("T20", "Excel: Szenario-Vergleich mit frischen Defaults (L1)", "WARN",
               "OriginatorParams(**sp)/GenericParams(**gp) erzeugt frische Defaults statt User-Werte. "
               "Nicht-ueberschriebene Parameter fallen auf Defaults zurueck.")
    else:
        record("T20", "Excel: Szenario-Vergleich nutzt User-Werte", "PASS")
else:
    record("T20", "Excel Szenario-Check", "WARN", "build_excel_model.py nicht gefunden")

# --- T21: Dead parameter detection ---
# Check if all OriginatorParams fields are actually used in forecast_originator
engine_path = os.path.join(os.path.dirname(__file__), "..", "models", "forecast_engine.py")
with open(engine_path, "r", encoding="utf-8") as f:
    engine_source = f.read()

# Get all field names from dataclasses
import dataclasses
orig_fields = {f.name for f in dataclasses.fields(OriginatorParams)}
gen_fields = {f.name for f in dataclasses.fields(GenericParams)}

# Check usage in forecast functions
# Get source of forecast_originator
fo_source = inspect.getsource(forecast_originator)
dead_orig = []
for field_name in orig_fields:
    # Check if params.field_name is referenced in the function
    if f"params.{field_name}" not in fo_source:
        dead_orig.append(field_name)

if not dead_orig:
    record("T21a", "Orig: Keine toten Parameter", "PASS")
else:
    record("T21a", "Orig: Keine toten Parameter", "FAIL",
           f"Unbenutzt in forecast_originator(): {dead_orig}")

fg_source = inspect.getsource(forecast_generic)
# Also check helper functions that receive params (indirect usage)
helpers_source = inspect.getsource(_tender_share_of_volume)
combined_gen_source = fg_source + helpers_source
# my_company_name is a label field, not a calculation parameter -- exclude from check
label_fields = {"my_company_name"}
dead_gen = []
for field_name in gen_fields:
    if field_name in label_fields:
        continue
    if f"params.{field_name}" not in combined_gen_source:
        dead_gen.append(field_name)

if not dead_gen:
    record("T21b", "Gen: Keine toten Parameter", "PASS")
else:
    record("T21b", "Gen: Keine toten Parameter", "FAIL",
           f"Unbenutzt in forecast_generic(): {dead_gen}")

# --- T22: Authorized Generic logic ---
o_ag = OriginatorParams(authorized_generic=True, ag_share_of_generics=0.25, ag_price_discount=0.30,
                        ag_share_decay_speed=0.5, ag_discount_growth_speed=0.5)
df_ag = forecast_originator(o_ag, forecast_months=60)
post_loe_ag = df_ag[df_ag["is_post_loe"]]

# AG should have revenue > 0 post-LOE
ag_rev_sum = post_loe_ag["ag_revenue"].sum()
if ag_rev_sum > 0:
    record("T22a", "AG: Umsatz > 0 post-LOE", "PASS", f"Summe={ag_rev_sum:,.0f}")
else:
    record("T22a", "AG: Umsatz > 0 post-LOE", "FAIL", f"Summe={ag_rev_sum}")

# AG share should decay over time (with decay_speed=0.5)
ag_shares = post_loe_ag["ag_share_current"].values
if len(ag_shares) > 10 and ag_shares[5] > ag_shares[-1]:
    record("T22b", "AG: Share-Decay funktioniert", "PASS",
           f"M5={ag_shares[5]:.3f} -> Ende={ag_shares[-1]:.3f}")
else:
    record("T22b", "AG: Share-Decay funktioniert", "FAIL")

# AG discount should grow
ag_disc = post_loe_ag["ag_discount_current"].values
if len(ag_disc) > 10 and ag_disc[-1] > ag_disc[1]:
    record("T22c", "AG: Discount-Zunahme funktioniert", "PASS",
           f"M1={ag_disc[1]:.3f} -> Ende={ag_disc[-1]:.3f}")
else:
    record("T22c", "AG: Discount-Zunahme funktioniert", "FAIL")

# total_originator_revenue = originator_revenue + ag_revenue
tor_err = (post_loe_ag["total_originator_revenue"] - post_loe_ag["originator_revenue"] - post_loe_ag["ag_revenue"]).abs().max()
if tor_err < 1.0:
    record("T22d", "AG: total_orig_rev = orig_rev + ag_rev", "PASS")
else:
    record("T22d", "AG: total_orig_rev = orig_rev + ag_rev", "FAIL", f"max err: {tor_err:.0f}")

# --- T23: Kassen GKV shares ---
g_default = GenericParams()
total_gkv = sum(k["gkv_share"] for k in g_default.tender_kassen)
# Should be less than 1.0 (not all Kassen are covered)
if total_gkv < 1.0:
    record("T23", "Kassen GKV-Shares < 100%", "PASS", f"Summe={total_gkv:.3f} ({total_gkv*100:.1f}%)")
else:
    record("T23", "Kassen GKV-Shares < 100%", "FAIL", f"Summe={total_gkv:.3f} - ueber 100%!")

# --- T24: market_data.py crash test ---
try:
    from data.market_data import generate_eliquis_market_data
    data = generate_eliquis_market_data()
    record("T24", "market_data.py ausfuehrbar", "PASS")
except ValueError as e:
    record("T24", "market_data.py ausfuehrbar", "FAIL", f"ValueError: {e}")
except Exception as e:
    record("T24", "market_data.py ausfuehrbar", "FAIL", f"{type(e).__name__}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ADDITIONAL CHECKS
# ═══════════════════════════════════════════════════════════════════════
print()
print("ZUSAETZLICHE PRUEFUNGEN")
print("-" * 40)

# T25: Pre-LOE months count (should be 12)
pre_loe = df_o[~df_o["is_post_loe"]]
if len(pre_loe) == 12:
    record("T25", "Orig: 12 Pre-LOE Monate", "PASS")
else:
    record("T25", "Orig: 12 Pre-LOE Monate", "FAIL", f"got {len(pre_loe)}")

# T26: Total rows count
expected_rows_o = 12 + 60  # pre-LOE + forecast
expected_rows_g = 60
if len(df_o) == expected_rows_o:
    record("T26a", "Orig: Zeilenanzahl korrekt", "PASS", f"{len(df_o)} Zeilen")
else:
    record("T26a", "Orig: Zeilenanzahl korrekt", "FAIL", f"erwartet {expected_rows_o}, got {len(df_o)}")

if len(df_g) == expected_rows_g:
    record("T26b", "Gen: Zeilenanzahl korrekt", "PASS", f"{len(df_g)} Zeilen")
else:
    record("T26b", "Gen: Zeilenanzahl korrekt", "FAIL", f"erwartet {expected_rows_g}, got {len(df_g)}")

# T27: Originator generic_segment_share calculation check
# generic_share = (baseline_market_share - share) * 0.85
# This is conceptually odd: the 0.85 factor is unexplained
post_loe_m1 = post_loe.iloc[0]
expected_gen_share = max(0, (o_params.baseline_market_share - post_loe_m1["originator_share"]) * 0.85)
actual_gen_share = post_loe_m1["generic_segment_share"]
diff_gs = abs(expected_gen_share - actual_gen_share)
if diff_gs < 0.001:
    record("T27", "Orig: generic_segment_share Berechnung nachvollziehbar", "WARN",
           "0.85-Faktor reduziert Generika-Share ohne klare Begruendung")
else:
    record("T27", "Orig: generic_segment_share Berechnung", "FAIL",
           f"erwartet {expected_gen_share:.4f}, got {actual_gen_share:.4f}")

# T28: Generic price floor check (my_price >= 20 EUR)
if len(launched_g) > 0:
    min_price = launched_g["my_price"].min()
    if min_price >= 19.99:
        record("T28", "Gen: Preis-Floor >= 20 EUR eingehalten", "PASS", f"min={min_price:.2f}")
    else:
        record("T28", "Gen: Preis-Floor >= 20 EUR eingehalten", "FAIL", f"min={min_price:.2f}")

# T29: Originator counterfactual revenue grows with market
cf = df_o[df_o["is_post_loe"]]["counterfactual_revenue"]
if cf.iloc[-1] > cf.iloc[0]:
    record("T29", "Orig: Counterfactual Revenue steigt (Marktwachstum)", "PASS",
           f"M1={cf.iloc[0]:,.0f} -> Ende={cf.iloc[-1]:,.0f}")
else:
    record("T29", "Orig: Counterfactual Revenue steigt (Marktwachstum)", "FAIL")

# T30: Generic segment capped by segment_peak_share
g_max_share = df_g["my_share"].max()
if g_max_share <= g_params.generic_segment_peak_share + 0.001:
    record("T30", "Gen: my_share <= segment_peak_share", "PASS",
           f"max={g_max_share:.3f}, cap={g_params.generic_segment_peak_share}")
else:
    record("T30", "Gen: my_share <= segment_peak_share", "WARN",
           f"max={g_max_share:.3f} > cap={g_params.generic_segment_peak_share}")


# ═══════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print(f"ERGEBNIS: {PASS} PASS | {FAIL} FAIL | {WARN} WARN")
print("=" * 70)

if FAIL > 0:
    print()
    print("FEHLER:")
    for tid, name, tag, detail in results:
        if tag == "FAIL":
            print(f"  {tid}: {name}")
            if detail:
                print(f"         -> {detail}")

if WARN > 0:
    print()
    print("WARNUNGEN:")
    for tid, name, tag, detail in results:
        if tag == "WARN":
            print(f"  {tid}: {name}")
            if detail:
                print(f"         -> {detail}")

print()
sys.exit(1 if FAIL > 0 else 0)
