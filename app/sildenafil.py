"""
Pharma Launch Forecast – Use Case 4: Sildenafil Rx-to-OTC Switch (Viatris/Viagra)
==================================================================================
Advanced Rx-to-OTC model with pharmacy-only distribution.
All volumes in TABLETS (1 tablet = 1 application = 50mg).
"""

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force reimport to clear any stale bytecode cache
import models.sildenafil_otc_engine as _engine_mod
importlib.reload(_engine_mod)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models.sildenafil_otc_engine import (
    SildenafilOtcParams, ChannelParams,
    forecast_sildenafil_otc, calculate_kpis_sildenafil,
)


BLUE = "#1e3a5f"
TEAL = "#0d9488"
AMBER = "#d97706"
GREEN = "#27ae60"
RED = "#c0392b"
PURPLE = "#7c3aed"
PINK = "#db2777"


def show():
    """Render the Sildenafil Rx-to-OTC Switch page."""

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
        .kpi-title {
            background: #f1f5f9; border: 1px solid #e2e8f0;
            border-radius: 8px; padding: 10px 12px;
            text-align: left; flex: 0 0 140px; min-width: 140px;
            display: flex; align-items: center;
        }
        .kpi-title-text { font-size: 12px; font-weight: 700; color: #475569; line-height: 1.3; }
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

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            color: #64748b;
        }
        .stTabs [aria-selected="true"] {
            background: #ffffff !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
            color: #0f172a !important;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # ===================================================================
    # SIDEBAR
    # ===================================================================
    with st.sidebar:
        st.markdown(f"#### Sildenafil Rx-to-OTC Switch")
        st.markdown("*Viatris / Viagra Connect (DE)*")

        scenario = st.selectbox("Szenario", [
            "Base Case", "Optimistisch (BMG erzwingt Switch)",
            "Konservativ (SVA-Auflagen)"
        ], key="sil_scenario")

        # --- Scenario-driven slider defaults -----------------------
        # All volumes in TABLETS (1 tablet = 1 application).
        # OTC: 350K packs x 6 = 2.1M tablets; Rx: 217K packs x 4 = 868K tablets
        if scenario == "Optimistisch (BMG erzwingt Switch)":
            _d = dict(otc_peak=2_700_000, otc_ramp=12, mktg=750_000,
                      new_patient=70, brand_share=35)
        elif scenario == "Konservativ (SVA-Auflagen)":
            _d = dict(otc_peak=1_200_000, otc_ramp=24, mktg=300_000,
                      new_patient=55, brand_share=20)
        else:  # Base Case
            _d = dict(otc_peak=2_100_000, otc_ramp=18, mktg=500_000,
                      new_patient=63, brand_share=25)

        # Reset scenario-dependent slider keys when scenario changes.
        _prev = st.session_state.get("_sil_prev_scenario")
        if _prev is not None and _prev != scenario:
            for _k in ["sil_otc_peak", "sil_otc_ramp",
                        "sil_np", "sil_brand"]:
                st.session_state.pop(_k, None)
            st.session_state["_sil_prev_scenario"] = scenario
            st.rerun()
        st.session_state["_sil_prev_scenario"] = scenario

        st.markdown("---")

        with st.expander("Rx-Markt", expanded=False):
            rx_tablets = st.number_input("Sildenafil Rx Tabl./Mon.", 200_000, 2_500_000, 868_000, 10_000, key="sil_rx_tabs")
            rx_price_brand = st.number_input("Viagra Preis/Tabl. (EUR)", 5.0, 25.0, 11.19, 0.5, key="sil_rx_brand")
            rx_price_generic = st.number_input("Generika Preis/Tabl. (EUR)", 0.50, 5.0, 1.50, 0.1, key="sil_rx_gen")
            rx_brand_share = st.slider("Viagra Markenanteil Rx (%)", 2, 25, 10, key="sil_rx_bs") / 100
            st.caption("*Rx-Rueckgang wird automatisch aus OTC-Rx-Migration berechnet*")

        with st.expander("OTC-Markt", expanded=False):
            otc_price = st.number_input("OTC Preis/Tablette (EUR)", 2.0, 15.0, 5.99, 0.5, key="sil_otc_p")
            otc_peak = st.number_input("OTC Peak Tabl./Mon.", 500_000, 5_000_000, _d["otc_peak"], 100_000, key="sil_otc_peak")
            otc_ramp = st.slider("Monate bis Peak", 6, 36, _d["otc_ramp"], key="sil_otc_ramp")
            new_patient = st.slider("Neue Patienten (% OTC-Vol.)", 30, 80, _d["new_patient"], key="sil_np") / 100
            st.markdown("---")
            st.caption("Tadalafil-Migration (Cialis bleibt Rx)")
            tada_monthly = st.number_input("Tadalafil Rx Tabl./Mon.", 200_000, 1_500_000, 480_000, 10_000, key="sil_tada")
            tada_switch = st.slider("Migration zu Sildenafil OTC (%)", 0, 30, 12, key="sil_tadas") / 100

        with st.expander("OTC Marke vs. Generika", expanded=False):
            brand_share = st.slider("Viagra Connect Anteil OTC (%)", 15, 70, _d["brand_share"], key="sil_brand") / 100
            brand_erosion = st.slider("Markenanteil-Erosion p.a. (Pp.)", 0, 10, 3, key="sil_berosion") / 100
            brand_premium = st.slider("Preispremium Marke (x)", 1.0, 3.0, 1.8, 0.1, key="sil_bprem")

        with st.expander("Stationaer vs. Online", expanded=False):
            st.caption("Apothekenpflichtig: nur Apotheken-Kanaele")
            ch_apo = st.slider("Stationaere Apotheke (%)", 20, 80, 55, key="sil_ch_apo")
            ch_online = 100 - ch_apo
            st.markdown(f"*Online-Apotheke: {ch_online}%*")
            online_growth = st.slider("Online-Wachstum p.a. (Pp.)", 0, 10, 2, key="sil_og") / 100

    # --- Build params --------------------------------------------------
    channels = [
        ChannelParams(name="Stationaere Apotheke", share_of_otc=ch_apo / 100,
                      share_trend_annual=-online_growth, margin_pct=0.42,
                      distribution_cost_pct=0.06, discretion_factor=0.70),
        ChannelParams(name="Online-Apotheke", share_of_otc=ch_online / 100,
                      share_trend_annual=online_growth, margin_pct=0.30,
                      distribution_cost_pct=0.10, discretion_factor=1.0),
    ]

    params = SildenafilOtcParams(
        rx_tablets_per_month=rx_tablets,
        rx_price_brand=rx_price_brand,
        rx_price_generic=rx_price_generic,
        rx_brand_share=rx_brand_share,
        otc_price_per_tablet=otc_price,
        otc_peak_tablets_per_month=otc_peak,
        otc_ramp_months=otc_ramp,
        new_patient_share=new_patient,
        brand_otc_share=brand_share,
        brand_otc_share_trend=-brand_erosion,
        brand_price_premium=brand_premium,
        channels=channels,
        marketing_monthly_eur=_d["mktg"],
        tadalafil_rx_tablets_monthly=tada_monthly,
        tadalafil_switch_to_sildenafil_otc=tada_switch,
    )

    df = forecast_sildenafil_otc(params)
    kpis = calculate_kpis_sildenafil(df)

    # ===================================================================
    # HEADER
    # ===================================================================
    st.markdown("")
    st.markdown(f"#### Sildenafil Rx-to-OTC Switch Forecast")
    st.markdown(f"<span style='font-size:13px;color:#64748b;'>"
                f"Viatris / Viagra Connect – Szenario: <b>{scenario}</b> | "
                f"Dual-Channel Apotheken-Modell (apothekenpflichtig)</span>",
                unsafe_allow_html=True)

    # ===================================================================
    # KPI CARDS (3 rows with title cards) — rendered as pure HTML flexbox
    # ===================================================================
    co_rev = kpis.get("crossover_month")
    co_tabs = kpis.get("crossover_month_tablets")
    co_text = f"M{co_rev} / M{co_tabs}" if co_rev and co_tabs else (
        f"Monat {co_rev}" if co_rev else "–"
    )

    be_text = f"M{kpis['breakeven_month']}" if kpis.get('breakeven_month') else "–"

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-title"><div class="kpi-title-text">Was bringt<br>der Switch?</div></div>
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
        <div class="kpi-title"><div class="kpi-title-text">Wie verteilt sich<br>der Markt?</div></div>
        <div class="kpi-card-purple">
            <div class="kpi-label">Online-Anteil M12</div>
            <div class="kpi-value">{kpis['online_share_m12']:.0%}</div>
            <div class="kpi-sublabel">Online-Apotheke</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Markenanteil M12</div>
            <div class="kpi-value">{kpis['brand_share_m12']:.0%}</div>
            <div class="kpi-sublabel">Viagra vs. Generika</div>
        </div>
        <div class="kpi-card-red">
            <div class="kpi-label">Rx-Rueckgang</div>
            <div class="kpi-value">{kpis['rx_decline_total']:.0%}</div>
            <div class="kpi-sublabel">ueber 5 Jahre</div>
        </div>
        <div class="kpi-card-green">
            <div class="kpi-label">Therapiequote 5J</div>
            <div class="kpi-value">{kpis['treatment_rate_final']:.0%}</div>
            <div class="kpi-sublabel">vorher: 30%</div>
        </div>
    </div>
    <div class="kpi-row">
        <div class="kpi-title"><div class="kpi-title-text">Lohnt es<br>sich?</div></div>
        <div class="kpi-card-green">
            <div class="kpi-label">Breakeven</div>
            <div class="kpi-value">{be_text}</div>
            <div class="kpi-sublabel">Kum. Gewinn > 0</div>
        </div>
        <div class="kpi-card-teal">
            <div class="kpi-label">Marketing-ROI</div>
            <div class="kpi-value">{kpis['marketing_roi']:.1f}x</div>
            <div class="kpi-sublabel">Gewinn / Marketing</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Marketing 5J</div>
            <div class="kpi-value">EUR {kpis['total_5y_marketing']/1e6:.0f}M</div>
            <div class="kpi-sublabel">kumuliert</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Umsatz 5J</div>
            <div class="kpi-value">EUR {kpis['total_5y_revenue']/1e6:.0f}M</div>
            <div class="kpi-sublabel">Rx + OTC kumuliert</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ===================================================================
    # CHARTS
    # ===================================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Rx vs. OTC", "Stationär vs. Online", "Marke vs. Generika",
        "Patienten-Zuwachs", "Profitabilitaet"
    ])

    # --- Chart 1: Rx vs OTC tablets + revenue -------------------------
    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=df["month"], y=df["rx_tablets"], name="Rx Tabletten",
            line=dict(color=BLUE, width=2.5),
        ))
        fig1.add_trace(go.Scatter(
            x=df["month"], y=df["otc_tablets"], name="OTC Tabletten",
            line=dict(color=TEAL, width=2.5),
        ))
        if kpis["crossover_month_tablets"]:
            fig1.add_vline(x=kpis["crossover_month_tablets"], line_dash="dot",
                           line_color=AMBER,
                           annotation_text=f"OTC > Rx (M{kpis['crossover_month_tablets']})")
        fig1.update_layout(
            title="Rx vs. OTC Tabletten/Monat",
            xaxis_title="Monate nach Switch", yaxis_title="Tabletten",
            yaxis_tickformat=",", height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig1, width="stretch")

        # Stacked revenue
        fig1b = go.Figure()
        fig1b.add_trace(go.Bar(
            x=df["month"], y=df["rx_revenue"], name="Rx Umsatz",
            marker_color="#93c5fd",
        ))
        fig1b.add_trace(go.Bar(
            x=df["month"], y=df["otc_manufacturer_revenue"], name="OTC Umsatz (Hersteller)",
            marker_color="#5eead4",
        ))
        if kpis["crossover_month"]:
            fig1b.add_vline(x=kpis["crossover_month"], line_dash="dot",
                            line_color=AMBER,
                            annotation_text=f"OTC > Rx (M{kpis['crossover_month']})")
        fig1b.update_layout(
            barmode="stack",
            title="Rx vs. OTC Umsatz/Monat",
            xaxis_title="Monate nach Switch", yaxis_title="EUR",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig1b, width="stretch")

    # --- Chart 2: Omnichannel -----------------------------------------
    with tab2:
        col_a, col_b = st.columns(2)

        with col_a:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["month"], y=df["ch_apotheke_tablets"],
                name="Stationaere Apotheke", stackgroup="one",
                line=dict(color=BLUE),
            ))
            fig2.add_trace(go.Scatter(
                x=df["month"], y=df["ch_online_tablets"],
                name="Online-Apotheke", stackgroup="one",
                line=dict(color=TEAL),
            ))
            fig2.update_layout(
                title="OTC-Volumen nach Vertriebskanal",
                xaxis_title="Monate", yaxis_title="Tabletten",
                yaxis_tickformat=",", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig2, width="stretch")

        with col_b:
            fig2b = go.Figure()
            fig2b.add_trace(go.Scatter(
                x=df["month"], y=df["ch_apotheke_share"],
                name="Stationaere Apotheke",
                line=dict(color=BLUE, width=2),
            ))
            fig2b.add_trace(go.Scatter(
                x=df["month"], y=df["ch_online_share"],
                name="Online-Apotheke",
                line=dict(color=TEAL, width=2),
            ))
            fig2b.update_layout(
                title="Kanalanteil-Entwicklung",
                xaxis_title="Monate", yaxis_title="Anteil",
                yaxis_tickformat=".0%", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig2b, width="stretch")

        # Revenue by channel
        fig2c = go.Figure()
        fig2c.add_trace(go.Bar(
            x=df["month"], y=df["ch_apotheke_revenue"],
            name="Apotheke", marker_color=BLUE,
        ))
        fig2c.add_trace(go.Bar(
            x=df["month"], y=df["ch_online_revenue"],
            name="Online", marker_color=TEAL,
        ))
        fig2c.update_layout(
            barmode="stack",
            title="OTC-Herstellerumsatz nach Kanal",
            xaxis_title="Monate", yaxis_title="EUR",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig2c, width="stretch")

    # --- Chart 3: Brand vs Generic ------------------------------------
    with tab3:
        col_c, col_d = st.columns(2)

        with col_c:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=df["month"], y=df["otc_brand_tablets"],
                name="Viagra Connect (Marke)", stackgroup="one",
                line=dict(color="#1e40af"),
            ))
            fig3.add_trace(go.Scatter(
                x=df["month"], y=df["otc_generic_tablets"],
                name="Generika OTC", stackgroup="one",
                line=dict(color="#94a3b8"),
            ))
            fig3.update_layout(
                title="OTC-Volumen: Marke vs. Generika",
                xaxis_title="Monate", yaxis_title="Tabletten",
                yaxis_tickformat=",", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig3, width="stretch")

        with col_d:
            fig3b = go.Figure()
            fig3b.add_trace(go.Scatter(
                x=df["month"], y=df["otc_brand_share"],
                name="Viagra Connect Anteil",
                line=dict(color="#1e40af", width=3),
                fill="tozeroy", fillcolor="rgba(30,64,175,0.1)",
            ))
            fig3b.update_layout(
                title="Viagra Markenanteil-Erosion",
                xaxis_title="Monate", yaxis_title="Anteil",
                yaxis_tickformat=".0%", height=400,
                yaxis_range=[0, 0.7],
            )
            st.plotly_chart(fig3b, width="stretch")

    # --- Chart 4: Patienten-Zuwachs ------------------------------------
    with tab4:
        # Volume decomposition (patient origin)
        fig3c = go.Figure()
        fig3c.add_trace(go.Scatter(
            x=df["month"], y=df["otc_from_new_patients"],
            name="Neue Patienten (nie Arzt)", stackgroup="one",
            line=dict(color=GREEN),
        ))
        fig3c.add_trace(go.Scatter(
            x=df["month"], y=df["otc_from_rx_migration"],
            name="Rx-Migration (Sildenafil)", stackgroup="one",
            line=dict(color=BLUE),
        ))
        fig3c.add_trace(go.Scatter(
            x=df["month"], y=df["otc_from_tadalafil"],
            name="Tadalafil-Migration", stackgroup="one",
            line=dict(color=PURPLE),
        ))
        fig3c.update_layout(
            title="OTC-Volumen Herkunft (Woher kommen die Patienten?)",
            xaxis_title="Monate", yaxis_title="Tabletten",
            yaxis_tickformat=",", height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig3c, width="stretch")

        treated_monthly = df["treatment_rate_effective"] * params.ed_prevalence_men
        untreated_monthly = params.ed_prevalence_men - treated_monthly

        col_tg1, col_tg2 = st.columns(2)

        with col_tg1:
            fig_tg_abs = go.Figure()
            fig_tg_abs.add_trace(go.Bar(
                x=df["month"], y=treated_monthly,
                name="Behandelt",
                marker_color=GREEN,
            ))
            fig_tg_abs.add_trace(go.Bar(
                x=df["month"], y=untreated_monthly,
                name="Unbehandelt",
                marker_color="#e5e7eb",
            ))
            fig_tg_abs.update_layout(
                barmode="stack",
                title="ED-Patienten: Behandelt vs. Unbehandelt",
                xaxis_title="Monate nach Switch", yaxis_title="Maenner",
                yaxis_tickformat=",", height=420,
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
                                  line_color="#999", annotation_text="Vor Switch (30%)")
            fig_tg_rate.update_layout(
                title="Therapiequote ueber Zeit",
                xaxis_title="Monate nach Switch", yaxis_title="Therapiequote",
                yaxis_tickformat=".0%", height=420,
            )
            st.plotly_chart(fig_tg_rate, width="stretch")

    # --- Chart 5: Profitability (2x2 grid) ---------------------------
    with tab5:
        # Row 1: Rx vs. OTC Gross Profit + Channel Profitability
        col_pr1, col_pr2 = st.columns(2)

        with col_pr1:
            fig_rxotc_gp = go.Figure()
            fig_rxotc_gp.add_trace(go.Bar(
                x=df["month"], y=df["rx_gross_profit"],
                name="Rx Bruttogewinn", marker_color="#93c5fd",
            ))
            fig_rxotc_gp.add_trace(go.Bar(
                x=df["month"], y=df["otc_gross_profit"],
                name="OTC Bruttogewinn", marker_color="#5eead4",
            ))
            co_rev = kpis.get("crossover_month")
            if co_rev:
                fig_rxotc_gp.add_vline(
                    x=co_rev, line_dash="dot", line_color=AMBER,
                    annotation_text=f"OTC > Rx (M{co_rev})",
                )
            fig_rxotc_gp.update_layout(
                barmode="group",
                title="Bruttogewinn: Rx vs. OTC (nach COGS)",
                xaxis_title="Monate", yaxis_title="EUR",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_rxotc_gp, width="stretch")

        with col_pr2:
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
    # SCENARIO COMPARISON TABLE
    # ===================================================================
    st.markdown("---")
    st.markdown("### Szenario-Vergleich")

    scenarios = {
        "Konservativ": {"otc_peak_tablets_per_month": 1_200_000, "otc_ramp_months": 24,
                        "marketing_monthly_eur": 300_000, "new_patient_share": 0.55,
                        "brand_otc_share": 0.20},
        "Base Case": {},
        "Optimistisch": {"otc_peak_tablets_per_month": 2_700_000, "otc_ramp_months": 12,
                         "marketing_monthly_eur": 750_000, "new_patient_share": 0.70,
                         "brand_otc_share": 0.35},
    }

    comp_rows = []
    from dataclasses import replace as _dc_replace
    for sn, overrides in scenarios.items():
        p = _dc_replace(params, **overrides) if overrides else params
        k = calculate_kpis_sildenafil(forecast_sildenafil_otc(p))
        comp_rows.append({
            "Szenario": sn,
            "OTC Umsatz M12": f"EUR {k['year1_otc_revenue']/1e6:.0f}M",
            "Gesamt M12": f"EUR {k['year1_total_revenue']/1e6:.0f}M",
            "Gewinn 5J": f"EUR {k['total_5y_profit']/1e6:.0f}M",
            "Online M12": f"{k['online_share_m12']:.0%}",
            "Marke M12": f"{k['brand_share_m12']:.0%}",
            "Crossover (Umsatz)": f"M{k['crossover_month']}" if k['crossover_month'] else "–",
            "Crossover (Tabl.)": f"M{k['crossover_month_tablets']}" if k['crossover_month_tablets'] else "–",
        })

    st.dataframe(pd.DataFrame(comp_rows).set_index("Szenario"), width=900)

    # ===================================================================
    # METHODOLOGY
    # ===================================================================
    with st.expander("Methodik & Datenquellen"):
        st.markdown("""
        **Modell-Architektur:** Volumenbasiertes Dual-Channel Rx/OTC Modell. Alle Volumina in Tabletten (1 Tabl. = 1 Anwendung = 50mg). OTC Peak ist ein direkter Input-Parameter.

        | Komponente | Methodik | Referenz |
        |---|---|---|
        | OTC-Ramp | Logistische S-Kurve | UK Viagra Connect Launch 2018 |
        | Rx-Rueckgang | **Abgeleitet** aus OTC-Rx-Migration | Konsistenzregel: keine Doppelzaehlung |
        | Rx-Umsatz | Herstellerumsatz (52% ex-factory) | Konsistenz mit OTC-Herstellerumsatz |
        | Apothekenverteilung | 2 Kanaele (apothekenpflichtig) | ABDA ZDF 2024: ~23% OTC online |
        | Online-Wachstum | +2 Pp./Jahr | ABDA/DatamedIQ: +1,5-2 Pp./Jahr (2019-2024) |
        | Online-Startanteil | 45% (Stigma-Kategorie) | Gewichtsabnahme 56%, Rauchentwoehn. 40% online |
        | Diskretions-Effekt | Parametrisiert (Baseline 0,70 + Sensitivity 0,15) | PMC: 36% der ED-Nutzer scham-/diskretionsgetrieben |
        | Markenanteil | Lineare Erosion + Premium (proportional auf Kanaele) | UK: Generika ab GBP 0.50/Tab |
        | Treatment Gap | Aus OTC-Volumen abgeleitet | UK: 63% Neupatienten |
        | Marketing | Kostenfaktor, 6-Monats-Taper zu Maintenance | Kein Volumen-Effekt |
        | Profitabilitaet | Separate Rx/OTC Bruttogewinn-Berechnung | COGS 12% auf Herstellerumsatz |
        | Tadalafil-Migration | Logistische S-Kurve + Saisonalitaet | Cialis bleibt Rx-only |

        **Zentrale Konsistenzregeln:**
        - Rx-Rueckgang = OTC-Rx-Migration (Tabletten koennen nicht in beiden Pools sein)
        - Rx- und OTC-Umsatz beide auf Herstellerebene (ex-factory) fuer Vergleichbarkeit
        - Brand Premium wird proportional auf Kanaele verteilt (nicht nur auf Gesamtsumme)
        - Marketing-Taper: gradueller 6-Monats-Uebergang statt Stufenfunktion

        **Annahmen Online-Anteil (Stuetzung):**

        | Annahme | Modellwert | Faktenbasis |
        |---|---|---|
        | Online-Startanteil | 45% | Allg. OTC: 23% (ABDA 2024). Stigma-Kategorien: Gewichtsabnahme 56%, Rauchentwoehn. 40% (ecommercegermany.com). ED-Stigma vergleichbar. |
        | Online-Wachstum | +2 Pp./Jahr | Allg. OTC: ~+1,5-2 Pp./Jahr (ABDA/DatamedIQ 2019-2024, +8 Pp. in 5 Jahren). |
        | Diskretions-Effekt | Parametrisiert | PMC-Studie (DE, n=11.456): 23% Diskretion + 13% Scham = 36%. STI-Studie: 80% bevorzugen Postversand (PMC). |

        **Datenquellen (alle oeffentlich):**
        - Arnold M (2023). Public-Health-Impact OTC-Switch Sildenafil 50 mg. HSK Berlin, inav-Gutachten (Viatris)
        - Braun et al. (2000). Cologne Male Survey -- ED-Praevalenz DE (19,2% bei 30-80J.)
        - May et al. (2007). Cottbus Survey, n=10.000 -- Behandlungsquote ~30%
        - Capogrosso et al. (2013). 1 von 4 Neudiagnosen <40 Jahre
        - Lee et al. (2021). UK Real-World-Studie, n=1.162 -- signif. mehr Arzt-/Apothekenbesuche post-Switch
        - Gordijn et al. (2022). Apotheken-Beratungsqualitaet bei OTC-Sildenafil (Nordirland)
        - MHRA (2017). Public Assessment Report -- Viagra Connect BTC-Reklassifizierung UK
        - ABDA (2024). Zahlen, Daten, Fakten -- Versandhandel: ~23% OTC online (237 Mio. Packungen)
        - DatamedIQ (2022). OTC-Versandhandel: 22,6% Umsatzanteil, +8,1% YoY
        - BVDVA/IQVIA (2024). OTC-Versandhandel: 49% des Mail-Order-Umsatzes, +8,1% YoY
        - Sempora (2024). Top 15 Online-Apotheken: EUR 2,83 Mrd. Nettoumsatz
        - PMC (Frontiers in Pharmacology, 2024). Online-Medikamentenkauf: Privatsphaere als Treiber bei ED
        - PMC (Sexual Medicine, 2020). DE Online-Plattform ED, n=11.456: 36% scham-/diskretionsgetrieben
        - ecommercegermany.com (2024). Stigma-Kategorien: Gewichtsabnahme 56%, Rauchentwoehn. 40% online
        - IQVIA Pharmamarkt DE, Apotheke Adhoc (PDE5-Marktdaten)
        - Handelsblatt / Citeline (BfArM SVA-Entscheidungen 2022/2023/2025)
        - PAGB/Frontier Economics (UK OTC Impact Report)

        Ausfuehrliche Dokumentation: [docs/Modell_Volumen.md](https://github.com/leelesemann-sys/pharma-launch-forecast/blob/main/docs/Modell_Volumen.md)
        """)


if __name__ == "__main__":
    st.set_page_config(page_title="Sildenafil OTC Switch", page_icon="💊", layout="wide")
    show()
