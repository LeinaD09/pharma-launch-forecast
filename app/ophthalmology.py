"""
Pharma Launch Forecast – Use Case 5: Eye Care Franchise Portfolio Launch
=====================================================================
Sequential specialty ophthalmology market entry with AMNOG pricing,
Facharzt adoption, field force scaling, and cross-product synergies.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models.ophthalmology_engine import (
    ProductParams, FieldForceParams, MarketParams,
    default_ryzumvi, default_mr141, default_tyrvaya,
    forecast_ophthalmology, calculate_kpis_ophthalmology,
)

BLUE = "#1e3a5f"
TEAL = "#0d9488"
AMBER = "#d97706"
GREEN = "#27ae60"
RED = "#c0392b"
PURPLE = "#7c3aed"
INDIGO = "#4f46e5"


def show():
    """Render the Ophthalmology Portfolio Launch page."""

    st.markdown("""
    <style>
        /* Reduce Streamlit default top padding */
        .block-container { padding-top: 1.5rem !important; padding-bottom: 0.5rem !important; }
        h2 { margin-top: 0 !important; margin-bottom: 0.2rem !important; }

        .kpi-card, .kpi-card-teal, .kpi-card-amber,
        .kpi-card-green, .kpi-card-purple, .kpi-card-indigo,
        .kpi-card-red, .kpi-card-orange, .kpi-card-blue {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px; padding: 10px 8px;
            color: #1e293b;
            text-align: center; margin: 2px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .kpi-value { font-size: 18px; font-weight: 700; margin: 2px 0; line-height: 1.2; color: #0f172a; }
        .kpi-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-sublabel { font-size: 9px; color: #94a3b8; margin-top: 1px; }

        div[data-testid="stSidebar"] {
            background-color: #f8fafc;
            min-width: 280px !important; max-width: 340px !important; width: 320px !important;
        }
        div[data-testid="stSidebar"] .stMarkdown p { font-size: 13px; }
        div[data-testid="stSidebar"] label { font-size: 13px !important; }

        /* Tab styling – visible background + border */
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

    # ═══════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("#### Eye Care Franchise")
        st.markdown("*Specialty Ophthalmology DE*")

        scenario = st.selectbox("Szenario", [
            "Base Case",
            "Aggressiv (schneller Aufbau)",
            "Konservativ (Tyrvaya verzoegert)",
        ], key="oph_scenario")

        st.markdown("---")

        # ─── Product 1: RYZUMVI ─────────────────────────────────
        with st.expander("P1: RYZUMVI (Mydriase)", expanded=False):
            r_launch = st.number_input("Launch Monat", 1, 24, 1, key="r_lm")
            r_eligible = st.number_input("Elig. Prozeduren/Jahr", 200_000, 2_000_000, 800_000, 50_000, key="r_elig")
            r_growth = st.slider("Marktwachstum /Jahr (%)", 0, 10, 2, key="r_growth") / 100
            r_addressable = st.slider("Adressierbar (%)", 5, 50, 25, key="r_addr") / 100
            r_share = st.slider("Peak Marktanteil (%)", 10, 80, 50, key="r_share") / 100
            r_speed = st.slider("Adoption (Mon. bis ~80% Peak)", 6, 36, 18, key="r_speed")
            r_price = st.number_input("Preis/Behandlung (EUR)", 10.0, 60.0, 25.0, 1.0, key="r_price")
            r_amnog_cut = st.slider("AMNOG-Preisabschlag (%)", 0, 40, 10, key="r_amnog") / 100

        # ─── Product 2: MR-141 ──────────────────────────────────
        with st.expander("P2: MR-141 (Presbyopie)", expanded=False):
            m_launch = st.number_input("Launch Monat", 6, 48, 18, key="m_lm")
            m_eligible = st.number_input("Elig. Patienten", 5_000_000, 25_000_000, 15_000_000, 1_000_000, key="m_elig")
            m_growth = st.slider("Marktwachstum /Jahr (%)", 0, 10, 3, key="m_growth") / 100
            m_addressable = st.slider("Adressierbar (%)", 1, 10, 2, key="m_addr") / 100
            m_compliance = st.slider("Compliance (%)", 30, 90, 60, key="m_comp") / 100
            m_share = st.slider("Peak Marktanteil (%)", 10, 60, 40, key="m_share") / 100
            m_speed = st.slider("Adoption (Mon. bis ~80% Peak)", 12, 48, 24, key="m_speed")
            m_price = st.number_input("Preis/Monat (EUR)", 20.0, 100.0, 45.0, 5.0, key="m_price")
            m_amnog_cut = st.slider("AMNOG-Preisabschlag (%)", 5, 50, 25, key="m_amnog") / 100

        # ─── Product 3: Tyrvaya ─────────────────────────────────
        with st.expander("P3: Tyrvaya (Trockenes Auge)", expanded=False):
            t_launch = st.number_input("Launch Monat", 24, 72, 42, key="t_lm")
            t_eligible = st.number_input("Diagn. DED-Patienten", 500_000, 3_000_000, 1_700_000, 100_000, key="t_elig")
            t_growth = st.slider("Marktwachstum /Jahr (%)", 0, 15, 6, key="t_growth") / 100
            t_addressable = st.slider("Adressierbar (%)", 3, 30, 12, key="t_addr") / 100
            t_compliance = st.slider("Compliance (%)", 40, 85, 65, key="t_comp") / 100
            t_share = st.slider("Peak Marktanteil (%)", 5, 40, 20, key="t_share") / 100
            t_speed = st.slider("Adoption (Mon. bis ~80% Peak)", 18, 48, 30, key="t_speed")
            t_price = st.number_input("Preis/Monat (EUR)", 80.0, 250.0, 140.0, 10.0, key="t_price")
            t_amnog_cut = st.slider("AMNOG-Preisabschlag (%)", 5, 40, 15, key="t_amnog") / 100

        # ─── Field Force ────────────────────────────────────────
        with st.expander("Aussendienst & GTM", expanded=False):
            ff_reps_peak = st.number_input("Peak Sales Reps", 10, 80, 45, 5, key="ff_reps")
            ff_msls = st.number_input("Peak MSLs", 3, 25, 12, key="ff_msls")
            ff_launch_mktg = st.number_input("Launch-Marketing/Mon. (EUR)", 100_000, 1_000_000, 400_000, 50_000, key="ff_mktg")
            ff_synergy_p2 = st.slider("Synergie P2 (Kostenanteil %)", 40, 100, 70, key="ff_syn2") / 100
            ff_synergy_p3 = st.slider("Synergie P3 (Kostenanteil %)", 30, 100, 80, key="ff_syn3") / 100

    # ─── Apply scenario overrides ──────────────────────────────
    # NOTE: Scenarios only override NON-slider params (launch timing, reps).
    # All slider-based values (share, speed, price) always come from the sidebar
    # so the user sees exactly what the model uses.
    if scenario == "Aggressiv (schneller Aufbau)":
        m_launch, t_launch = 12, 30
        ff_reps_peak = 60
    elif scenario == "Konservativ (Tyrvaya verzoegert)":
        t_launch = 60
        ff_reps_peak = 35

    # ─── Build product params ──────────────────────────────────
    p1 = default_ryzumvi()
    p1.launch_month = r_launch
    p1.eligible_patients = r_eligible
    p1.market_growth_annual = r_growth
    p1.addressable_pct = r_addressable
    p1.peak_market_share = r_share
    p1.launch_price_monthly = r_price
    p1.amnog_price_cut_pct = r_amnog_cut
    p1.adoption_speed = r_speed

    p2 = default_mr141()
    p2.launch_month = m_launch
    p2.eligible_patients = m_eligible
    p2.market_growth_annual = m_growth
    p2.addressable_pct = m_addressable
    p2.peak_market_share = m_share
    p2.launch_price_monthly = m_price
    p2.amnog_price_cut_pct = m_amnog_cut
    p2.adoption_speed = m_speed
    p2.compliance_rate = m_compliance

    p3 = default_tyrvaya()
    p3.launch_month = t_launch
    p3.eligible_patients = t_eligible
    p3.market_growth_annual = t_growth
    p3.addressable_pct = t_addressable
    p3.peak_market_share = t_share
    p3.launch_price_monthly = t_price
    p3.amnog_price_cut_pct = t_amnog_cut
    p3.adoption_speed = t_speed
    p3.compliance_rate = t_compliance

    products = [p1, p2, p3]

    ff = FieldForceParams(
        reps_peak=ff_reps_peak,
        msls_peak=ff_msls,
        launch_marketing_monthly=ff_launch_mktg,
        synergy_factor_p2=ff_synergy_p2,
        synergy_factor_p3=ff_synergy_p3,
    )

    df = forecast_ophthalmology(products, ff, forecast_months=84)
    kpis = calculate_kpis_ophthalmology(df, products)

    # ═══════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("## Eye Care Franchise – Specialty Ophthalmology Portfolio")
    st.caption(f"Sequenzieller Markteintritt DE | Szenario: **{scenario}** | 3 Produkte, 7-Jahres-Horizont")

    # ═══════════════════════════════════════════════════════════════════
    # KPI CARDS – Row 1: Portfolio + Product Split
    # ═══════════════════════════════════════════════════════════════════
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Portfolio-Umsatz 7J</div>
            <div class="kpi-value">EUR {kpis['total_7y_revenue']/1e6:.0f}M</div>
            <div class="kpi-sublabel">Alle 3 Produkte</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">RYZUMVI (Mydriase)</div>
            <div class="kpi-value">EUR {kpis.get('ryzumvi_total_revenue',0)/1e6:.0f}M / {kpis.get('ryzumvi_revenue_share',0):.0%}</div>
            <div class="kpi-sublabel">ab Monat 1</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">MR-141 (Presbyopie)</div>
            <div class="kpi-value">EUR {kpis.get('mr141_total_revenue',0)/1e6:.0f}M / {kpis.get('mr141_revenue_share',0):.0%}</div>
            <div class="kpi-sublabel">ab Monat {products[1].launch_month}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Tyrvaya (DED)</div>
            <div class="kpi-value">EUR {kpis.get('tyrvaya_total_revenue',0)/1e6:.0f}M / {kpis.get('tyrvaya_revenue_share',0):.0%}</div>
            <div class="kpi-sublabel">ab Monat {products[2].launch_month}</div>
        </div>""", unsafe_allow_html=True)

    # KPI Row 2: Financial KPIs
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Portfolio-Gewinn 7J</div>
            <div class="kpi-value">EUR {kpis['total_7y_profit']/1e6:.0f}M</div>
            <div class="kpi-sublabel">nach GTM-Kosten</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">GTM-Invest 7J</div>
            <div class="kpi-value">EUR {kpis['total_7y_gtm_cost']/1e6:.0f}M</div>
            <div class="kpi-sublabel">AD + MSL + Marketing</div>
        </div>""", unsafe_allow_html=True)
    with c7:
        be = kpis.get("breakeven_month")
        be_text = f"Monat {be}" if be else "–"
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Break-Even</div>
            <div class="kpi-value">{be_text}</div>
            <div class="kpi-sublabel">Kum. Gewinn > 0</div>
        </div>""", unsafe_allow_html=True)
    with c8:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">ROI (7 Jahre)</div>
            <div class="kpi-value">{kpis['final_roi']:.1f}x</div>
            <div class="kpi-sublabel">Gewinn / GTM-Invest</div>
        </div>""", unsafe_allow_html=True)

    # ─── Helper: staggered launch markers ────────────────────────
    def _add_launch_markers(fig, products_list):
        """Add launch vlines with staggered labels inside the plot area."""
        y_positions = [0.95, 0.88, 0.81]  # inside chart, staggered top-down
        for i, p in enumerate(products_list):
            fig.add_vline(x=p.launch_month, line_dash="dot", line_color="#ccc")
            fig.add_annotation(
                x=p.launch_month, y=y_positions[i % len(y_positions)],
                yref="paper", text=f"▾ {p.name}",
                showarrow=False, font=dict(size=9, color="#94a3b8"),
            )

    # ═══════════════════════════════════════════════════════════════════
    # CHARTS
    # ═══════════════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Portfolio-Umsatz", "Produkt-Detail", "Aussendienst & GTM",
        "Facharzt-Adoption", "AMNOG-Pricing"
    ])

    # ─── Tab 1: Portfolio Revenue ─────────────────────────────────
    with tab1:
        fig1 = go.Figure()
        colors = {"ryzumvi": TEAL, "mr141": BLUE, "tyrvaya": AMBER}
        names = {"ryzumvi": "RYZUMVI (Mydriase)", "mr141": "MR-141 (Presbyopie)", "tyrvaya": "Tyrvaya (DED)"}
        for p in products:
            fig1.add_trace(go.Scatter(
                x=df["month"], y=df[f"{p.code}_revenue"],
                name=names[p.code], stackgroup="one",
                line=dict(color=colors[p.code]),
            ))
        # Launch markers
        _add_launch_markers(fig1, products)
        fig1.update_layout(
            title="Portfolio-Umsatz nach Produkt (monatlich)",
            xaxis_title="Monate", yaxis_title="EUR",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, traceorder="reversed"),
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Cumulative
        col_a, col_b = st.columns(2)
        with col_a:
            fig1b = go.Figure()
            fig1b.add_trace(go.Scatter(
                x=df["month"], y=df["cumulative_revenue"],
                name="Kum. Umsatz", line=dict(color=BLUE, width=2.5),
            ))
            fig1b.add_trace(go.Scatter(
                x=df["month"], y=df["cumulative_profit"],
                name="Kum. Gewinn", line=dict(color=GREEN, width=2.5),
            ))
            fig1b.add_trace(go.Scatter(
                x=df["month"], y=df["cumulative_gtm_cost"],
                name="Kum. GTM-Invest", line=dict(color=RED, width=1.5, dash="dot"),
            ))
            fig1b.update_layout(
                title="Kumuliert: Umsatz, Gewinn, Invest",
                xaxis_title="Monate", yaxis_title="EUR", height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig1b, use_container_width=True)

        with col_b:
            fig1c = go.Figure()
            fig1c.add_trace(go.Scatter(
                x=df["month"], y=df["roi"],
                name="ROI", line=dict(color=PURPLE, width=3),
                fill="tozeroy", fillcolor="rgba(124,58,237,0.08)",
            ))
            fig1c.add_hline(y=1.0, line_dash="dash", line_color="#999",
                            annotation_text="Break-Even (1.0x)")
            fig1c.update_layout(
                title="Return on Investment (kumuliert)",
                xaxis_title="Monate", yaxis_title="ROI (x)", height=380,
            )
            st.plotly_chart(fig1c, use_container_width=True)

    # ─── Tab 2: Product Detail ────────────────────────────────────
    with tab2:
        for p in products:
            st.markdown(f"### {names[p.code]}")
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                st.metric("Peak Patienten/Mon.", f"{kpis.get(f'{p.code}_peak_patients', 0):,}")
            with pc2:
                _peak_rev = kpis.get(f'{p.code}_peak_revenue_month', 0)
                st.metric("Peak Umsatz/Mon.", f"EUR {_peak_rev/1e6:.2f}M")
            with pc3:
                st.metric("7J Umsatz", f"EUR {kpis.get(f'{p.code}_total_revenue', 0)/1e6:.0f}M")

            fig_p = make_subplots(specs=[[{"secondary_y": True}]])
            fig_p.add_trace(go.Bar(
                x=df["month"], y=df[f"{p.code}_revenue"],
                name="Umsatz", marker_color=colors[p.code], opacity=0.6,
            ), secondary_y=False)
            fig_p.add_trace(go.Scatter(
                x=df["month"], y=df[f"{p.code}_patients"],
                name="Patienten", line=dict(color=RED, width=2),
            ), secondary_y=True)
            if p.launch_month > 1:
                fig_p.add_vline(x=p.launch_month, line_dash="dot",
                                annotation_text="Launch")
            if p.amnog_month > 0:
                fig_p.add_vline(x=p.amnog_month, line_dash="dash", line_color=AMBER,
                                annotation_text="AMNOG")
            fig_p.update_layout(
                title=f"{p.name}: Umsatz & Patienten",
                xaxis_title="Monate", height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            fig_p.update_yaxes(title_text="EUR/Monat", secondary_y=False)
            fig_p.update_yaxes(title_text="Patienten", secondary_y=True)
            st.plotly_chart(fig_p, use_container_width=True)

    # ─── Tab 3: Field Force & GTM ─────────────────────────────────
    with tab3:
        col_c, col_d = st.columns(2)
        with col_c:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=df["month"], y=df["ff_reps"],
                name="Sales Reps", line=dict(color=BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(30,58,95,0.1)",
            ))
            fig3.add_trace(go.Scatter(
                x=df["month"], y=df["ff_msls"],
                name="MSLs", line=dict(color=TEAL, width=2.5),
                fill="tozeroy", fillcolor="rgba(13,148,136,0.1)",
            ))
            _add_launch_markers(fig3, products)
            fig3.update_layout(
                title="Aussendienst-Aufbau", xaxis_title="Monate",
                yaxis_title="Anzahl", height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig3, use_container_width=True)

        with col_d:
            fig3b = go.Figure()
            fig3b.add_trace(go.Scatter(
                x=df["month"], y=df["ff_rep_cost"],
                name="AD-Kosten", stackgroup="one", line=dict(color=BLUE),
            ))
            fig3b.add_trace(go.Scatter(
                x=df["month"], y=df["ff_msl_cost"],
                name="MSL-Kosten", stackgroup="one", line=dict(color=TEAL),
            ))
            fig3b.add_trace(go.Scatter(
                x=df["month"], y=df["ff_marketing"],
                name="Marketing", stackgroup="one", line=dict(color=AMBER),
            ))
            fig3b.add_trace(go.Scatter(
                x=df["month"], y=df["ff_congress_kol"],
                name="Kongresse & KOL", stackgroup="one", line=dict(color=PURPLE),
            ))
            fig3b.add_trace(go.Scatter(
                x=df["month"], y=df["ff_digital"],
                name="Digital", stackgroup="one", line=dict(color=GREEN),
            ))
            _add_launch_markers(fig3b, products)
            fig3b.update_layout(
                title="GTM-Kosten nach Kategorie", xaxis_title="Monate",
                yaxis_title="EUR/Monat", height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig3b, use_container_width=True)

        # Efficiency metric
        fig3c = go.Figure()
        revenue_per_rep = [
            df.loc[i, "total_revenue"] / max(1, df.loc[i, "ff_reps"])
            for i in range(len(df))
        ]
        fig3c.add_trace(go.Scatter(
            x=df["month"], y=revenue_per_rep,
            name="Umsatz pro Rep", line=dict(color=INDIGO, width=2.5),
        ))
        _add_launch_markers(fig3c, products)
        fig3c.update_layout(
            title="Effizienz: Umsatz pro Sales Rep/Monat",
            xaxis_title="Monate", yaxis_title="EUR/Rep/Monat", height=350,
        )
        st.plotly_chart(fig3c, use_container_width=True)

    # ─── Tab 4: Facharzt Adoption ─────────────────────────────────
    with tab4:
        col_e, col_f = st.columns(2)
        with col_e:
            fig5 = go.Figure()
            for p in products:
                fig5.add_trace(go.Scatter(
                    x=df["month"], y=df[f"{p.code}_prescribers"],
                    name=names[p.code], line=dict(color=colors[p.code], width=2.5),
                ))
            fig5.add_hline(y=6_600, line_dash="dash", line_color="#ccc",
                           annotation_text="GKV-Augenaerzte gesamt (6.600)")
            fig5.update_layout(
                title="Verordnende Augenaerzte (S-Kurve)",
                xaxis_title="Monate", yaxis_title="Anzahl Verordner",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig5, use_container_width=True)

        with col_f:
            fig5b = go.Figure()
            for p in products:
                fig5b.add_trace(go.Scatter(
                    x=df["month"], y=df[f"{p.code}_share"],
                    name=names[p.code], line=dict(color=colors[p.code], width=2.5),
                ))
            fig5b.update_layout(
                title="Marktanteil-Entwicklung",
                xaxis_title="Monate", yaxis_title="Marktanteil",
                yaxis_tickformat=".0%", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig5b, use_container_width=True)

    # ─── Tab 5: AMNOG Pricing ─────────────────────────────────────
    with tab5:
        fig4 = go.Figure()
        for p in products:
            fig4.add_trace(go.Scatter(
                x=df["month"], y=df[f"{p.code}_price"],
                name=names[p.code], line=dict(color=colors[p.code], width=2.5),
            ))
            # AMNOG marker
            if p.amnog_month > 0 and p.amnog_month <= 84:
                fig4.add_annotation(
                    x=p.amnog_month, y=df.loc[df["month"] == min(p.amnog_month, 84)].iloc[0][f"{p.code}_price"] if len(df[df["month"] == min(p.amnog_month, 84)]) > 0 else 0,
                    text=f"AMNOG {p.name}", showarrow=True, arrowhead=2,
                    arrowcolor=AMBER, font=dict(size=10),
                )
        fig4.update_layout(
            title="Preisentwicklung (AMNOG-Lebenszyklus)",
            xaxis_title="Monate", yaxis_title="EUR/Monat bzw. EUR/Behandlung",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig4, use_container_width=True)

        st.info("""
        **AMNOG-Pricing:** Jedes Produkt startet mit freier Preissetzung (Phase 1).
        Nach 6 Monaten erfolgt die G-BA Nutzenbewertung (IQWiG-Gutachten).
        Der verhandelte Erstattungsbetrag gilt ab Monat 7 und unterliegt
        anschliessend einer jaehrlichen Erosion durch Wettbewerb und Generika.
        """)

    # ═══════════════════════════════════════════════════════════════════
    # SCENARIO COMPARISON
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Szenario-Vergleich")

    scenarios_def = {
        "Konservativ": {"t_launch": 60, "t_share": 0.12, "ff_peak": 35, "m_launch": 24,
                        "r_speed": 24, "m_speed": 30, "t_speed": 36, "r_share": 0.40},
        "Base Case": {"t_launch": 42, "t_share": 0.20, "ff_peak": 45, "m_launch": 18,
                      "r_speed": 18, "m_speed": 24, "t_speed": 30, "r_share": 0.50},
        "Aggressiv": {"t_launch": 30, "t_share": 0.25, "ff_peak": 60, "m_launch": 12,
                      "r_speed": 12, "m_speed": 18, "t_speed": 24, "r_share": 0.60},
    }

    comp_rows = []
    for sn, ov in scenarios_def.items():
        sp1 = default_ryzumvi()
        sp1.peak_market_share = ov["r_share"]
        sp1.adoption_speed = ov["r_speed"]
        sp2 = default_mr141()
        sp2.launch_month = ov["m_launch"]
        sp2.adoption_speed = ov["m_speed"]
        sp3 = default_tyrvaya()
        sp3.launch_month = ov["t_launch"]
        sp3.peak_market_share = ov["t_share"]
        sp3.adoption_speed = ov["t_speed"]
        sff = FieldForceParams(reps_peak=ov["ff_peak"])
        sdf = forecast_ophthalmology([sp1, sp2, sp3], sff, forecast_months=84)
        sk = calculate_kpis_ophthalmology(sdf, [sp1, sp2, sp3])
        be = sk.get("breakeven_month")
        comp_rows.append({
            "Szenario": sn,
            "Umsatz 7J": f"EUR {sk['total_7y_revenue']/1e6:.0f}M",
            "Gewinn 7J": f"EUR {sk['total_7y_profit']/1e6:.0f}M",
            "GTM-Invest": f"EUR {sk['total_7y_gtm_cost']/1e6:.0f}M",
            "ROI": f"{sk['final_roi']:.1f}x",
            "Break-Even": f"M{be}" if be else "–",
            "Peak Reps": ov["ff_peak"],
        })

    st.dataframe(pd.DataFrame(comp_rows).set_index("Szenario"), width=900)

    # ═══════════════════════════════════════════════════════════════════
    # METHODOLOGY
    # ═══════════════════════════════════════════════════════════════════
    with st.expander("Methodik & Datenquellen"):
        st.markdown("""
        **Modell-Architektur:** Sequenzieller Portfolio-Launch mit AMNOG-Pricing

        | Komponente | Methodik | Referenz |
        |---|---|---|
        | Facharzt-Adoption | Logistische S-Kurve pro Produkt | Pharma Launch Benchmarks |
        | AMNOG-Pricing | 3-Phasen: Frei → G-BA → Erosion | IQWiG / GKV-SV Verfahren |
        | Field Force | Lineare Skalierung + Synergie | Branchenbenchmarks (1 Rep:100-200 Aerzte) |
        | Cross-Product Synergy | P2: 70%, P3: 80% der Standalone-Kosten | Portfolio-Effekte |
        | Wettbewerb | Jaehrl. Share-Erosion pro Produkt | iKervis, Vevizye, Vuity |

        **Datenquellen (alle oeffentlich):**
        - Oeffentliche Investor Relations / Pipeline-Informationen
        - MHRA/FDA Approvals (RYZUMVI, Tyrvaya)
        - Novaliq/Thea (Vevizye EU-Zulassung Okt 2024)
        - Santen (iKervis: EUR 120-135/Mon., Schwere Keratitis)
        - KBV/BAeK Aerztestatistik 2024 (8.250 Augenaerzte)
        - Grand View Research (DE Dry Eye Markt)
        - IQWiG AMNOG-Statistiken
        """)


if __name__ == "__main__":
    st.set_page_config(page_title="Eye Care Franchise", page_icon="👁", layout="wide")
    show()
