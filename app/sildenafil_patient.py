"""
Pharma Launch Forecast – Use Case 4b: Sildenafil Patient-Based Model
=====================================================================
Patient-flow model: Epidemiology → Patients → Tablets → Revenue
"""

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import models.sildenafil_patient_engine as _engine_mod
importlib.reload(_engine_mod)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models.sildenafil_patient_engine import (
    SildenafilPatientParams, ChannelParams,
    forecast_sildenafil_patient, calculate_kpis_patient,
)


BLUE = "#1e3a5f"
TEAL = "#0d9488"
AMBER = "#d97706"
GREEN = "#27ae60"
RED = "#c0392b"
PURPLE = "#7c3aed"
PINK = "#db2777"


def show():
    """Render the patient-based Sildenafil forecast page."""

    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        .kpi-row { display: flex; gap: 8px; margin-bottom: 6px; width: 100%; box-sizing: border-box; }
        .kpi-card, .kpi-card-teal, .kpi-card-amber,
        .kpi-card-green, .kpi-card-red, .kpi-card-purple {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px; padding: 10px 8px;
            color: #1e293b;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            flex: 1; min-width: 0;
        }
        .kpi-value { font-size: 18px; font-weight: 700; margin: 2px 0; line-height: 1.2; color: #0f172a; }
        .kpi-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-sublabel { font-size: 9px; color: #94a3b8; margin-top: 1px; }
        div[data-testid="stSidebar"] {
            background-color: #f8fafc;
            min-width: 280px !important; max-width: 320px !important; width: 300px !important;
        }
        div[data-testid="stSidebar"] .stMarkdown p { font-size: 13px; }
        div[data-testid="stSidebar"] label { font-size: 13px !important; }
        .plot-container { margin-top: -10px; }
        .stTabs [data-baseweb="tab-list"] {
            background: #f8fafc; border: 1px solid #e5e7eb;
            border-radius: 8px; padding: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06); gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px; padding: 8px 16px;
            font-weight: 500; color: #64748b;
        }
        .stTabs [aria-selected="true"] {
            background: #ffffff !important; border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
            color: #0f172a !important; font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # ===================================================================
    # SIDEBAR – Patient-Based Parameters
    # ===================================================================
    with st.sidebar:
        st.markdown("#### Sildenafil Patient-Based Model")
        st.markdown("*Epidemiologie → Patienten → Tabletten → Umsatz*")

        scenario = st.selectbox("Szenario", [
            "Base Case", "Optimistisch (BMG erzwingt Switch)",
            "Konservativ (SVA-Auflagen)"
        ], key="silpat_scenario")

        if scenario == "Optimistisch (BMG erzwingt Switch)":
            _d = dict(addressable=19, ramp=12, mktg=750_000,
                      new_patient=70, rx_decline=5, brand_share=35,
                      tablets_per_pat=4.5)
        elif scenario == "Konservativ (SVA-Auflagen)":
            _d = dict(addressable=8, ramp=24, mktg=300_000,
                      new_patient=55, rx_decline=12, brand_share=20,
                      tablets_per_pat=3.5)
        else:
            _d = dict(addressable=15, ramp=18, mktg=500_000,
                      new_patient=63, rx_decline=8, brand_share=25,
                      tablets_per_pat=4.0)

        _prev = st.session_state.get("_silpat_prev_scenario")
        if _prev is not None and _prev != scenario:
            for _k in ["silpat_addr", "silpat_ramp", "silpat_np",
                        "silpat_rxdec", "silpat_brand", "silpat_tpp"]:
                st.session_state.pop(_k, None)
            st.session_state["_silpat_prev_scenario"] = scenario
            st.rerun()
        st.session_state["_silpat_prev_scenario"] = scenario

        st.markdown("---")

        # --- Epidemiology & Patient Pool ---
        with st.expander("Patientenpool (Epidemiologie)", expanded=True):
            ed_prevalence = st.number_input(
                "ED-Praevalenz (Maenner DE)", 1_000_000, 10_000_000,
                5_000_000, 100_000, key="silpat_prev")
            treatment_rate = st.slider(
                "Aktuelle Therapiequote (%)", 10, 50, 30, key="silpat_tr") / 100

            untreated = ed_prevalence * (1 - treatment_rate)
            st.caption(f"→ Unbehandelt: **{untreated:,.0f}** Maenner")

            addressable = st.slider(
                "Erreichbare Unbehandelte (%)", 5, 30,
                _d["addressable"], key="silpat_addr") / 100
            addressable_patients = int(untreated * addressable)
            st.caption(f"→ Adressierbarer Pool: **{addressable_patients:,.0f}** Patienten")

            tablets_per_pat = st.slider(
                "Tabletten/Patient/Monat", 1.0, 8.0,
                _d["tablets_per_pat"], 0.5, key="silpat_tpp")

            otc_peak_computed = addressable_patients * tablets_per_pat
            st.success(f"**OTC Peak: {otc_peak_computed:,.0f} Tabl./Mon.**")
            st.caption("(berechnet aus Patientenpool × Frequenz)")

        # --- OTC Parameters ---
        with st.expander("OTC-Markt", expanded=False):
            otc_price = st.number_input(
                "OTC Preis/Tablette (EUR)", 2.0, 15.0, 5.99, 0.5,
                key="silpat_otcp")
            uptake_ramp = st.slider(
                "Monate bis Peak-Uptake", 6, 36, _d["ramp"],
                key="silpat_ramp")
            new_patient = st.slider(
                "Neue Patienten (% OTC-Vol.)", 30, 80,
                _d["new_patient"], key="silpat_np") / 100
            st.markdown("---")
            st.caption("Tadalafil-Migration")
            tada_patients = st.number_input(
                "Tadalafil Rx Patienten/Mon.", 50_000, 500_000,
                120_000, 10_000, key="silpat_tada")
            tada_switch = st.slider(
                "Migration zu Sildenafil OTC (%)", 0, 30, 12,
                key="silpat_tadas") / 100

        # --- Rx Market ---
        with st.expander("Rx-Markt", expanded=False):
            rx_patients = st.number_input(
                "Sildenafil Rx Patienten/Mon.", 50_000, 500_000,
                217_000, 10_000, key="silpat_rxpat")
            rx_tablets_per_pat = st.slider(
                "Rx Tabl./Patient/Mon.", 1.0, 8.0, 4.0, 0.5,
                key="silpat_rxtpp")
            rx_price_brand = st.number_input(
                "Viagra Preis/Tabl. (EUR)", 5.0, 25.0, 11.19, 0.5,
                key="silpat_rxbrand")
            rx_price_generic = st.number_input(
                "Generika Preis/Tabl. (EUR)", 0.50, 5.0, 1.50, 0.1,
                key="silpat_rxgen")
            rx_brand_share = st.slider(
                "Viagra Markenanteil Rx (%)", 2, 25, 10,
                key="silpat_rxbs") / 100
            rx_decline = st.slider(
                "Rx-Rueckgang durch OTC (%)", 0, 30,
                _d["rx_decline"], key="silpat_rxdec") / 100

        # --- Brand vs. Generic ---
        with st.expander("OTC Marke vs. Generika", expanded=False):
            brand_share = st.slider(
                "Viagra Connect Anteil OTC (%)", 15, 70,
                _d["brand_share"], key="silpat_brand") / 100
            brand_erosion = st.slider(
                "Markenanteil-Erosion p.a. (Pp.)", 0, 10, 3,
                key="silpat_berosion") / 100
            brand_premium = st.slider(
                "Preispremium Marke (x)", 1.0, 3.0, 1.8, 0.1,
                key="silpat_bprem")

        # --- Channels ---
        with st.expander("Stationaer vs. Online", expanded=False):
            st.caption("Apothekenpflichtig: nur Apotheken-Kanaele")
            ch_apo = st.slider(
                "Stationaere Apotheke (%)", 20, 80, 55,
                key="silpat_chapo")
            ch_online = 100 - ch_apo
            st.markdown(f"*Online-Apotheke: {ch_online}%*")
            online_growth = st.slider(
                "Online-Wachstum p.a. (Pp.)", 0, 10, 2,
                key="silpat_og") / 100

    # --- Build params --------------------------------------------------
    channels = [
        ChannelParams(name="Stationaere Apotheke", share_of_otc=ch_apo / 100,
                      share_trend_annual=-online_growth, margin_pct=0.42,
                      distribution_cost_pct=0.06, discretion_factor=0.70),
        ChannelParams(name="Online-Apotheke", share_of_otc=ch_online / 100,
                      share_trend_annual=online_growth, margin_pct=0.30,
                      distribution_cost_pct=0.10, discretion_factor=1.0),
    ]

    params = SildenafilPatientParams(
        ed_prevalence_men=ed_prevalence,
        treatment_rate=treatment_rate,
        addressable_pct=addressable,
        uptake_ramp_months=uptake_ramp,
        tablets_per_patient_per_month=tablets_per_pat,
        new_patient_share=new_patient,
        rx_patients_monthly=rx_patients,
        rx_tablets_per_patient=rx_tablets_per_pat,
        rx_price_brand=rx_price_brand,
        rx_price_generic=rx_price_generic,
        rx_brand_share=rx_brand_share,
        rx_decline_rate=rx_decline,
        otc_price_per_tablet=otc_price,
        tadalafil_patients_monthly=tada_patients,
        tadalafil_switch_pct=tada_switch,
        brand_otc_share=brand_share,
        brand_otc_share_trend=-brand_erosion,
        brand_price_premium=brand_premium,
        channels=channels,
        marketing_monthly_eur=_d["mktg"],
    )

    df = forecast_sildenafil_patient(params)
    kpis = calculate_kpis_patient(df)

    # ===================================================================
    # HEADER
    # ===================================================================
    st.markdown("")

    co_rev = kpis.get("crossover_month")
    co_tabs = kpis.get("crossover_month_tablets")
    co_text = f"M{co_rev} / M{co_tabs}" if co_rev and co_tabs else (
        f"Monat {co_rev}" if co_rev else "–"
    )

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card-teal">
            <div class="kpi-label">OTC Umsatz M12</div>
            <div class="kpi-value">EUR {kpis['year1_otc_revenue']/1e6:.1f}M</div>
            <div class="kpi-sublabel">Herstellerumsatz</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Gesamtumsatz M12</div>
            <div class="kpi-value">EUR {kpis['year1_total_revenue']/1e6:.1f}M</div>
            <div class="kpi-sublabel">Rx + OTC kumuliert</div>
        </div>
        <div class="kpi-card-amber">
            <div class="kpi-label">OTC > Rx ab</div>
            <div class="kpi-value">{co_text}</div>
            <div class="kpi-sublabel">Umsatz / Tabletten</div>
        </div>
        <div class="kpi-card-green">
            <div class="kpi-label">Gewinn 5J</div>
            <div class="kpi-value">EUR {kpis['total_5y_profit']/1e6:.0f}M</div>
            <div class="kpi-sublabel">nach Marketing & COGS</div>
        </div>
    </div>
    <div class="kpi-row">
        <div class="kpi-card-purple">
            <div class="kpi-label">OTC Patienten Peak</div>
            <div class="kpi-value">{kpis['peak_otc_patients']:,.0f}</div>
            <div class="kpi-sublabel">aktive OTC-Kaeufer</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Neue OTC-Patienten</div>
            <div class="kpi-value">{kpis['newly_treated_total']:,.0f}</div>
            <div class="kpi-sublabel">aktiv, vorher nie beim Arzt</div>
        </div>
        <div class="kpi-card-red">
            <div class="kpi-label">Rx-Rueckgang</div>
            <div class="kpi-value">{kpis['rx_decline_total']:.0%}</div>
            <div class="kpi-sublabel">ueber 5 Jahre</div>
        </div>
        <div class="kpi-card-green">
            <div class="kpi-label">Therapiequote ED 5J</div>
            <div class="kpi-value">{kpis['treatment_rate_final']:.0%}</div>
            <div class="kpi-sublabel">vorher: {params.treatment_rate:.0%}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ===================================================================
    # CHARTS – 4 Tabs
    # ===================================================================

    tab1, tab2, tab3, tab4 = st.tabs([
        "Patienten & Therapieluecke", "Rx vs. OTC",
        "Kanal & Marke", "Profitabilitaet"
    ])

    # --- Tab 1: Patienten & Therapielücke (merged funnel + treatment gap)
    with tab1:
        # Row 1: Uptake + Herkunft
        col_p1, col_p2 = st.columns(2)

        with col_p1:
            fig_funnel = go.Figure()
            fig_funnel.add_trace(go.Scatter(
                x=df["month"], y=df["otc_patients_active"],
                name="OTC Patienten (aktiv)", fill="tozeroy",
                line=dict(color=TEAL, width=2.5),
                fillcolor="rgba(13,148,136,0.15)",
            ))
            fig_funnel.add_trace(go.Scatter(
                x=df["month"], y=df["otc_new_patients"],
                name="davon: Neue Patienten",
                line=dict(color=GREEN, width=2, dash="dot"),
            ))
            fig_funnel.add_trace(go.Scatter(
                x=df["month"], y=df["otc_rxmigration_patients"],
                name="davon: Rx-Migration",
                line=dict(color=BLUE, width=2, dash="dot"),
            ))
            fig_funnel.add_trace(go.Scatter(
                x=df["month"], y=df["tada_migration_patients"],
                name="Tadalafil-Migration",
                line=dict(color=PURPLE, width=1.5, dash="dash"),
            ))
            fig_funnel.add_hline(
                y=kpis["addressable_patients"], line_dash="dash",
                line_color="#999",
                annotation_text=f"Adressierbarer Pool: {kpis['addressable_patients']:,.0f}",
            )
            fig_funnel.update_layout(
                title="Patienten-Uptake (aktive OTC-Kaeufer)",
                xaxis_title="Monate nach Switch",
                yaxis_title="Patienten",
                yaxis_tickformat=",", height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_funnel, width="stretch")

        with col_p2:
            fig_herkunft = go.Figure()
            fig_herkunft.add_trace(go.Scatter(
                x=df["month"], y=df["otc_from_new_patients"],
                name="Neue Patienten (nie Arzt)", stackgroup="one",
                line=dict(color=GREEN),
            ))
            fig_herkunft.add_trace(go.Scatter(
                x=df["month"], y=df["otc_from_rx_migration"],
                name="Rx-Migration (Sildenafil)", stackgroup="one",
                line=dict(color=BLUE),
            ))
            fig_herkunft.add_trace(go.Scatter(
                x=df["month"], y=df["otc_from_tadalafil"],
                name="Tadalafil-Migration", stackgroup="one",
                line=dict(color=PURPLE),
            ))
            fig_herkunft.update_layout(
                title="OTC-Volumen Herkunft (Tabletten)",
                xaxis_title="Monate nach Switch", yaxis_title="Tabletten/Monat",
                yaxis_tickformat=",", height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_herkunft, width="stretch")

        # Row 2: Treatment Gap + Therapiequote
        treated_monthly = df["treatment_rate_effective"] * params.ed_prevalence_men
        untreated_monthly = params.ed_prevalence_men - treated_monthly

        col_tg1, col_tg2 = st.columns(2)

        with col_tg1:
            fig_tg_abs = go.Figure()
            fig_tg_abs.add_trace(go.Bar(
                x=df["month"], y=treated_monthly,
                name="Behandelt", marker_color=GREEN,
            ))
            fig_tg_abs.add_trace(go.Bar(
                x=df["month"], y=untreated_monthly,
                name="Unbehandelt", marker_color="#e5e7eb",
            ))
            fig_tg_abs.update_layout(
                barmode="stack",
                title="ED-Patienten: Behandelt vs. Unbehandelt",
                xaxis_title="Monate nach Switch", yaxis_title="Maenner",
                yaxis_tickformat=",", height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_tg_abs, width="stretch")

        with col_tg2:
            fig_tg_rate = go.Figure()
            fig_tg_rate.add_trace(go.Scatter(
                x=df["month"], y=df["treatment_rate_effective"],
                name="Therapiequote",
                line=dict(color=GREEN, width=3),
                fill="tozeroy", fillcolor="rgba(39,174,96,0.1)",
            ))
            fig_tg_rate.add_hline(y=params.treatment_rate, line_dash="dash",
                                  line_color="#999",
                                  annotation_text=f"Vor Switch ({params.treatment_rate:.0%})")
            fig_tg_rate.update_layout(
                title="Therapiequote ueber Zeit",
                xaxis_title="Monate nach Switch", yaxis_title="Therapiequote",
                yaxis_tickformat=".0%", height=380,
            )
            st.plotly_chart(fig_tg_rate, width="stretch")

        # Funnel summary table
        st.markdown("#### Patienten-Funnel")
        funnel_data = {
            "Stufe": [
                "ED-Praevalenz (Maenner DE)",
                "Aktuell behandelt",
                "Unbehandelt (Treatment Gap)",
                "Adressierbarer OTC-Pool",
                "OTC Patienten M12",
                "OTC Patienten M60 (Peak)",
            ],
            "Patienten": [
                f"{params.ed_prevalence_men:,.0f}",
                f"{params.ed_prevalence_men * params.treatment_rate:,.0f}",
                f"{untreated:,.0f}",
                f"{addressable_patients:,.0f}",
                f"{int(df[df['month']==12]['otc_patients_active'].iloc[0]) if len(df[df['month']==12]) > 0 else 0:,}",
                f"{kpis['peak_otc_patients']:,}",
            ],
            "Anteil": [
                "100%",
                f"{params.treatment_rate:.0%}",
                f"{1-params.treatment_rate:.0%}",
                f"{addressable:.0%} der Unbehandelten",
                "",
                "",
            ],
        }
        st.dataframe(pd.DataFrame(funnel_data), hide_index=True, width=700)

        st.info(
            "**Konsistenz-Check:** Die Therapiequote wird aus den tatsaechlich "
            "aktiven OTC-Neupatienten abgeleitet (Anteil neue Patienten an "
            "aktiven OTC-Kaeufern), nicht unabhaengig berechnet. "
            f"Peak: **{kpis['newly_treated_total']:,.0f}** aktive Neupatienten "
            f"→ Therapiequote steigt von {params.treatment_rate:.0%} "
            f"auf {kpis['treatment_rate_final']:.0%}."
        )

    # --- Tab 2: Rx vs. OTC (with crossover markers) -------------------
    with tab2:
        fig_rx = go.Figure()
        fig_rx.add_trace(go.Scatter(
            x=df["month"], y=df["rx_tablets"], name="Rx Tabletten",
            line=dict(color=BLUE, width=2.5),
        ))
        fig_rx.add_trace(go.Scatter(
            x=df["month"], y=df["otc_tablets"], name="OTC Tabletten",
            line=dict(color=TEAL, width=2.5),
        ))
        if co_tabs:
            fig_rx.add_vline(x=co_tabs, line_dash="dot", line_color=AMBER,
                             annotation_text=f"OTC > Rx (M{co_tabs})")
        fig_rx.add_hline(
            y=kpis["otc_peak_computed"], line_dash="dash", line_color=TEAL,
            annotation_text=f"Berechneter Peak: {kpis['otc_peak_computed']:,.0f}",
        )
        fig_rx.update_layout(
            title="Rx vs. OTC Tabletten/Monat",
            xaxis_title="Monate nach Switch", yaxis_title="Tabletten",
            yaxis_tickformat=",", height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_rx, width="stretch")

        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=df["month"], y=df["rx_revenue"], name="Rx Umsatz",
            marker_color="#93c5fd",
        ))
        fig_rev.add_trace(go.Bar(
            x=df["month"], y=df["otc_manufacturer_revenue"],
            name="OTC Umsatz (Hersteller)", marker_color="#5eead4",
        ))
        if co_rev:
            fig_rev.add_vline(x=co_rev, line_dash="dot", line_color=AMBER,
                              annotation_text=f"OTC > Rx (M{co_rev})")
        fig_rev.update_layout(
            barmode="stack",
            title="Rx vs. OTC Umsatz/Monat",
            xaxis_title="Monate nach Switch", yaxis_title="EUR",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_rev, width="stretch")

    # --- Tab 3: Kanal & Marke (2×2 layout) ----------------------------
    with tab3:
        col_km1, col_km2 = st.columns(2)

        # Top-left: Channel volume (stacked area)
        with col_km1:
            fig_ch_vol = go.Figure()
            fig_ch_vol.add_trace(go.Scatter(
                x=df["month"], y=df["ch_apotheke_tablets"],
                name="Stationaere Apotheke", stackgroup="one",
                line=dict(color=BLUE),
            ))
            fig_ch_vol.add_trace(go.Scatter(
                x=df["month"], y=df["ch_online_tablets"],
                name="Online-Apotheke", stackgroup="one",
                line=dict(color=TEAL),
            ))
            fig_ch_vol.update_layout(
                title="OTC-Volumen nach Kanal",
                xaxis_title="Monate", yaxis_title="Tabletten",
                yaxis_tickformat=",", height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_ch_vol, width="stretch")

        # Top-right: Channel share (lines)
        with col_km2:
            fig_ch_share = go.Figure()
            fig_ch_share.add_trace(go.Scatter(
                x=df["month"], y=df["ch_apotheke_share"],
                name="Stationaer", line=dict(color=BLUE, width=2),
            ))
            fig_ch_share.add_trace(go.Scatter(
                x=df["month"], y=df["ch_online_share"],
                name="Online", line=dict(color=TEAL, width=2),
            ))
            fig_ch_share.update_layout(
                title="Kanal-Anteile",
                xaxis_title="Monate", yaxis_title="Anteil",
                yaxis_tickformat=".0%", height=380,
            )
            st.plotly_chart(fig_ch_share, width="stretch")

        col_km3, col_km4 = st.columns(2)

        # Bottom-left: Brand vs Generic volume (stacked area)
        with col_km3:
            fig_bg_vol = go.Figure()
            fig_bg_vol.add_trace(go.Scatter(
                x=df["month"], y=df["otc_brand_tablets"],
                name="Viagra Connect (Marke)", stackgroup="one",
                line=dict(color="#1e40af"),
            ))
            fig_bg_vol.add_trace(go.Scatter(
                x=df["month"], y=df["otc_generic_tablets"],
                name="Generika OTC", stackgroup="one",
                line=dict(color="#94a3b8"),
            ))
            fig_bg_vol.update_layout(
                title="OTC-Volumen: Marke vs. Generika",
                xaxis_title="Monate", yaxis_title="Tabletten",
                yaxis_tickformat=",", height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_bg_vol, width="stretch")

        # Bottom-right: Brand erosion (fill line)
        with col_km4:
            fig_brand = go.Figure()
            fig_brand.add_trace(go.Scatter(
                x=df["month"], y=df["otc_brand_share"],
                name="Viagra Connect Anteil",
                line=dict(color=PINK, width=3),
                fill="tozeroy", fillcolor="rgba(219,39,119,0.08)",
            ))
            fig_brand.update_layout(
                title="Viagra Markenanteil-Erosion",
                xaxis_title="Monate", yaxis_title="Anteil",
                yaxis_tickformat=".0%", height=380,
                yaxis_range=[0, 0.7],
            )
            st.plotly_chart(fig_brand, width="stretch")

        # Channel revenue (full width)
        fig_ch_rev = go.Figure()
        fig_ch_rev.add_trace(go.Bar(
            x=df["month"], y=df["ch_apotheke_revenue"],
            name="Apotheke", marker_color=BLUE,
        ))
        fig_ch_rev.add_trace(go.Bar(
            x=df["month"], y=df["ch_online_revenue"],
            name="Online", marker_color=TEAL,
        ))
        fig_ch_rev.update_layout(
            barmode="stack",
            title="OTC-Herstellerumsatz nach Kanal",
            xaxis_title="Monate", yaxis_title="EUR",
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_ch_rev, width="stretch")

    # --- Tab 4: Profitabilität ----------------------------------------
    with tab4:
        # Row 1: Rx vs. OTC revenue + Channel profitability
        col_pr1, col_pr2 = st.columns(2)

        with col_pr1:
            fig_rxotc_gp = go.Figure()
            fig_rxotc_gp.add_trace(go.Bar(
                x=df["month"], y=df["rx_gross_profit"],
                name="Rx Bruttomarge", marker_color="#93c5fd",
            ))
            fig_rxotc_gp.add_trace(go.Bar(
                x=df["month"], y=df["otc_gross_profit"],
                name="OTC Bruttomarge", marker_color="#5eead4",
            ))
            co_rev = kpis.get("crossover_month")
            if co_rev:
                fig_rxotc_gp.add_vline(
                    x=co_rev, line_dash="dot", line_color=AMBER,
                    annotation_text=f"OTC > Rx (M{co_rev})",
                )
            fig_rxotc_gp.update_layout(
                barmode="group",
                title="Bruttomarge: Rx vs. OTC (nach COGS)",
                xaxis_title="Monate", yaxis_title="EUR",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_rxotc_gp, width="stretch")

        with col_pr2:
            # Channel profitability: gross profit per channel
            # Shows the margin advantage of online over time
            cogs_pct = params.cogs_pct
            fig_ch_profit = go.Figure()
            fig_ch_profit.add_trace(go.Bar(
                x=df["month"], y=df["ch_apotheke_revenue"] * (1 - cogs_pct),
                name="Stationaer (Hst. 52%)", marker_color=BLUE,
            ))
            fig_ch_profit.add_trace(go.Bar(
                x=df["month"], y=df["ch_online_revenue"] * (1 - cogs_pct),
                name="Online (Hst. 60%)", marker_color=TEAL,
            ))
            fig_ch_profit.update_layout(
                barmode="group",
                title="Bruttogewinn nach Kanal (nach COGS)",
                xaxis_title="Monate", yaxis_title="EUR",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_ch_profit, width="stretch")

        # Row 2: Cumulative + Monthly profit
        col_pr3, col_pr4 = st.columns(2)

        with col_pr3:
            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(
                x=df["month"], y=df["cumulative_total_revenue"],
                name="Kum. Umsatz", line=dict(color=BLUE, width=2.5),
            ))
            fig_cum.add_trace(go.Scatter(
                x=df["month"], y=df["cumulative_profit"],
                name="Kum. Gewinn", line=dict(color=GREEN, width=2.5),
            ))
            fig_cum.add_trace(go.Scatter(
                x=df["month"], y=df["cumulative_marketing"],
                name="Kum. Marketing", line=dict(color=RED, width=1.5, dash="dot"),
            ))
            fig_cum.update_layout(
                title="Kumulierter Umsatz, Gewinn & Marketing",
                xaxis_title="Monate", yaxis_title="EUR", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_cum, width="stretch")

        with col_pr4:
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Bar(
                x=df["month"], y=df["gross_profit"],
                name="Bruttogewinn",
                marker_color=[GREEN if v >= 0 else RED for v in df["gross_profit"]],
            ))
            fig_profit.add_trace(go.Scatter(
                x=df["month"], y=df["marketing_spend"],
                name="Marketing", line=dict(color=RED, width=1.5, dash="dot"),
            ))
            fig_profit.update_layout(
                title="Monatl. Bruttogewinn vs. Marketing",
                xaxis_title="Monate", yaxis_title="EUR", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_profit, width="stretch")

    # ===================================================================
    # SCENARIO COMPARISON
    # ===================================================================
    st.markdown("---")
    st.markdown("### Szenario-Vergleich")

    scenarios = {
        "Konservativ": {"addressable_pct": 0.08, "uptake_ramp_months": 24,
                        "marketing_monthly_eur": 300_000, "new_patient_share": 0.55,
                        "rx_decline_rate": 0.12, "brand_otc_share": 0.20,
                        "tablets_per_patient_per_month": 3.5},
        "Base Case": {},
        "Optimistisch": {"addressable_pct": 0.19, "uptake_ramp_months": 12,
                         "marketing_monthly_eur": 750_000, "new_patient_share": 0.70,
                         "rx_decline_rate": 0.05, "brand_otc_share": 0.35,
                         "tablets_per_patient_per_month": 4.5},
    }

    comp_rows = []
    for sn, overrides in scenarios.items():
        p = SildenafilPatientParams(**overrides)
        k = calculate_kpis_patient(forecast_sildenafil_patient(p))
        comp_rows.append({
            "Szenario": sn,
            "OTC Peak Pat.": f"{k['peak_otc_patients']:,.0f}",
            "OTC Umsatz M12": f"EUR {k['year1_otc_revenue']/1e6:.0f}M",
            "Gesamt M12": f"EUR {k['year1_total_revenue']/1e6:.0f}M",
            "Gewinn 5J": f"EUR {k['total_5y_profit']/1e6:.0f}M",
            "Neue Pat. (Peak)": f"{k['newly_treated_total']:,.0f}",
            "Therapiequote": f"{k['treatment_rate_final']:.0%}",
        })

    st.dataframe(pd.DataFrame(comp_rows).set_index("Szenario"), width=900)

    # ===================================================================
    # METHODOLOGY
    # ===================================================================
    with st.expander("Methodik & Datenquellen"):
        st.markdown(f"""
        **Modell-Typ:** Patient-Based Forecast (Best Practice)

        **Patienten-Funnel:**

        | Stufe | Wert | Quelle |
        |---|---|---|
        | ED-Praevalenz (DE) | {params.ed_prevalence_men:,.0f} | Braun et al. 2000, Cologne Male Survey |
        | Therapiequote | {params.treatment_rate:.0%} | May et al. 2007; Arnold 2023 |
        | Unbehandelt | {untreated:,.0f} | Berechnet |
        | Erreichbar via OTC | {addressable:.0%} | UK-Analogie + Adjustierung |
        | Adressierbarer Pool | {addressable_patients:,.0f} | Berechnet |
        | Tabl./Patient/Mon. | {tablets_per_pat:.1f} | Rx-Durchschnitt (IQVIA) |
        | **OTC Peak (berechnet)** | **{otc_peak_computed:,.0f} Tabl./Mon.** | **Patienten × Frequenz** |

        **Unterschied zum volumenbasierten Modell:**
        - OTC Peak wird **berechnet** (nicht als Input gesetzt)
        - Therapiequote steigt **konsistent** mit tatsaechlichen OTC-Neupatientenzahlen
        - Alle Patientenzahlen sind **explizit und nachvollziehbar**
        - Ungenutzte Parameter (trial_rate, repeat_rate) wurden durch aktive Funnel-Logik ersetzt

        **Datenquellen:** Identisch zum volumenbasierten Modell (Arnold 2023, Braun 2000, May 2007, Lee 2021, MHRA 2017, ABDA 2024).
        """)


if __name__ == "__main__":
    st.set_page_config(page_title="Sildenafil Patient Model", page_icon="💊", layout="wide")
    show()
