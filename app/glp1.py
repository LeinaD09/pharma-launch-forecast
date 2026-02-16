"""
Pharma Launch Forecast – Use Case 2: GLP-1 Brand Competition
=============================================================
Mounjaro (Tirzepatid, Lilly) vs. Ozempic/Wegovy (Semaglutid, Novo Nordisk)

Patient-based model with per-indication revenue streams.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO

from models.brand_competition_engine import (
    IndicationParams, BrandParams, MarketParams,
    forecast_brand, calculate_kpis_brand,
    default_lilly_indications, default_novo_indications,
)


def show():
    """Render the GLP-1 Brand Competition page."""
    # ─── Custom CSS ─────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0.5rem !important; }
        .kpi-card, .kpi-card-orange, .kpi-card-blue,
        .kpi-card-green, .kpi-card-red {
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
        .perspective-header {
            font-size: 16px; padding: 10px 15px; border-radius: 8px;
            margin-bottom: 20px; font-weight: 600;
        }
        .lilly-header { background-color: #fef3c7; color: #92400e; border-left: 4px solid #f59e0b; }
        .novo-header { background-color: #dbeafe; color: #1e40af; border-left: 4px solid #2563eb; }
        div[data-testid="stSidebar"] {
            background-color: #f8fafc;
            min-width: 280px !important; max-width: 320px !important; width: 300px !important;
        }
        div[data-testid="stSidebar"] [data-testid="stExpander"] { margin-bottom: -8px; }
        div[data-testid="stSidebar"] [data-testid="stExpander"] summary { font-size: 15px; font-weight: 600; }
        div[data-testid="stSidebar"] .stSlider label p { font-size: 14px !important; }
        div[data-testid="stSidebar"] h1 { font-size: 22px !important; margin-bottom: 0 !important; }
    </style>
    """, unsafe_allow_html=True)


    def fmt_eur(v, d=0):
        if abs(v) >= 1e9: return f"\u20ac{v/1e9:,.{d}f} Mrd."
        if abs(v) >= 1e6: return f"\u20ac{v/1e6:,.{d}f} Mio."
        if abs(v) >= 1e3: return f"\u20ac{v/1e3:,.{d}f}K"
        return f"\u20ac{v:,.{d}f}"

    def fmt_num(v):
        if abs(v) >= 1e6: return f"{v/1e6:,.1f} Mio."
        if abs(v) >= 1e3: return f"{v/1e3:,.0f}K"
        return f"{v:,.0f}"

    def kpi(label, value, typ="default", sub=""):
        cls = {"default": "kpi-card", "orange": "kpi-card-orange", "blue": "kpi-card-blue",
               "green": "kpi-card-green", "red": "kpi-card-red"}.get(typ, "kpi-card")
        s = f'<div class="kpi-sublabel">{sub}</div>' if sub else ""
        return f'<div class="{cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{s}</div>'


    # ─── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("GLP-1 Forecast")
        st.caption("Patientenbasiertes Modell")

        perspective = st.radio(
            "Perspektive",
            ["\U0001f7e1 Lilly (Mounjaro)", "\U0001f535 Novo Nordisk (Ozempic)"],
            index=0, horizontal=True,
        )
        is_lilly = "Lilly" in perspective

        scenario = st.selectbox(
            "Szenario", ["Base Case", "Bull (Lilly)", "Bull (Novo)"],
            index=0, label_visibility="collapsed",
        )

        # Reset sliders when scenario changes so defaults take effect
        _prev = st.session_state.get("_glp1_prev_scenario")
        if _prev is not None and _prev != scenario:
            for k in list(st.session_state):
                if k.startswith(("t2d_", "adipo_", "cv_", "mash_", "comp_",
                                 "Horizont", "COGS", "SGA", "supply_")):
                    st.session_state.pop(k, None)
            st.session_state["_glp1_prev_scenario"] = scenario
            st.rerun()
        st.session_state["_glp1_prev_scenario"] = scenario

        # Scenario defaults
        sc = {
            "Base Case":    {"t2d_peak": 25, "adipo_peak": 35, "months": 36, "adipo_gkv": False, "t2d_pen": 22, "comp_t2d": 30},
            "Bull (Lilly)": {"t2d_peak": 35, "adipo_peak": 45, "months": 24, "adipo_gkv": True, "t2d_pen": 28, "comp_t2d": 25},
            "Bull (Novo)":  {"t2d_peak": 15, "adipo_peak": 20, "months": 48, "adipo_gkv": False, "t2d_pen": 20, "comp_t2d": 38},
        }[scenario]

        forecast_years = st.slider("Horizont (Jahre)", 1, 7, 5)

        # ─── T2D ──────────────────────────────────────────────────────
        with st.expander("Diabetes (T2D)", expanded=True):
            st.caption("6,33 Mio. T2D-Patienten in Deutschland")
            t2d_pen = st.slider(
                "GLP-1-Behandlungsrate Ziel (%)",
                10, 35, sc["t2d_pen"], 1,
                key="t2d_pen",
                help="Anteil der T2D-Patienten, die mit GLP-1 behandelt werden",
            )
            t2d_peak = st.slider(
                "Mein Marktanteil Peak (%)",
                5, 40, sc["t2d_peak"], 1,
                key="t2d_peak",
                help="Angestrebter Spitzenanteil im T2D-Segment",
            )
            t2d_price = st.slider(
                "Preis / Monat (\u20ac)",
                150, 500, 350 if is_lilly else 300, 25,
                key="t2d_price",
                help="Monatlicher Therapiepreis T2D",
            )
            t2d_persist = st.slider(
                "Therapietreue nach 12 Mon. (%)",
                30, 95, 70, 5,
                key="t2d_persist",
                help="Anteil der Patienten, die nach 12 Monaten noch therapiert werden",
            )

        # ─── Adipositas ────────────────────────────────────────────────
        with st.expander("Adipositas", expanded=False):
            st.caption("8 Mio. potenzielle Patienten (BMI \u2265 30)")
            adipo_gkv = st.checkbox(
                "GKV-Erstattung",
                value=sc["adipo_gkv"],
                key="adipo_gkv",
                help="Falls ja: Massiver Nachfrageanstieg durch Erstattung",
            )
            if adipo_gkv:
                adipo_pen = st.slider(
                    "Behandlungsrate Ziel (%)",
                    1.0, 10.0, 5.0, 0.5,
                    key="adipo_pen_gkv",
                    help="Bei GKV-Erstattung: deutlich hoehere Behandlungsrate",
                )
            else:
                adipo_pen = st.slider(
                    "Behandlungsrate Ziel (%)",
                    0.5, 5.0, 1.5, 0.5,
                    key="adipo_pen_nogkv",
                    help="Ohne GKV: nur Selbstzahler",
                )
            adipo_peak = st.slider(
                "Mein Marktanteil Peak (%)",
                5, 50, sc["adipo_peak"], 5,
                key="adipo_peak",
            )
            adipo_price = st.slider(
                "Preis / Monat (\u20ac)",
                150, 500, 300 if is_lilly else 277, 25,
                key="adipo_price",
            )
            adipo_persist = st.slider(
                "Therapietreue nach 12 Mon. (%)",
                20, 80, 45, 5,
                key="adipo_persist",
                help="Adipositas: niedrigere Adhearenz als T2D",
            )

        # ─── CV-Risiko ─────────────────────────────────────────────────
        with st.expander("CV-Risikoreduktion", expanded=False):
            cv_enabled = st.checkbox(
                "Indikation aktiv",
                value=False,
                key="cv_enabled",
                help="Kardiovaskulaere Risikoreduktion (noch nicht zugelassen)",
            )
            if cv_enabled:
                cv_peak = st.slider("Mein Marktanteil Peak (%)", 5, 30, 20, 5, key="cv_peak")
                cv_price = st.slider("Preis / Monat (\u20ac)", 200, 500, 350, 25, key="cv_price")
                cv_persist = st.slider("Therapietreue 12 Mon. (%)", 30, 90, 65, 5, key="cv_persist")
            else:
                cv_peak, cv_price, cv_persist = 20, 350, 65

        # ─── MASH ──────────────────────────────────────────────────────
        with st.expander("MASH / NASH", expanded=False):
            mash_enabled = st.checkbox(
                "Indikation aktiv",
                value=False,
                key="mash_enabled",
                help="Lebererkrankung (MASH/NASH, Studien laufen)",
            )
            if mash_enabled:
                mash_peak = st.slider("Mein Marktanteil Peak (%)", 5, 30, 25, 5, key="mash_peak")
                mash_price = st.slider("Preis / Monat (\u20ac)", 200, 500, 350, 25, key="mash_price")
                mash_persist = st.slider("Therapietreue 12 Mon. (%)", 30, 90, 60, 5, key="mash_persist")
            else:
                mash_peak, mash_price, mash_persist = 25, 350, 60

        # ─── Wettbewerber ──────────────────────────────────────────────
        with st.expander("Wettbewerber", expanded=False):
            comp_label = "Novo Nordisk" if is_lilly else "Eli Lilly"
            st.caption(f"Hauptwettbewerber: {comp_label}")
            comp_t2d_peak = st.slider(
                f"{comp_label} Peak Share T2D (%)",
                10, 40, sc["comp_t2d"], 1,
                key="comp_t2d_peak",
            )
            comp_t2d_price = st.slider(
                f"{comp_label} Preis T2D (\u20ac/Mon.)",
                200, 500, 300 if is_lilly else 350, 25,
                key="comp_t2d_price",
            )
            comp_supply = st.checkbox(
                "Lieferengpass aktiv",
                value=True if is_lilly else False,
                key="comp_supply",
                help="Lieferengpass des Wettbewerbers",
            )
            if comp_supply:
                comp_supply_end = st.slider(
                    "Engpass endet (Monat)",
                    0, 24, 12, 3,
                    key="comp_supply_end",
                )
            else:
                comp_supply_end = 0

        # ─── Kosten & Supply ───────────────────────────────────────────
        with st.expander("Kosten & Supply", expanded=False):
            cogs_pct = st.slider("COGS (%)", 10, 40, 20, 5, key="COGS")
            sga = st.number_input("SG&A / Monat (\u20ac)", 200_000, 2_000_000, 800_000, 100_000, key="SGA")
            my_supply = st.checkbox("Eigener Lieferengpass", value=False, key="supply_own")
            if my_supply:
                supply_cap = st.slider("Kapazitaet (Patienten/Mon.)", 50_000, 500_000, 200_000, 50_000, key="supply_cap")
                supply_end = st.slider("Normalisierung (Monat)", 6, 36, 18, 3, key="supply_end")
            else:
                supply_cap, supply_end = 200_000, 0

        months_peak = sc["months"]

    # ─── Build Indication Params ───────────────────────────────────────────
    if is_lilly:
        defaults = default_lilly_indications()
    else:
        defaults = default_novo_indications()

    # T2D
    ind_t2d = defaults[0]
    ind_t2d.treated_pct_peak = t2d_pen / 100
    ind_t2d.my_share_peak = t2d_peak / 100
    ind_t2d.months_to_peak_share = months_peak
    ind_t2d.price_per_month = t2d_price
    ind_t2d.persistence_12m = t2d_persist / 100
    ind_t2d.competitor_share_peak = comp_t2d_peak / 100
    ind_t2d.competitor_price_per_month = comp_t2d_price

    # Adipositas
    ind_adipo = defaults[1]
    ind_adipo.treated_pct_peak = adipo_pen / 100
    ind_adipo.my_share_peak = adipo_peak / 100
    ind_adipo.months_to_peak_share = months_peak
    ind_adipo.price_per_month = adipo_price
    ind_adipo.persistence_12m = adipo_persist / 100
    ind_adipo.gkv_covered = adipo_gkv

    # CV-Risiko
    ind_cv = defaults[2]
    ind_cv.enabled = cv_enabled
    ind_cv.my_share_peak = cv_peak / 100
    ind_cv.price_per_month = cv_price
    ind_cv.persistence_12m = cv_persist / 100

    # MASH
    ind_mash = defaults[3]
    ind_mash.enabled = mash_enabled
    ind_mash.my_share_peak = mash_peak / 100
    ind_mash.price_per_month = mash_price
    ind_mash.persistence_12m = mash_persist / 100

    indications = [ind_t2d, ind_adipo, ind_cv, ind_mash]

    brand = BrandParams(
        name="Mounjaro (Tirzepatid)" if is_lilly else "Ozempic / Wegovy (Semaglutid)",
        company="Eli Lilly" if is_lilly else "Novo Nordisk",
        indications=indications,
        supply_constrained=my_supply,
        supply_capacity_monthly_patients=supply_cap,
        supply_normalization_month=supply_end,
        cogs_pct=cogs_pct / 100,
        sga_monthly_eur=sga,
        price_trend_annual=-0.03,
    )

    # ─── Run Forecast ─────────────────────────────────────────────────────
    df = forecast_brand(brand, forecast_months=forecast_years * 12)
    kpis = calculate_kpis_brand(df)

    # ─── Main ─────────────────────────────────────────────────────────────
    st.title("GLP-1 Markt \u2013 Brand Competition Forecast")
    comp_name = "Ozempic / Wegovy" if is_lilly else "Mounjaro"
    st.markdown(
        f"**Patientenbasiertes Modell** | "
        f"**{brand.name}** vs. **{comp_name}**"
    )

    header_cls = "lilly-header" if is_lilly else "novo-header"
    icon = "\U0001f7e1" if is_lilly else "\U0001f535"
    st.markdown(
        f'<div class="perspective-header {header_cls}">'
        f'{icon} Perspektive: {brand.company} \u2013 {brand.name}</div>',
        unsafe_allow_html=True,
    )

    # ─── KPI Row 1 ──────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    color = "orange" if is_lilly else "blue"
    with c1:
        st.markdown(kpi("Umsatz Jahr 1", fmt_eur(kpis["year1_revenue"]), color), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi(f"Umsatz {forecast_years}J", fmt_eur(kpis["total_5y_revenue"]), color), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Peak Patienten", fmt_num(kpis["peak_patients"]), color), unsafe_allow_html=True)
    with c4:
        ot = kpis.get("overtake_month")
        ot_text = f"Monat {ot}" if ot else "\u2013"
        st.markdown(kpi("Market Leader ab", ot_text, "green" if ot else "default"), unsafe_allow_html=True)

    # ─── KPI Row 2 ──────────────────────────────────────────────────────
    st.markdown("")
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        t2d_rev = kpis["revenue_by_indication"].get("t2d", 0)
        st.markdown(kpi("davon T2D", fmt_eur(t2d_rev), sub="5-Jahres-Umsatz"), unsafe_allow_html=True)
    with c6:
        adipo_rev = kpis["revenue_by_indication"].get("adipositas", 0)
        st.markdown(kpi("davon Adipositas", fmt_eur(adipo_rev), sub="5-Jahres-Umsatz"), unsafe_allow_html=True)
    with c7:
        st.markdown(kpi(f"Gewinn {forecast_years}J", fmt_eur(kpis["total_5y_profit"]),
                         "green" if kpis["total_5y_profit"] > 0 else "red"), unsafe_allow_html=True)
    with c8:
        st.markdown(kpi("Durchschn. Preis", f"\u20ac{kpis['avg_price']:,.0f}/Mon."), unsafe_allow_html=True)

    st.markdown("")

    # ─── Indication colors ─────────────────────────────────────────────
    IND_COLORS = {
        "t2d": "#3b82f6",          # blue
        "adipositas": "#22c55e",   # green
        "cvrisiko": "#a855f7",     # purple
        "mash": "#f59e0b",         # amber
    }

    # ─── Charts Row 1: Patients by Indication + Revenue by Indication ──
    col1, col2 = st.columns(2)

    # Helper: get indication column keys
    ind_keys = []
    for ind in brand.indications:
        key = ind.name.lower().replace("-", "").replace("/", "").replace(" ", "_")
        ind_keys.append((ind.name, key))

    with col1:
        fig = go.Figure()
        for ind_name, key in ind_keys:
            col_name = f"patients_{key}"
            if col_name in df.columns and df[col_name].sum() > 0:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df[col_name], mode="lines",
                    name=ind_name, stackgroup="one",
                    line=dict(color=IND_COLORS.get(key, "#94a3b8"), width=0),
                    fillcolor=IND_COLORS.get(key, "#94a3b8"),
                    hovertemplate="%{y:,.0f} Pat.<extra></extra>",
                ))
        fig.update_layout(
            title="Patienten nach Indikation",
            yaxis_title="Patienten / Monat",
            template="plotly_white", height=420,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        for ind_name, key in ind_keys:
            col_name = f"revenue_{key}"
            if col_name in df.columns and df[col_name].sum() > 0:
                fig2.add_trace(go.Bar(
                    x=df["date"], y=df[col_name], name=ind_name,
                    marker_color=IND_COLORS.get(key, "#94a3b8"),
                    hovertemplate="%{y:\u20ac,.0f}<extra></extra>",
                ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            x=df["date"], y=df["cumulative_revenue"], mode="lines",
            name="Kumuliert", line=dict(color="#166534", width=3),
            hovertemplate="%{y:\u20ac,.0f}<extra></extra>",
        ), secondary_y=True)
        fig2.update_layout(
            title="Umsatz nach Indikation",
            barmode="stack", template="plotly_white", height=420,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        fig2.update_yaxes(title_text="Monatlich (EUR)", secondary_y=False)
        fig2.update_yaxes(title_text="Kumuliert (EUR)", secondary_y=True)
        st.plotly_chart(fig2, use_container_width=True)

    # ─── Charts Row 2: Share Race + Revenue Comparison ──────────────────
    col3, col4 = st.columns(2)

    my_color = "#f59e0b" if is_lilly else "#2563eb"
    comp_color = "#2563eb" if is_lilly else "#f59e0b"

    with col3:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df["date"], y=df["my_share_weighted"], mode="lines",
            name=brand.name.split("(")[0].strip(),
            line=dict(color=my_color, width=3),
            fill="tozeroy",
            fillcolor=f"rgba({','.join(str(int(my_color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.15)",
            hovertemplate="%{y:.1%}<extra></extra>",
        ))
        fig3.add_trace(go.Scatter(
            x=df["date"], y=df["comp_share_weighted"], mode="lines",
            name=comp_name.split("(")[0].strip(),
            line=dict(color=comp_color, width=3, dash="dash"),
            hovertemplate="%{y:.1%}<extra></extra>",
        ))
        fig3.update_layout(
            title="Marktanteils-Wettlauf (gewichtet)",
            yaxis_title="Marktanteil", yaxis_tickformat=".0%",
            template="plotly_white", height=420,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=df["date"], y=df["my_revenue"], name=brand.company,
            marker_color=my_color,
            hovertemplate="%{y:\u20ac,.0f}<extra></extra>",
        ))
        fig4.add_trace(go.Bar(
            x=df["date"], y=df["comp_revenue"], name=comp_name.split("(")[0].strip(),
            marker_color=comp_color,
            hovertemplate="%{y:\u20ac,.0f}<extra></extra>",
        ))
        fig4.update_layout(
            title="Umsatzvergleich (monatlich)",
            barmode="group", yaxis_title="Umsatz (EUR)",
            template="plotly_white", height=420,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ─── Charts Row 3: Persistence Effect + Profitability ──────────────
    col5, col6 = st.columns(2)

    with col5:
        # Stacked bar: theoretical patients vs actual (with persistence gap)
        fig5 = go.Figure()
        # We can show demand vs actual patients
        fig5.add_trace(go.Scatter(
            x=df["date"], y=df["my_patients"], mode="lines",
            name="Tatsaechliche Patienten",
            line=dict(color=my_color, width=3),
            fill="tozeroy",
            fillcolor=f"rgba({','.join(str(int(my_color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.2)",
            hovertemplate="%{y:,.0f}<extra></extra>",
        ))
        fig5.add_trace(go.Scatter(
            x=df["date"], y=df["comp_patients"], mode="lines",
            name="Wettbewerber Patienten",
            line=dict(color=comp_color, width=2, dash="dash"),
            hovertemplate="%{y:,.0f}<extra></extra>",
        ))
        fig5.update_layout(
            title="Patienten-Wettlauf",
            yaxis_title="Patienten / Monat",
            template="plotly_white", height=350,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col6:
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            x=df["date"], y=df["my_revenue"], name="Umsatz",
            marker_color="#86efac",
        ))
        fig6.add_trace(go.Bar(
            x=df["date"], y=[-c for c in df["my_cogs"]], name="COGS",
            marker_color="#fca5a5",
        ))
        fig6.add_trace(go.Scatter(
            x=df["date"], y=df["cumulative_profit"], mode="lines",
            name="Kum. Gewinn", line=dict(color="#166534", width=3), yaxis="y2",
        ))
        fig6.update_layout(
            title="Profitabilitaet", barmode="relative",
            yaxis=dict(title="Monatlich (EUR)"),
            yaxis2=dict(title="Kumuliert (EUR)", overlaying="y", side="right"),
            template="plotly_white", height=350, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig6, use_container_width=True)

    # ─── Supply Gap (if applicable) ─────────────────────────────────────
    if df["supply_gap"].sum() > 0:
        fig_sg = go.Figure()
        fig_sg.add_trace(go.Bar(
            x=df["date"], y=df["supply_gap"], name="Ungedeckte Nachfrage",
            marker_color="#ef4444",
        ))
        fig_sg.update_layout(
            title="Supply Gap: Nachfrage vs. Lieferkapazitaet",
            yaxis_title="Fehlende Patienten", template="plotly_white", height=280,
        )
        st.plotly_chart(fig_sg, use_container_width=True)

    # ─── Detail Table ───────────────────────────────────────────────────
    with st.expander("Detaildaten"):
        disp_cols = ["month", "my_patients", "my_revenue", "my_share_weighted",
                     "comp_share_weighted", "comp_patients", "comp_revenue",
                     "my_operating_profit", "cumulative_revenue", "cumulative_profit"]
        # Add per-indication patient columns
        for ind_name, key in ind_keys:
            pcol = f"patients_{key}"
            if pcol in df.columns:
                disp_cols.append(pcol)

        disp = df[disp_cols].copy()
        rename_map = {
            "month": "Monat",
            "my_patients": "Meine Pat.",
            "my_revenue": "Umsatz",
            "my_share_weighted": "Mein Anteil",
            "comp_share_weighted": "Comp. Anteil",
            "comp_patients": "Comp. Pat.",
            "comp_revenue": "Comp. Umsatz",
            "my_operating_profit": "Oper. Gewinn",
            "cumulative_revenue": "Kum. Umsatz",
            "cumulative_profit": "Kum. Gewinn",
        }
        for ind_name, key in ind_keys:
            pcol = f"patients_{key}"
            if pcol in disp.columns:
                rename_map[pcol] = f"Pat. {ind_name}"
        disp = disp.rename(columns=rename_map)

        disp["Mein Anteil"] = disp["Mein Anteil"].apply(lambda x: f"{x:.1%}")
        disp["Comp. Anteil"] = disp["Comp. Anteil"].apply(lambda x: f"{x:.1%}")
        for c in ["Meine Pat.", "Comp. Pat."] + [f"Pat. {n}" for n, _ in ind_keys if f"patients_{_}" in df.columns]:
            if c in disp.columns:
                disp[c] = disp[c].apply(lambda x: f"{x:,.0f}")
        for c in ["Umsatz", "Comp. Umsatz", "Oper. Gewinn", "Kum. Umsatz", "Kum. Gewinn"]:
            if c in disp.columns:
                disp[c] = disp[c].apply(lambda x: f"\u20ac{x:,.0f}")
        st.dataframe(disp, use_container_width=True, hide_index=True)

    # ─── Export ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Export")
    col_e1, col_e2, _ = st.columns([1, 1, 2])
    with col_e1:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            df.drop(columns=["date"]).to_excel(w, sheet_name=brand.company, index=False)
        st.download_button("Excel herunterladen", buf.getvalue(),
                           "glp1_brand_forecast.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_e2:
        st.info(f"Perspektive: {brand.company} | Szenario: {scenario}")

    # ─── Footer ─────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Patientenbasiertes Forecast-Modell. Daten sind synthetisch, basierend auf "
        "oeffentlichen Quellen: BARMER 2025, G-BA Nutzenbewertung Tirzepatid, "
        "IQVIA Pharmamarkt 2024, EMA EPAR Mounjaro. Kein Bezug zu vertraulichen Daten."
    )


if __name__ == "__main__":
    show()
