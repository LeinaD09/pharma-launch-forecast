"""
Pharma Launch Forecast – Interactive Scenario Tool
===================================================
Use Case 1: Eliquis (Apixaban) Generic Entry 2026

Two perspectives:
  1. ORIGINATOR (BMS/Pfizer): Revenue-at-Risk Analysis
  2. GENERIC ENTRANT: Market Opportunity Analysis
"""

import sys
import os
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from io import BytesIO

# BUG-E2 fix: Force reimport to avoid Streamlit Cloud stale bytecode cache
import models.forecast_engine as _engine_mod
importlib.reload(_engine_mod)
from models.forecast_engine import (
    OriginatorParams,
    GenericParams,
    forecast_originator,
    forecast_generic,
    calculate_kpis_originator,
    calculate_kpis_generic,
)

def show():
    """Render the Eliquis Generic Entry page."""
        # ─── Custom CSS ─────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0.5rem !important; }
        .kpi-card, .kpi-card-red, .kpi-card-green, .kpi-card-purple {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px 8px;
            color: #1e293b;
            text-align: center;
            margin: 2px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .kpi-value { font-size: 18px; font-weight: 700; margin: 2px 0; line-height: 1.2; color: #0f172a; }
        .kpi-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-sublabel { font-size: 9px; color: #94a3b8; margin-top: 1px; }
        .perspective-header {
            font-size: 16px;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 600;
        }
        .originator-header {
            background-color: #fee2e2;
            color: #991b1b;
            border-left: 4px solid #dc2626;
        }
        .generic-header {
            background-color: #dcfce7;
            color: #166534;
            border-left: 4px solid #16a34a;
        }
        div[data-testid="stSidebar"] {
            background-color: #f8fafc;
            min-width: 280px !important;
            max-width: 320px !important;
            width: 300px !important;
        }
        div[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        div[data-testid="stSidebar"] [data-testid="stExpander"] {
            margin-bottom: -8px;
        }
        div[data-testid="stSidebar"] [data-testid="stExpander"] summary {
            font-size: 15px;
            font-weight: 600;
        }
        div[data-testid="stSidebar"] .stSlider label p {
            font-size: 14px !important;
        }
        div[data-testid="stSidebar"] h1 {
            font-size: 22px !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stSidebar"] .stDivider {
            margin: 4px 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)


    def format_eur(value: float, decimals: int = 0) -> str:
        """Format number as EUR currency."""
        if abs(value) >= 1_000_000_000:
            return f"\u20ac{value / 1_000_000_000:,.{decimals}f} Mrd."
        elif abs(value) >= 1_000_000:
            return f"\u20ac{value / 1_000_000:,.{decimals}f} Mio."
        elif abs(value) >= 1_000:
            return f"\u20ac{value / 1_000:,.{decimals}f}K"
        return f"\u20ac{value:,.{decimals}f}"


    def format_number(value: float) -> str:
        """Format large numbers with K/M suffix."""
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:,.0f}K"
        return f"{value:,.0f}"


    def kpi_card(label: str, value: str, card_type: str = "default", sublabel: str = "") -> str:
        css_class = {
            "default": "kpi-card",
            "red": "kpi-card-red",
            "green": "kpi-card-green",
            "purple": "kpi-card-purple",
        }.get(card_type, "kpi-card")
        sub_html = f'<div class="kpi-sublabel">{sublabel}</div>' if sublabel else ""
        return f"""
        <div class="{css_class}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {sub_html}
        </div>
        """


    # ─── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("Launch Forecast")
        st.caption("Eliquis \u2013 Generika-Eintritt 2026")

        # Perspective + Scenario (always visible, compact)
        perspective = st.radio(
            "Perspektive",
            ["\U0001f3e2 Original-Anbieter", "\U0001f48a Generika-Anbieter"],
            index=0, horizontal=True,
        )
        is_originator = "Original-Anbieter" in perspective

        scenario = st.selectbox(
            "Szenario",
            ["Base Case", "Bull (Generika)", "Bear (Generika)", "Custom"],
            index=0, label_visibility="collapsed",
        )

        # BUG-E3 fix: Reset slider session_state on scenario change
        _prev_scenario = st.session_state.get("_eliq_prev_scenario")
        if _prev_scenario is not None and _prev_scenario != scenario:
            for _k in ["Preis-Reduktion bei LOE (%)", "Erosions-Speed",
                        "Boden-Marktanteil (%)", "Monate bis Boden"]:
                st.session_state.pop(_k, None)
            st.session_state["_eliq_prev_scenario"] = scenario
            st.rerun()
        st.session_state["_eliq_prev_scenario"] = scenario

        # ─── Markt ──────────────────────────────────────────────────────────
        forecast_years = 7  # Fixed horizon
        with st.expander("Markt NOAK/DOAK", expanded=False):
            market_growth = st.slider(
                "Marktwachstum p.a. (%)", 0.0, 5.0, 2.0, 0.5,
                help="NOAK-Marktwachstum"
            ) / 100

        # ─── Aut-idem ───────────────────────────────────────────────────────
        with st.expander("Aut-idem / Substitution", expanded=False):
            aut_idem_enabled = st.checkbox("Aut-idem aktiv", value=True,
                                           help="SGB V \u00a7129 Apothekensubstitution")
            if aut_idem_enabled:
                aut_idem_peak = st.slider("Substitutionsquote (%)", 20, 95, 75, 5)
                aut_idem_ramp = st.slider("Festbetrag-Delay (Mon.)", 0, 12, 6, 1)
                aut_idem_full = st.slider("Volle Subst. nach (Mon.)", 6, 24, 12, 3)
            else:
                aut_idem_peak = 0
                aut_idem_ramp = 6
                aut_idem_full = 12

        if is_originator:
            # ─── Originator ─────────────────────────────────────────────────
            defaults = {
                "Base Case": (15, 1.0, 12, 18),
                "Bull (Generika)": (10, 1.3, 8, 12),
                "Bear (Generika)": (20, 0.7, 18, 24),
                "Custom": (15, 1.0, 12, 18),
            }
            d = defaults[scenario]

            with st.expander("Preis & Marktanteil", expanded=True):
                price_reduction = st.slider("Preis-Reduktion bei LOE (%)", 0, 40, d[0], 5)
                erosion_speed = st.slider("Erosions-Speed", 0.3, 2.0, d[1], 0.1,
                                          help="1.0=Normal, >1=schneller")
                floor_share = st.slider("Boden-Marktanteil (%)", 3, 25, d[2], 1)
                months_to_floor = st.slider("Monate bis Boden", 6, 36, d[3], 3)

            with st.expander("Authorized Generic", expanded=False):
                authorized_generic = st.checkbox("AG launchen?", value=False)
                ag_share = 0.25
                ag_discount = 0.30
                ag_share_decay = 0.0
                ag_discount_growth = 0.0
                if authorized_generic:
                    ag_share = st.slider("AG-Anteil am Generika-Segment (%)", 10, 50, 25, 5,
                                         help="Initialer Anteil des AG an allen Generika-Verordnungen") / 100
                    ag_share_decay = st.slider("↘ Anteil-Erosion Speed", 0.0, 2.0, 0.5, 0.1,
                                               help="0=statisch, 1=moderate Erosion, 2=schnelle Erosion. "
                                                    "AG verliert Marktanteil an unabhängige Generika.")
                    st.divider()
                    ag_discount = st.slider("AG Preis-Discount (%)", 20, 60, 30, 5,
                                            help="Initialer Preisabschlag des AG vs. Originator-Preis") / 100
                    ag_discount_growth = st.slider("↘ Discount-Zunahme Speed", 0.0, 2.0, 0.5, 0.1,
                                                    help="0=statisch, 1=moderater Preisverfall, 2=schneller Preisverfall. "
                                                         "AG-Preis nähert sich Generika-Preis an.")

            params = OriginatorParams(
                price_reduction_pct=price_reduction / 100,
                erosion_speed=erosion_speed,
                floor_share=floor_share / 100,
                months_to_floor=months_to_floor,
                market_growth_annual=market_growth,
                authorized_generic=authorized_generic,
                ag_share_of_generics=ag_share,
                ag_price_discount=ag_discount,
                ag_share_decay_speed=ag_share_decay,
                ag_discount_growth_speed=ag_discount_growth,
                aut_idem_enabled=aut_idem_enabled,
                aut_idem_quote_peak=aut_idem_peak / 100,
                aut_idem_ramp_months=aut_idem_ramp,
                aut_idem_full_months=aut_idem_full,
            )

        else:
            # ─── Generika ───────────────────────────────────────────────────
            with st.expander("Mein Generikum", expanded=True):
                company_name = st.text_input("Firma", value="Mein Unternehmen")
                launch_offset = st.slider("Launch nach LOE (Mon.)", 0, 12, 0, 1)
                price_discount = st.slider("Preis-Discount (%)", 20, 70, 45, 5)
                target_peak = st.slider("Peak-Marktanteil (%)", 2, 25, 10, 1)
                months_to_peak = st.slider("Mon. bis Peak", 6, 36, 18, 3)

            with st.expander("Generika Marktanteil", expanded=False):
                generic_segment_peak = st.slider("Generika gesamt Peak Share (%)", 20, 70, 55, 5,
                                                  help="Peak-Marktanteil aller Generika zusammen (inkl. meines)")
                generic_segment_months = st.slider("Mon. bis Peak Share", 12, 48, 24, 3,
                                                    help="Monate nach LOE bis das Generika-Segment seinen Peak erreicht")

            with st.expander("Kosten", expanded=False):
                cogs_pct = st.slider("COGS (%)", 10, 50, 25, 5)
                sga_monthly = st.number_input("SG&A / Monat (\u20ac)", 50_000, 500_000, 150_000, 25_000)
                launch_invest = st.number_input("Launch-Invest (\u20ac)", 0, 2_000_000, 500_000, 100_000)

            with st.expander("Rabattvertr\u00e4ge / Tender", expanded=False):
                tender_enabled = st.checkbox("Tender modellieren", value=True,
                                             help="\u00a7130a SGB V")
                if tender_enabled:
                    tender_start = st.slider("Start nach (Mon.)", 0, 12, 3, 1)
                    st.caption("**Kassen \u2013 Win-Wahrscheinlichkeit:**")
                    kassen_defaults = [
                        ("TK", 11.5, 0.158, 50, "Ziel"),
                        ("BARMER", 8.7, 0.119, 40, "Ziel"),
                        ("DAK", 5.5, 0.075, 45, "Ziel"),
                        ("AOK Bay", 4.6, 0.063, 30, "Optional"),
                        ("AOK BW", 4.5, 0.062, 30, "Optional"),
                    ]
                    tender_kassen = []
                    for name, lives, gkv_share, default_prob, status in kassen_defaults:
                        prob = st.slider(
                            f"{name} ({lives}M)", 0, 80, default_prob, 5,
                            key=f"tender_{name}",
                        )
                        if prob > 0:
                            tender_kassen.append({
                                "name": name, "lives_mio": lives,
                                "gkv_share": gkv_share, "win_prob": prob / 100,
                                "status": status,
                            })
                else:
                    tender_start = 3
                    tender_kassen = []

                my_aut_idem_capture = 0.30
                if aut_idem_enabled:
                    my_aut_idem_capture = st.slider(
                        "Mein Aut-idem-Anteil (%)", 10, 60, 30, 5
                    ) / 100

            params = GenericParams(
                my_company_name=company_name,
                launch_month_offset=launch_offset,
                price_discount_vs_originator=price_discount / 100,
                target_peak_share=target_peak / 100,
                months_to_peak=months_to_peak,
                generic_segment_peak_share=generic_segment_peak / 100,
                generic_segment_months_to_peak=generic_segment_months,
                cogs_pct_of_revenue=cogs_pct / 100,
                sga_monthly_eur=sga_monthly,
                launch_investment_eur=launch_invest,
                market_growth_annual=market_growth,
                aut_idem_enabled=aut_idem_enabled,
                aut_idem_quote_peak=aut_idem_peak / 100,
                aut_idem_ramp_months=aut_idem_ramp,
                aut_idem_full_months=aut_idem_full,
                my_aut_idem_capture=my_aut_idem_capture,
                tender_enabled=tender_enabled,
                tender_start_month=tender_start if tender_enabled else 3,
                tender_kassen=tender_kassen if tender_kassen else None,
            )


    # ─── Main Content ───────────────────────────────────────────────────────

    st.title("Eliquis (Apixaban) \u2013 Generika-Eintritt Mai 2026")
    st.markdown("**Markt:** Orale Antikoagulantien (NOAK/DOAK) Deutschland | **LOE:** Mai 2026")

    LOE_STR = "2026-05-01"

    if is_originator:
        # ═══════════════════════════════════════════════════════════════════
        # ORIGINATOR PERSPECTIVE
        # ═══════════════════════════════════════════════════════════════════
        st.markdown(
            '<div class="perspective-header originator-header">'
            '\U0001f3e2 Perspektive: Original-Anbieter \u2013 Revenue at Risk'
            '</div>',
            unsafe_allow_html=True,
        )

        df = forecast_originator(params, forecast_months=forecast_years * 12)
        kpis = calculate_kpis_originator(df)

        # ─── KPI Cards ──────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(kpi_card(
                "Umsatz vor LOE (p.a.)",
                format_eur(kpis["pre_loe_annual_revenue"]),
            ), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi_card(
                "Umsatz Jahr 1 nach LOE",
                format_eur(kpis["year1_post_loe_revenue"]),
                "red",
            ), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi_card(
                "Umsatz-R\u00fcckgang Jahr 1",
                f"-{kpis['year1_revenue_decline_pct']:.1f}%",
                "red",
            ), unsafe_allow_html=True)
        with c4:
            st.markdown(kpi_card(
                f"Revenue at Risk ({forecast_years}J)",
                format_eur(kpis["total_revenue_at_risk_5y"]),
                "red",
            ), unsafe_allow_html=True)

        st.markdown("")

        # ─── Chart 1: Revenue Trajectory + Market Share with Aut-idem ──
        col1, col2 = st.columns(2)

        with col1:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df["date"], y=df["counterfactual_revenue"],
                mode="lines", name="Ohne Generika-Eintritt",
                line=dict(color="#94a3b8", dash="dot", width=2),
                hovertemplate="Ohne Generika: %{y:\u20ac,.0f}<extra></extra>",
            ))

            fig.add_trace(go.Scatter(
                x=df["date"], y=df["originator_revenue"],
                mode="lines", name="Originator-Umsatz",
                line=dict(color="#dc2626", width=3),
                fill="tonexty", fillcolor="rgba(220,38,38,0.1)",
                hovertemplate="Originator: %{y:\u20ac,.0f}<extra></extra>",
            ))

            if params.authorized_generic:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df["ag_revenue"],
                    mode="lines", name="Authorized Generic",
                    line=dict(color="#f59e0b", width=2),
                    hovertemplate="AG: %{y:\u20ac,.0f}<extra></extra>",
                ))

            fig.add_shape(type="line", x0=LOE_STR, x1=LOE_STR, y0=0, y1=1,
                          yref="paper", line=dict(dash="dash", color="#6b7280", width=1))
            fig.add_annotation(x=LOE_STR, y=1, yref="paper", text="LOE Mai 2026",
                               showarrow=False, yanchor="bottom", font=dict(size=11, color="#6b7280"))

            fig.update_layout(
                title="Umsatzentwicklung (monatlich)",
                yaxis_title="Umsatz (EUR)",
                xaxis_title="",
                hovermode="x unified",
                template="plotly_white",
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, width="stretch")

        with col2:
            # Market share + aut-idem rate overlay
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])

            fig2.add_trace(go.Scatter(
                x=df["date"], y=df["originator_share"],
                mode="lines", name="Originator-Marktanteil",
                line=dict(color="#dc2626", width=3),
                hovertemplate="Originator: %{y:.1%}<extra></extra>",
            ), secondary_y=False)

            fig2.add_trace(go.Scatter(
                x=df["date"], y=df["generic_segment_share"],
                mode="lines", name="Generika-Segment",
                line=dict(color="#16a34a", width=2),
                hovertemplate="Generika: %{y:.1%}<extra></extra>",
            ), secondary_y=False)

            if aut_idem_enabled:
                fig2.add_trace(go.Scatter(
                    x=df["date"], y=df["aut_idem_rate"],
                    mode="lines", name="Aut-idem-Quote",
                    line=dict(color="#3b82f6", width=2, dash="dash"),
                    hovertemplate="Aut-idem: %{y:.1%}<extra></extra>",
                ), secondary_y=True)

            fig2.add_shape(type="line", x0=LOE_STR, x1=LOE_STR, y0=0, y1=1,
                           yref="paper", line=dict(dash="dash", color="#6b7280", width=1))
            fig2.add_annotation(x=LOE_STR, y=1, yref="paper", text="LOE",
                                showarrow=False, yanchor="bottom", font=dict(size=11, color="#6b7280"))

            fig2.update_layout(
                title="Marktanteil & Aut-idem-Quote",
                hovermode="x unified",
                template="plotly_white",
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            fig2.update_yaxes(title_text="Marktanteil", tickformat=".0%", secondary_y=False)
            fig2.update_yaxes(title_text="Aut-idem-Quote", tickformat=".0%",
                             range=[0, 1], secondary_y=True)

            st.plotly_chart(fig2, width="stretch")

        # ─── Chart 2: Cumulative Revenue at Risk ────────────────────────
        fig3 = go.Figure()
        post_loe = df[df["is_post_loe"]]

        fig3.add_trace(go.Bar(
            x=post_loe["date"], y=post_loe["revenue_at_risk"],
            name="Monatlicher Revenue at Risk",
            marker_color="#fca5a5",
            hovertemplate="Monatl. Verlust: %{y:\u20ac,.0f}<extra></extra>",
        ))

        fig3.add_trace(go.Scatter(
            x=post_loe["date"], y=post_loe["cumulative_revenue_at_risk"],
            mode="lines", name="Kumuliert",
            line=dict(color="#dc2626", width=3),
            yaxis="y2",
            hovertemplate="Kumuliert: %{y:\u20ac,.0f}<extra></extra>",
        ))

        fig3.update_layout(
            title="Revenue at Risk \u2013 Kumulative Analyse",
            yaxis=dict(title="Monatlich (EUR)", side="left"),
            yaxis2=dict(title="Kumuliert (EUR)", side="right", overlaying="y"),
            template="plotly_white",
            height=380,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig3, width="stretch")

        # ─── Share trajectory table ─────────────────────────────────────
        with st.expander("\U0001f4ca Detaildaten anzeigen"):
            display_df = df[["month", "originator_trx", "originator_share",
                             "originator_price", "originator_revenue",
                             "aut_idem_rate", "revenue_at_risk",
                             "cumulative_revenue_at_risk"]].copy()
            display_df.columns = [
                "Monat", "Originator TRx", "Marktanteil", "Preis/TRx",
                "Umsatz", "Aut-idem-Quote", "Revenue at Risk", "Kum. Revenue at Risk"
            ]
            display_df["Marktanteil"] = display_df["Marktanteil"].apply(lambda x: f"{x:.1%}")
            display_df["Aut-idem-Quote"] = display_df["Aut-idem-Quote"].apply(lambda x: f"{x:.1%}")
            display_df["Preis/TRx"] = display_df["Preis/TRx"].apply(lambda x: f"\u20ac{x:,.2f}")
            for col in ["Umsatz", "Revenue at Risk", "Kum. Revenue at Risk"]:
                display_df[col] = display_df[col].apply(lambda x: f"\u20ac{x:,.0f}")
            display_df["Originator TRx"] = display_df["Originator TRx"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(display_df, width="stretch", hide_index=True)


    else:
        # ═══════════════════════════════════════════════════════════════════
        # GENERIC PERSPECTIVE
        # ═══════════════════════════════════════════════════════════════════
        st.markdown(
            '<div class="perspective-header generic-header">'
            '\U0001f48a Perspektive: Generika-Anbieter \u2013 Market Opportunity'
            '</div>',
            unsafe_allow_html=True,
        )

        df = forecast_generic(params, forecast_months=forecast_years * 12)
        kpis = calculate_kpis_generic(df)

        # ─── KPI Cards Row 1 ────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(kpi_card(
                "Umsatz Jahr 1",
                format_eur(kpis.get("year1_revenue", 0)),
                "green",
            ), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi_card(
                f"Umsatz {forecast_years}J kumuliert",
                format_eur(kpis.get("total_5y_revenue", 0)),
                "green",
            ), unsafe_allow_html=True)
        with c3:
            be_month = kpis.get("breakeven_month")
            be_text = f"Monat {be_month}" if be_month else "Nicht erreicht"
            st.markdown(kpi_card(
                "Break-Even",
                be_text,
            ), unsafe_allow_html=True)
        with c4:
            st.markdown(kpi_card(
                f"Gewinn {forecast_years}J",
                format_eur(kpis.get("total_5y_profit", 0)),
                "green" if kpis.get("total_5y_profit", 0) > 0 else "red",
            ), unsafe_allow_html=True)

        # ─── KPI Cards Row 2: Peak Share + Volume Decomposition ─────────
        st.markdown("")
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            st.markdown(kpi_card(
                "Peak Marktanteil",
                f"{kpis.get('peak_share', 0):.1%}",
                "green",
            ), unsafe_allow_html=True)
        with c6:
            st.markdown(kpi_card(
                "Volumen: Organisch",
                f"{kpis.get('volume_organic_pct', 0):.0%}",
                "purple",
                "Natürlicher S-Kurven-Aufbau",
            ), unsafe_allow_html=True)
        with c7:
            st.markdown(kpi_card(
                "Volumen: Aut-idem",
                f"{kpis.get('volume_aut_idem_pct', 0):.0%}",
                "purple",
                "Apothekensubstitution",
            ), unsafe_allow_html=True)
        with c8:
            st.markdown(kpi_card(
                "Volumen: Tender",
                f"{kpis.get('volume_tender_pct', 0):.0%}",
                "purple",
                "GKV-Rabattverträge",
            ), unsafe_allow_html=True)

        st.markdown("")

        # ─── Chart Row 1: Revenue Build-Up + Market Share ────────────────
        col1, col2 = st.columns(2)

        with col1:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df["date"], y=df["my_revenue"],
                name="Mein Umsatz",
                marker_color="#16a34a",
                hovertemplate="Umsatz: %{y:\u20ac,.0f}<extra></extra>",
            ))

            fig.add_trace(go.Scatter(
                x=df["date"], y=df["cumulative_revenue"],
                mode="lines", name="Kumulierter Umsatz",
                line=dict(color="#166534", width=3),
                yaxis="y2",
                hovertemplate="Kumuliert: %{y:\u20ac,.0f}<extra></extra>",
            ))

            launch_date = pd.Timestamp("2026-05-01") + pd.DateOffset(months=params.launch_month_offset)
            launch_str = launch_date.strftime("%Y-%m-%d")
            fig.add_shape(type="line", x0=launch_str, x1=launch_str, y0=0, y1=1,
                          yref="paper", line=dict(dash="dash", color="#6b7280", width=1))
            fig.add_annotation(x=launch_str, y=1, yref="paper", text="Launch",
                               showarrow=False, yanchor="bottom", font=dict(size=11, color="#6b7280"))

            fig.update_layout(
                title="Umsatz-Aufbau (monatlich & kumuliert)",
                yaxis=dict(title="Monatlich (EUR)", side="left"),
                yaxis2=dict(title="Kumuliert (EUR)", side="right", overlaying="y"),
                template="plotly_white",
                height=420,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, width="stretch")

        with col2:
            fig2 = go.Figure()

            fig2.add_trace(go.Scatter(
                x=df["date"], y=df["my_share"],
                mode="lines", name="Mein Marktanteil",
                line=dict(color="#16a34a", width=3),
                fill="tozeroy", fillcolor="rgba(22,163,74,0.15)",
                hovertemplate="Mein Anteil: %{y:.1%}<extra></extra>",
            ))

            fig2.add_trace(go.Scatter(
                x=df["date"], y=df["total_generic_share"],
                mode="lines", name="Generika-Segment gesamt",
                line=dict(color="#94a3b8", dash="dot", width=2),
                hovertemplate="Alle Generika: %{y:.1%}<extra></extra>",
            ))

            fig2.add_shape(type="line", x0=launch_str, x1=launch_str, y0=0, y1=1,
                           yref="paper", line=dict(dash="dash", color="#6b7280", width=1))
            fig2.add_annotation(x=launch_str, y=1, yref="paper", text="Launch",
                                showarrow=False, yanchor="bottom", font=dict(size=11, color="#6b7280"))

            fig2.update_layout(
                title="Marktanteils-Aufbau",
                yaxis_title="Marktanteil",
                yaxis_tickformat=".0%",
                template="plotly_white",
                height=420,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig2, width="stretch")

        # ─── Chart Row 2: Volume Decomposition + Profitability ──────────
        col3, col4 = st.columns(2)

        with col3:
            # Stacked area chart: Organic / Aut-idem / Tender
            fig_vol = go.Figure()

            fig_vol.add_trace(go.Scatter(
                x=df["date"], y=df["organic_trx"],
                mode="lines", name="Organisch",
                line=dict(width=0.5, color="#16a34a"),
                fill="tozeroy", fillcolor="rgba(22,163,74,0.4)",
                stackgroup="volume",
                hovertemplate="Organisch: %{y:,.0f} TRx<extra></extra>",
            ))

            fig_vol.add_trace(go.Scatter(
                x=df["date"], y=df["aut_idem_trx"],
                mode="lines", name="Aut-idem",
                line=dict(width=0.5, color="#3b82f6"),
                fill="tonexty", fillcolor="rgba(59,130,246,0.4)",
                stackgroup="volume",
                hovertemplate="Aut-idem: %{y:,.0f} TRx<extra></extra>",
            ))

            fig_vol.add_trace(go.Scatter(
                x=df["date"], y=df["tender_trx"],
                mode="lines", name="Tender/Rabattvertrag",
                line=dict(width=0.5, color="#f59e0b"),
                fill="tonexty", fillcolor="rgba(245,158,11,0.4)",
                stackgroup="volume",
                hovertemplate="Tender: %{y:,.0f} TRx<extra></extra>",
            ))

            fig_vol.add_shape(type="line", x0=launch_str, x1=launch_str, y0=0, y1=1,
                              yref="paper", line=dict(dash="dash", color="#6b7280", width=1))
            fig_vol.add_annotation(x=launch_str, y=1, yref="paper", text="Launch",
                                   showarrow=False, yanchor="bottom", font=dict(size=11, color="#6b7280"))

            fig_vol.update_layout(
                title="Volumen-Zerlegung (TRx nach Quelle)",
                yaxis_title="TRx / Monat",
                xaxis_title="",
                template="plotly_white",
                height=420,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_vol, width="stretch")

        with col4:
            # Profitability waterfall
            fig3 = go.Figure()

            fig3.add_trace(go.Bar(
                x=df["date"], y=df["my_revenue"],
                name="Umsatz",
                marker_color="#86efac",
                hovertemplate="Umsatz: %{y:\u20ac,.0f}<extra></extra>",
            ))

            fig3.add_trace(go.Bar(
                x=df["date"], y=[-c for c in df["cogs"]],
                name="COGS",
                marker_color="#fca5a5",
                hovertemplate="COGS: %{y:\u20ac,.0f}<extra></extra>",
            ))

            fig3.add_trace(go.Bar(
                x=df["date"], y=[-s for s in df["sga"]],
                name="Vertrieb & Marketing",
                marker_color="#fdba74",
                hovertemplate="SG&A: %{y:\u20ac,.0f}<extra></extra>",
            ))

            fig3.add_trace(go.Scatter(
                x=df["date"], y=df["cumulative_profit"],
                mode="lines", name="Kum. Gewinn",
                line=dict(color="#166534", width=3),
                yaxis="y2",
                hovertemplate="Kum. Gewinn: %{y:\u20ac,.0f}<extra></extra>",
            ))

            fig3.update_layout(
                title="Profitabilit\u00e4ts-Analyse",
                barmode="relative",
                yaxis=dict(title="Monatlich (EUR)", side="left"),
                yaxis2=dict(title="Kumulierter Gewinn (EUR)", side="right", overlaying="y"),
                template="plotly_white",
                height=420,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig3, width="stretch")

        # ─── Chart Row 3: Aut-idem Rate ─────────────────────────────────
        if aut_idem_enabled:
            fig_ai = go.Figure()
            fig_ai.add_trace(go.Scatter(
                x=df["date"], y=df["aut_idem_rate"],
                mode="lines", name="Aut-idem-Quote",
                line=dict(color="#3b82f6", width=3),
                fill="tozeroy", fillcolor="rgba(59,130,246,0.15)",
                hovertemplate="Quote: %{y:.1%}<extra></extra>",
            ))
            fig_ai.add_shape(type="line", x0=launch_str, x1=launch_str, y0=0, y1=1,
                             yref="paper", line=dict(dash="dash", color="#6b7280", width=1))
            fig_ai.add_annotation(x=launch_str, y=1, yref="paper", text="Launch",
                                  showarrow=False, yanchor="bottom", font=dict(size=11, color="#6b7280"))
            fig_ai.update_layout(
                title="Aut-idem-Substitutionsquote \u00fcber Zeit",
                yaxis_title="Quote",
                yaxis_tickformat=".0%",
                yaxis_range=[0, 1],
                template="plotly_white",
                height=300,
                hovermode="x unified",
            )
            st.plotly_chart(fig_ai, width="stretch")

        # ─── Detail table ───────────────────────────────────────────────
        with st.expander("\U0001f4ca Detaildaten anzeigen"):
            display_df = df[["month", "organic_trx", "aut_idem_trx", "tender_trx",
                             "my_trx", "my_share", "aut_idem_rate", "my_price",
                             "my_revenue", "operating_profit",
                             "cumulative_revenue", "cumulative_profit"]].copy()
            display_df.columns = [
                "Monat", "Organisch TRx", "Aut-idem TRx", "Tender TRx",
                "Gesamt TRx", "Marktanteil", "Aut-idem-Quote", "Preis/TRx",
                "Umsatz", "Oper. Gewinn", "Kum. Umsatz", "Kum. Gewinn"
            ]
            display_df["Marktanteil"] = display_df["Marktanteil"].apply(lambda x: f"{x:.1%}")
            display_df["Aut-idem-Quote"] = display_df["Aut-idem-Quote"].apply(lambda x: f"{x:.1%}")
            display_df["Preis/TRx"] = display_df["Preis/TRx"].apply(lambda x: f"\u20ac{x:,.2f}" if x > 0 else "-")
            for col in ["Umsatz", "Oper. Gewinn", "Kum. Umsatz", "Kum. Gewinn"]:
                display_df[col] = display_df[col].apply(lambda x: f"\u20ac{x:,.0f}")
            for col in ["Organisch TRx", "Aut-idem TRx", "Tender TRx", "Gesamt TRx"]:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")
            st.dataframe(display_df, width="stretch", hide_index=True)


    # ─── Excel Export (both perspectives) ───────────────────────────────────
    st.divider()
    st.subheader("\U0001f4e5 Export")

    col_exp1, col_exp2, _ = st.columns([1, 1, 2])

    with col_exp1:
        # BUG-E1 fix: Reuse the params configured by the user via sliders
        # (both perspectives are always exported regardless of active view)
        if is_originator:
            orig_params = params  # already configured above with all slider values
            gen_params = GenericParams(
                market_growth_annual=market_growth,
                aut_idem_enabled=aut_idem_enabled,
                aut_idem_quote_peak=aut_idem_peak / 100,
                aut_idem_ramp_months=aut_idem_ramp,
                aut_idem_full_months=aut_idem_full,
            )
        else:
            orig_params = OriginatorParams(
                market_growth_annual=market_growth,
                aut_idem_enabled=aut_idem_enabled,
                aut_idem_quote_peak=aut_idem_peak / 100,
                aut_idem_ramp_months=aut_idem_ramp,
                aut_idem_full_months=aut_idem_full,
            )
            gen_params = params  # already configured above with all slider values

        df_orig = forecast_originator(orig_params, forecast_months=forecast_years * 12)
        df_gen = forecast_generic(gen_params, forecast_months=forecast_years * 12)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_orig.drop(columns=["date"]).to_excel(writer, sheet_name="Originator", index=False)
            df_gen.drop(columns=["date"]).to_excel(writer, sheet_name="Generika", index=False)

            summary = pd.DataFrame({
                "Metrik": [
                    "Forecast-Horizont",
                    "LOE-Datum",
                    "Perspektive",
                    "Szenario",
                    "Aut-idem aktiv",
                    "Aut-idem Peak-Quote",
                ],
                "Wert": [
                    f"{forecast_years} Jahre",
                    "Mai 2026",
                    perspective,
                    scenario,
                    "Ja" if aut_idem_enabled else "Nein",
                    f"{aut_idem_peak}%",
                ],
            })
            summary.to_excel(writer, sheet_name="Parameter", index=False)

        st.download_button(
            label="\u2b07\ufe0f Excel herunterladen",
            data=buffer.getvalue(),
            file_name="eliquis_launch_forecast.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_exp2:
        st.info("Export enth\u00e4lt beide Perspektiven (Originator + Generika) als separate Tabellenbl\u00e4tter.")


    # ─── Methodik & Datenquellen ─────────────────────────────────────────────
    st.divider()
    with st.expander("Methodik & Datenquellen"):
        st.markdown("""
**Modell-Architektur:** Dual-Perspektive Originator/Generika mit Aut-idem-Substitution, Rabattvertrags-Modellierung und Authorized-Generic-Strategie. Alle Volumina in TRx (Verordnungen).

| Komponente | Methodik | Referenz |
|---|---|---|
| Originator-Erosion | Exponentieller Decay: Share(t) = Floor + (Init-Floor) * e^(-k*t*speed) | Standard im Pharma-Forecasting; validiert durch Clopidogrel, Atorvastatin LOEs |
| Generika-Uptake | Logistische S-Kurve: 1 / (1 + e^(-s*(t-m))) | Rogers Adoption Curve; Standard bei Launch-Forecasts |
| Aut-idem-Substitution | Lineare Rampe: 0 -> Peak ueber [ramp, full] Monate | Abgeleitet aus G-BA Festbetrags-Timing + Apotheken-Substitutionsverhalten |
| Tender/Rabattvertrag | Erwartungswert: Sum(Kasse_share * Win_prob) * Ramp | Kein binaeres Modell; gewichteter Durchschnitt ueber Kassen-Portfolio |
| Preis-Erosion (Generika) | Zusaetzlicher Preisverfall: +0.3%/Monat, Max 15% | Beobachteter Trend in reifen Generika-Maerkten |
| Authorized Generic (AG) | AG-Anteil: exp. Decay; AG-Discount: exp. Zunahme | Originator-Zweitmarke zur Verteidigung des Generika-Segments |
| Competitive Ceiling | effective_peak = min(target_peak, segment_peak) | Peak-Share begrenzt durch Gesamtsegment |
| Marktwachstum | Lineares monatliches Compounding | NOAK-Markt: ~2% p.a. durch Bevoelkerungsalterung |

**Kernannahmen (Default-Werte):**

| Annahme | Modellwert | Faktenbasis |
|---|---|---|
| Eliquis Marktanteil | 42% (TRx) | Lauer-Taxe / GKV-Auswertungen 2024 |
| Eliquis Preis/TRx | EUR 91,50 | Lauer-Taxe, Festbetragslisten |
| NOAK-Gesamtmarkt | 4,2 Mio. TRx/Monat | IQVIA / GKV-Arzneimittelindex |
| Originator Boden-Share | 12% | Markentreue bei Small Molecules: 10-15% typisch |
| Generika-Segment Peak | 55% | Vergleich Clopidogrel (Plavix): 60-70% nach 3 Jahren |
| Aut-idem Peak-Quote | 75% | Abhaengig von Arzt-Akzeptanz und Festbetrag |
| Festbetrag-Delay | 6 Monate | G-BA braucht 3-6 Monate fuer Festbetragsgruppe |
| Generika Preis-Discount | 45% | Marktueblich DE: 30-60% fuer Generika |
| COGS | 25% | Branchenueblich Small Molecule Generika |

**Regulatorischer Rahmen:**
- **Aut-idem (SGB V Par.129):** Apotheke darf/muss wirkstoffgleiches Generikum abgeben, sofern Arzt nicht aut-idem ausschliesst
- **Festbetragsgruppe (G-BA):** Bestimmt Erstattungsobergrenze; typisch 3-6 Monate nach LOE
- **Rabattvertraege (Par.130a SGB V):** Krankenkassen schliessen Exklusivvertraege mit Generika-Herstellern
- **Authorized Generic:** Originator lanciert eigenes Generikum unter Zweitmarke zur Segment-Verteidigung

**Datenquellen (alle oeffentlich):**
- Lauer-Taxe / Festbetragslisten (Eliquis-Preis, Packungsgroessen)
- IQVIA Pharmamarkt Deutschland (NOAK-Marktvolumen, Marktanteile)
- GKV-Arzneimittelindex / WIdO (Verordnungsdaten)
- G-BA Beschluesse Festbetragsgruppen (Festbetrags-Timing, historische Referenzen)
- BfArM Zulassungsdaten (LOE-Datum, Patentablauf Apixaban)
- EMA / European Patent Office (Supplementary Protection Certificate)
- Plavix/Clopidogrel LOE 2009-2012 (Referenz Erosionsdynamik)
- Atorvastatin (Sortis) LOE 2012 (Referenz Generika-Uptake)
- ABDA Zahlen, Daten, Fakten 2024 (Apothekenmarkt)
- GKV-Spitzenverband (Rabattvertrags-Mechanik, Par.130a SGB V)
- Handelsblatt / Apotheke Adhoc (Marktberichte NOAK-Segment)
        """)

    # ─── Footer ─────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "\U0001f4cc Daten sind synthetisch und dienen ausschlie\u00dflich der Illustration. "
        "Angelehnt an \u00f6ffentlich verf\u00fcgbare Marktdaten zum NOAK-Segment in Deutschland. "
        "Kein Bezug zu vertraulichen IQVIA-Daten."
    )


if __name__ == "__main__":
    show()
