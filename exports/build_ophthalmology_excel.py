"""
Build a professional Excel forecast model for the Eye Care Franchise Ophthalmology Portfolio.

Sheets:
1. INPUTS          - All user-configurable parameters (yellow cells)
2. Marktdaten      - Ophthalmology market, dry eye landscape, competitor overview
3. Portfolio       - Product-level monthly forecast (RYZUMVI, MR-141, Tyrvaya)
4. Forecast        - Portfolio-level monthly forecast with cumulative P&L
5. Dashboard       - Executive summary with scenario comparison
6. Methodik        - Transparency matrix: Facts vs. Assumptions vs. Models
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import xlsxwriter
import numpy as np
import pandas as pd
from models.ophthalmology_engine import (
    ProductParams, FieldForceParams, MarketParams,
    default_ryzumvi, default_mr141, default_tyrvaya,
    forecast_ophthalmology, calculate_kpis_ophthalmology,
)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Ophthalmology_Portfolio_Forecast.xlsx")


def build_model():
    wb = xlsxwriter.Workbook(OUTPUT_PATH)

    # --- Format Definitions ------------------------------------------------
    fmt = {}
    fmt["title"] = wb.add_format({"bold": True, "font_size": 16, "font_color": "#1e3a5f", "bottom": 2, "bottom_color": "#1e3a5f"})
    fmt["section"] = wb.add_format({"bold": True, "font_size": 12, "font_color": "#1e3a5f", "bg_color": "#e8f0fe", "border": 1, "border_color": "#b0c4de"})
    fmt["subsection"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "#374151", "bottom": 1, "bottom_color": "#d1d5db"})
    fmt["input"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "num_format": "#,##0", "font_color": "#1a237e", "bold": True})
    fmt["input_pct"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "num_format": "0.0%", "font_color": "#1a237e", "bold": True})
    fmt["input_eur"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "num_format": "\u20ac#,##0.00", "font_color": "#1a237e", "bold": True})
    fmt["input_text"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "font_color": "#1a237e", "bold": True})
    fmt["label"] = wb.add_format({"font_size": 10, "font_color": "#374151", "text_wrap": True, "valign": "vcenter"})
    fmt["label_bold"] = wb.add_format({"font_size": 10, "font_color": "#374151", "bold": True, "valign": "vcenter"})
    fmt["hint"] = wb.add_format({"font_size": 9, "font_color": "#9ca3af", "italic": True, "text_wrap": True, "valign": "vcenter"})
    fmt["number"] = wb.add_format({"num_format": "#,##0"})
    fmt["eur"] = wb.add_format({"num_format": "\u20ac#,##0"})
    fmt["eur_detail"] = wb.add_format({"num_format": "\u20ac#,##0.00"})
    fmt["pct"] = wb.add_format({"num_format": "0.0%"})
    fmt["mult"] = wb.add_format({"num_format": "0.00x"})
    fmt["th"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#1e3a5f", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_teal"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#134e4a", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_amber"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#92400e", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_purple"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#4c1d95", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["kpi_label"] = wb.add_format({"bold": True, "font_size": 11, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1})
    fmt["kpi_value"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "num_format": "\u20ac#,##0", "align": "center"})
    fmt["kpi_value_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#134e4a", "bg_color": "#f0fdf4", "border": 1, "num_format": "0.0%", "align": "center"})
    fmt["kpi_value_plain"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "align": "center"})
    fmt["row_alt"] = wb.add_format({"bg_color": "#f8fafc"})
    fmt["row_alt_eur"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "\u20ac#,##0"})
    fmt["row_alt_pct"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "0.0%"})
    fmt["row_alt_num"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "#,##0"})
    fmt["row_alt_mult"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "0.00x"})
    fmt["fact"] = wb.add_format({"bg_color": "#dcfce7", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})
    fmt["assumption"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})
    fmt["model"] = wb.add_format({"bg_color": "#dbeafe", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})
    fmt["gap"] = wb.add_format({"bg_color": "#fef2f2", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})

    def write_input_row(ws, row, label, value, fmt_key, hint):
        ws.write(row, 1, label, fmt["label_bold"])
        ws.write(row, 2, value, fmt[fmt_key])
        ws.write(row, 3, hint, fmt["hint"])

    # Run base case forecast
    products = [default_ryzumvi(), default_mr141(), default_tyrvaya()]
    ff = FieldForceParams()
    mkt = MarketParams()
    df = forecast_ophthalmology(products, ff, mkt, forecast_months=84)
    kpis = calculate_kpis_ophthalmology(df, products)

    # ===================================================================
    # SHEET 1: INPUTS
    # ===================================================================
    ws = wb.add_worksheet("INPUTS")
    ws.hide_gridlines(2)
    ws.set_tab_color("#E0B800")
    ws.set_column("A:A", 3)
    ws.set_column("B:B", 44)
    ws.set_column("C:C", 18)
    ws.set_column("D:D", 58)

    row = 1
    ws.merge_range(row, 1, row, 3, "Eye Care Franchise - Ophthalmology Portfolio Forecast", fmt["title"])
    row += 1
    ws.merge_range(row, 1, row, 3,
        "Sequenzieller Markteintritt DE | 3 Produkte | 7-Jahres-Horizont",
        wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    # --- P1: RYZUMVI ---
    row += 2
    ws.merge_range(row, 1, row, 3, "P1: RYZUMVI (Mydriase-Reversal)", fmt["section"])
    p1 = products[0]
    for label, value, fk, hint in [
        ("Indikation", "Mydriase-Reversal (Pupillenerweiterung)", "input_text", "Phentolamin Augentropfen, first-in-class DE"),
        ("Launch-Monat", p1.launch_month, "input", "Ab Modellstart (2026)"),
        ("Eligible Prozeduren/Jahr", p1.eligible_patients, "input", "Dilatierte Augenuntersuchungen, davon Reversal gewuenscht"),
        ("Adressierbarer Anteil", p1.addressable_pct, "input_pct", "% der Prozeduren die Reversal aktiv nutzen"),
        ("Peak Marktanteil", p1.peak_market_share, "input_pct", "First-in-class, kein Wettbewerb"),
        ("Preis/Behandlung (EUR)", p1.launch_price_monthly, "input_eur", "Einmalapplikation pro Untersuchung"),
        ("AMNOG-Abschlag", p1.amnog_price_cut_pct, "input_pct", "Einzigartig = milder Abschlag erwartet"),
        ("Adoptions-Speed (Mon.)", p1.adoption_speed, "input", "Monate bis ~80% Peak Share"),
        ("Peak verordnende Aerzte", p1.peak_prescribers, "input", "Augenaerzte die regelmaessig dilatieren"),
        ("COGS (%)", p1.cogs_pct, "input_pct", "Herstellkosten"),
        ("Royalty (%)", p1.royalty_pct, "input_pct", "Ocuphire-Lizenz"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # --- P2: MR-141 ---
    row += 2
    ws.merge_range(row, 1, row, 3, "P2: MR-141 (Presbyopie)", fmt["section"])
    p2 = products[1]
    for label, value, fk, hint in [
        ("Indikation", "Presbyopie (Altersweitsichtigkeit)", "input_text", "Phentolamin Augentropfen, taegl. Anwendung"),
        ("Launch-Monat", p2.launch_month, "input", "Ca. 1.5 Jahre nach P1"),
        ("Eligible Patienten", p2.eligible_patients, "input", "Presbyopie-Praevalenz 40+ in DE"),
        ("Adressierbarer Anteil", p2.addressable_pct, "input_pct", "Konservativ: Rx-Therapie statt Brille"),
        ("Peak Marktanteil", p2.peak_market_share, "input_pct", "Begrenzt: Vuity (AbbVie) als Wettbewerber"),
        ("Preis/Monat (EUR)", p2.launch_price_monthly, "input_eur", "Taegl. Applikation, chronisch"),
        ("AMNOG-Abschlag", p2.amnog_price_cut_pct, "input_pct", "Lifestyle-nah = haertere Verhandlung"),
        ("Adoptions-Speed (Mon.)", p2.adoption_speed, "input", "Monate bis ~80% Peak Share"),
        ("Compliance (%)", p2.compliance_rate, "input_pct", "Lifestyle = niedrigere Compliance"),
        ("Wettbewerber-Druck p.a.", p2.competitive_pressure_annual, "input_pct", "Jaehrl. Share-Erosion"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # --- P3: Tyrvaya ---
    row += 2
    ws.merge_range(row, 1, row, 3, "P3: Tyrvaya (Trockenes Auge / DED)", fmt["section"])
    p3 = products[2]
    for label, value, fk, hint in [
        ("Indikation", "Keratoconjunctivitis sicca (Trockenes Auge)", "input_text", "Vareniclin Nasenspray, neuer MOA"),
        ("Launch-Monat", p3.launch_month, "input", "EMA-Zulassung + AMNOG erforderlich (~3.5 Jahre)"),
        ("Diagn. DED-Patienten DE", p3.eligible_patients, "input", "1.5-1.9 Mio. diagnostiziert"),
        ("Adressierbarer Anteil", p3.addressable_pct, "input_pct", "Moderat-bis-schwer, Rx-geeignet"),
        ("Peak Marktanteil", p3.peak_market_share, "input_pct", "Wettbewerb: iKervis, Vevizye, Generika"),
        ("Preis/Monat (EUR)", p3.launch_price_monthly, "input_eur", "Benchmark: iKervis EUR 120-135/Mon."),
        ("AMNOG-Abschlag", p3.amnog_price_cut_pct, "input_pct", "Neuartiger MOA = moderater Abschlag"),
        ("Adoptions-Speed (Mon.)", p3.adoption_speed, "input", "DED: breites Verschreiberpotenzial"),
        ("Compliance (%)", p3.compliance_rate, "input_pct", "Nasenspray BID, chronisch"),
        ("Wettbewerber", p3.competitors, "input", "iKervis, Vevizye, CsA-Generika"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # --- Field Force ---
    row += 2
    ws.merge_range(row, 1, row, 3, "AUSSENDIENST & GO-TO-MARKET", fmt["section"])
    for label, value, fk, hint in [
        ("Reps bei Launch", ff.reps_at_launch, "input", "Initiale Sales Reps"),
        ("Peak Sales Reps", ff.reps_peak, "input", "Maximaler AD-Umfang"),
        ("Reps Ramp-Up (Mon.)", ff.reps_ramp_months, "input", "Monate bis Peak"),
        ("Rep Jahreskosten (EUR)", ff.rep_annual_cost, "input", "Voll belastet (Gehalt + Auto + Overhead)"),
        ("Peak MSLs", ff.msls_peak, "input", "Medical Science Liaisons"),
        ("MSL Jahreskosten (EUR)", ff.msl_annual_cost, "input", "Voll belastet"),
        ("Launch-Marketing/Mon. (EUR)", ff.launch_marketing_monthly, "input", "Waehrend Launch-Phase"),
        ("Maintenance-Marketing (EUR)", ff.maintenance_marketing_monthly, "input", "Nach Launch-Phase"),
        ("Launch-Phase (Mon.)", ff.launch_phase_months, "input", "Dauer der intensiven Phase"),
        ("Kongresse/Jahr (EUR)", ff.congress_annual_budget, "input", "DOG, AAD etc."),
        ("KOL-Programm/Jahr (EUR)", ff.kol_program_annual, "input", "Advisory Boards, Speaker"),
        ("Digital Marketing/Mon. (EUR)", ff.digital_marketing_monthly, "input", "Digitale Kanaele"),
        ("Synergie P2 (Kostenanteil)", ff.synergy_factor_p2, "input_pct", "P2 Launch = 70% Standalone-Kosten"),
        ("Synergie P3 (Kostenanteil)", ff.synergy_factor_p3, "input_pct", "P3 Launch = 80% Standalone-Kosten"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # --- Scenario definitions ---
    row += 2
    ws.merge_range(row, 1, row, 3, "SZENARIO-DEFINITIONEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Konservativ", "Base Case", "Aggressiv"]):
        ws.write(row, 1 + c, h, fmt["th"])
    for param, cons, base, agg in [
        ("Tyrvaya Launch (Monat)", 60, 42, 30),
        ("Tyrvaya Peak Share", 0.12, 0.20, 0.25),
        ("MR-141 Launch (Monat)", 24, 18, 12),
        ("Peak Sales Reps", 35, 45, 60),
        ("RYZUMVI Speed (Mon.)", 24, 18, 12),
        ("MR-141 Speed (Mon.)", 30, 24, 18),
        ("Tyrvaya Speed (Mon.)", 36, 30, 24),
    ]:
        row += 1
        ws.write(row, 1, param, fmt["label_bold"])
        for c, val in enumerate([cons, base, agg]):
            if isinstance(val, float) and val < 1:
                ws.write(row, 2 + c, val, fmt["input_pct"])
            else:
                ws.write(row, 2 + c, val, fmt["input"])

    # ===================================================================
    # SHEET 2: MARKTDATEN
    # ===================================================================
    ws2 = wb.add_worksheet("Marktdaten")
    ws2.hide_gridlines(2)
    ws2.set_tab_color("#1e3a5f")
    ws2.set_column("A:A", 3)
    ws2.set_column("B:B", 38)
    ws2.set_column("C:G", 20)

    row = 1
    ws2.merge_range(row, 1, row, 5, "Ophthalmologie-Markt Deutschland & Wettbewerb", fmt["title"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "Ophthalmologen & Versorgungsstruktur", fmt["section"])
    for label, value in [
        ("Augenaerzte gesamt (DE)", "8.250+ (BAeK/KBV 2024)"),
        ("Davon GKV-Vertragsaerzte", "~6.600 (vertragsaerztl. Versorgung)"),
        ("MVZ-Augenaerzte (2024)", "~2.250 (Anteil wachsend, +8% p.a.)"),
        ("Patientenkontakte/Arzt/Quartal", "~1.000-1.400 (BVA-Daten)"),
        ("Verguetung", "EBM + IGeL (Mydriase: meist IGeL)"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "Trockenes Auge (DED) – Marktlandschaft", fmt["section"])
    for label, value in [
        ("Betroffene (DE)", "~10 Mio. (Praevalenz 15-20%)"),
        ("Diagnostiziert", "1.5-1.9 Mio."),
        ("Rx-Therapiequote", "Nur 36% der Diagnostizierten"),
        ("Marktvolumen DE (Rx+OTC)", "~EUR 430 Mio. (CAGR 5.7%)"),
        ("Rx-Anteil", "~35% (Rest: OTC kuenstl. Traenen)"),
        ("OTC kuenstl. Traenen", "~EUR 280 Mio. (+4% p.a.)"),
        ("Ophth. Rx-Gesamtmarkt DE", "~EUR 1.2 Mrd."),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "DED-Wettbewerber (Rx)", fmt["section"])
    row += 1
    for c, h in enumerate(["Produkt", "Firma", "Indikation", "Preis/Mon.", "Status DE"]):
        ws2.write(row, 1 + c, h, fmt["th"])
    ws2.set_row(row, 30)
    for prod, firma, ind, preis, status in [
        ("iKervis (CsA)", "Santen", "Schwere Keratitis (DED)", "EUR 120-135", "Seit 2015, Referenzprodukt"),
        ("Vevizye (CsA)", "Novaliq / Thea", "Moderate-schwere DED", "EUR ~120 (erw.)", "EU-Zul. Okt 2024, DE-Launch 2025"),
        ("Restasis (CsA)", "AbbVie", "DED (nur USA)", "n/a DE", "Kein EU-Launch"),
        ("Tyrvaya (Varenicl.)", "Specialty Pharma", "DED, neuer MOA", "EUR 140 (gepl.)", "Kein EMA-Filing bisher"),
        ("OTC Traenen", "Diverse", "Milde DED, Befeuchtung", "EUR 5-15", "Freier Markt, hohes Volumen"),
    ]:
        row += 1
        ws2.write(row, 1, prod, fmt["label_bold"])
        ws2.write(row, 2, firma, fmt["label"])
        ws2.write(row, 3, ind, fmt["label"])
        ws2.write(row, 4, preis, fmt["label"])
        ws2.write(row, 5, status, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "Ophthalmologie-Pipeline (Eye Care Franchise)", fmt["section"])
    for label, value in [
        ("Strategie", "Aufbau Specialty-Ophthalmologie durch Akquisitionen + Pipeline"),
        ("Oyster Point Akquisition", "Abgeschlossen 2023, Basis fuer Tyrvaya"),
        ("Famy Life Sciences", "Erworben 2023, RYZUMVI + MR-141 Pipeline"),
        ("RYZUMVI (Phentolamin)", "FDA-zugelassen (Aug 2023), EU-Einreichung erwartet"),
        ("MR-141 (Phentolamin)", "Phase III Presbyopie, Ergebnisse 2025/26 erw."),
        ("Tyrvaya (Vareniclin)", "FDA-zugelassen (Okt 2021), kein EMA-Filing"),
        ("Fokus DE", "Facharzt-Vertrieb, AMNOG-Erstattung, MVZ-Zugang"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "AMNOG-Referenzfaelle (Augenheilkunde)", fmt["section"])
    for label, value in [
        ("iKervis (CsA, 2016)", "Gering: Zusatznutzen vs. Traenenersatz; EUR 120-135/Mon. EB"),
        ("Eylea (Aflibercept, 2013)", "Betraechtlich: AMD; EUR ~1.100/Injektion EB"),
        ("Lucentis (Ranibizumab, 2013)", "Gering: DME; EUR ~800/Injektion EB"),
        ("Typisches Ergebnis", "Augenheilkunde: oft 'geringer Zusatznutzen'"),
        ("Konsequenz fuer Preis", "AMNOG-Cut 10-25%, danach jaehrl. Erosion 1-3%"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    # ===================================================================
    # SHEET 3: PORTFOLIO (Product-level detail)
    # ===================================================================
    ws3 = wb.add_worksheet("Portfolio")
    ws3.hide_gridlines(2)
    ws3.set_tab_color("#7c3aed")
    ws3.set_column("A:A", 3)
    ws3.set_column("B:B", 10)
    ws3.set_column("C:Q", 14)

    row = 1
    ws3.merge_range(row, 1, row, 14, "Produkt-Level Forecast – Alle 3 Produkte", fmt["title"])

    row += 2
    headers_port = [
        "Monat",
        "RYZUMVI\nPat.", "RYZUMVI\nPreis", "RYZUMVI\nUmsatz", "RYZUMVI\nVerordner",
        "MR-141\nPat.", "MR-141\nPreis", "MR-141\nUmsatz", "MR-141\nVerordner",
        "Tyrvaya\nPat.", "Tyrvaya\nPreis", "Tyrvaya\nUmsatz", "Tyrvaya\nVerordner",
        "Portfolio\nUmsatz",
    ]
    for c, h in enumerate(headers_port):
        if c == 0:
            ws3.write(row, 1 + c, h, fmt["th"])
        elif c <= 4:
            ws3.write(row, 1 + c, h, fmt["th_teal"])
        elif c <= 8:
            ws3.write(row, 1 + c, h, fmt["th"])
        elif c <= 12:
            ws3.write(row, 1 + c, h, fmt["th_amber"])
        else:
            ws3.write(row, 1 + c, h, fmt["th_purple"])
    ws3.set_row(row, 35)
    data_start_p = row + 1

    for i, (_, r) in enumerate(df.iterrows()):
        row += 1
        is_alt = i % 2 == 1
        ws3.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
        # RYZUMVI
        ws3.write(row, 2, r["ryzumvi_patients"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 3, r["ryzumvi_price"], fmt["row_alt_eur"] if is_alt else fmt["eur_detail"])
        ws3.write(row, 4, r["ryzumvi_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 5, r["ryzumvi_prescribers"], fmt["row_alt_num"] if is_alt else fmt["number"])
        # MR-141
        ws3.write(row, 6, r["mr141_patients"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 7, r["mr141_price"], fmt["row_alt_eur"] if is_alt else fmt["eur_detail"])
        ws3.write(row, 8, r["mr141_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 9, r["mr141_prescribers"], fmt["row_alt_num"] if is_alt else fmt["number"])
        # Tyrvaya
        ws3.write(row, 10, r["tyrvaya_patients"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 11, r["tyrvaya_price"], fmt["row_alt_eur"] if is_alt else fmt["eur_detail"])
        ws3.write(row, 12, r["tyrvaya_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 13, r["tyrvaya_prescribers"], fmt["row_alt_num"] if is_alt else fmt["number"])
        # Portfolio
        ws3.write(row, 14, r["total_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
    data_end_p = row

    # Chart: Product revenue stacked
    chart_p = wb.add_chart({"type": "area", "subtype": "stacked"})
    chart_p.add_series({
        "name": "RYZUMVI", "categories": ["Portfolio", data_start_p, 1, data_end_p, 1],
        "values": ["Portfolio", data_start_p, 4, data_end_p, 4], "fill": {"color": "#0d9488"},
    })
    chart_p.add_series({
        "name": "MR-141", "categories": ["Portfolio", data_start_p, 1, data_end_p, 1],
        "values": ["Portfolio", data_start_p, 8, data_end_p, 8], "fill": {"color": "#1e3a5f"},
    })
    chart_p.add_series({
        "name": "Tyrvaya", "categories": ["Portfolio", data_start_p, 1, data_end_p, 1],
        "values": ["Portfolio", data_start_p, 12, data_end_p, 12], "fill": {"color": "#d97706"},
    })
    chart_p.set_title({"name": "Portfolio-Umsatz nach Produkt (monatlich)"})
    chart_p.set_y_axis({"name": "EUR", "num_format": "\u20ac#,##0"})
    chart_p.set_size({"width": 860, "height": 400})
    chart_p.set_legend({"position": "bottom"})
    ws3.insert_chart("B" + str(row + 3), chart_p)

    # Chart: Prescriber adoption
    chart_presc = wb.add_chart({"type": "line"})
    chart_presc.add_series({
        "name": "RYZUMVI Verordner", "categories": ["Portfolio", data_start_p, 1, data_end_p, 1],
        "values": ["Portfolio", data_start_p, 5, data_end_p, 5],
        "line": {"color": "#0d9488", "width": 2.5},
    })
    chart_presc.add_series({
        "name": "MR-141 Verordner", "categories": ["Portfolio", data_start_p, 1, data_end_p, 1],
        "values": ["Portfolio", data_start_p, 9, data_end_p, 9],
        "line": {"color": "#1e3a5f", "width": 2.5},
    })
    chart_presc.add_series({
        "name": "Tyrvaya Verordner", "categories": ["Portfolio", data_start_p, 1, data_end_p, 1],
        "values": ["Portfolio", data_start_p, 13, data_end_p, 13],
        "line": {"color": "#d97706", "width": 2.5},
    })
    chart_presc.set_title({"name": "Facharzt-Adoption (verordnende Augenaerzte)"})
    chart_presc.set_y_axis({"name": "Anzahl Verordner", "num_format": "#,##0"})
    chart_presc.set_size({"width": 860, "height": 380})
    chart_presc.set_legend({"position": "bottom"})
    ws3.insert_chart("B" + str(row + 24), chart_presc)

    # ===================================================================
    # SHEET 4: FORECAST (Portfolio-level with P&L)
    # ===================================================================
    ws4 = wb.add_worksheet("Forecast")
    ws4.hide_gridlines(2)
    ws4.set_tab_color("#0d9488")
    ws4.set_column("A:A", 3)
    ws4.set_column("B:B", 10)
    ws4.set_column("C:O", 14)

    row = 1
    ws4.merge_range(row, 1, row, 12, "Portfolio-Forecast mit P&L und GTM-Invest (Base Case)", fmt["title"])

    # KPIs
    row += 2
    be = kpis.get("breakeven_month")
    be_text = f"Monat {be}" if be else "-"
    kpi_data = [
        ("Portfolio 7J Umsatz", kpis["total_7y_revenue"], "kpi_value"),
        ("Portfolio 7J Gewinn", kpis["total_7y_profit"], "kpi_value"),
        ("Break-Even", be_text, "kpi_value_plain"),
        ("ROI (7 Jahre)", f"{kpis['final_roi']:.1f}x", "kpi_value_plain"),
        ("GTM-Invest 7J", kpis["total_7y_gtm_cost"], "kpi_value"),
    ]
    for c, (label, value, vfmt) in enumerate(kpi_data):
        col = 1 + c * 2
        ws4.merge_range(row, col, row, col + 1, label, fmt["kpi_label"])
        ws4.merge_range(row + 1, col, row + 1, col + 1, value, fmt[vfmt])

    row += 4
    headers_fc = [
        "Monat", "Produkte\nLive", "Gesamt\nUmsatz", "Gesamt\nPatienten",
        "Reps", "MSLs", "GTM-Kosten\n/Mon.",
        "Portfolio\nGewinn", "Kum.\nUmsatz", "Kum.\nGewinn",
        "Kum.\nGTM-Invest", "ROI",
        "MVZ-Anteil",
    ]
    for c, h in enumerate(headers_fc):
        ws4.write(row, 1 + c, h, fmt["th_teal"])
    ws4.set_row(row, 35)
    data_start_f = row + 1

    for i, (_, r) in enumerate(df.iterrows()):
        row += 1
        is_alt = i % 2 == 1
        ws4.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
        ws4.write(row, 2, r["products_launched"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 3, r["total_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 4, r["total_patients"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 5, r["ff_reps"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 6, r["ff_msls"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 7, r["total_gtm_cost"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 8, r["portfolio_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 9, r["cumulative_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 10, r["cumulative_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 11, r["cumulative_gtm_cost"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 12, r["roi"], fmt["row_alt_mult"] if is_alt else fmt["mult"])
        ws4.write(row, 13, r["mvz_share"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
    data_end_f = row

    # Chart: Revenue vs Profit vs GTM
    chart_fc = wb.add_chart({"type": "line"})
    chart_fc.add_series({
        "name": "Kum. Umsatz", "categories": ["Forecast", data_start_f, 1, data_end_f, 1],
        "values": ["Forecast", data_start_f, 9, data_end_f, 9],
        "line": {"color": "#1e3a5f", "width": 2.5},
    })
    chart_fc.add_series({
        "name": "Kum. Gewinn", "categories": ["Forecast", data_start_f, 1, data_end_f, 1],
        "values": ["Forecast", data_start_f, 10, data_end_f, 10],
        "line": {"color": "#27ae60", "width": 2.5},
    })
    chart_fc.add_series({
        "name": "Kum. GTM-Invest", "categories": ["Forecast", data_start_f, 1, data_end_f, 1],
        "values": ["Forecast", data_start_f, 11, data_end_f, 11],
        "line": {"color": "#c0392b", "width": 1.5, "dash_type": "dash"},
    })
    chart_fc.set_title({"name": "Kumuliert: Umsatz, Gewinn, GTM-Invest"})
    chart_fc.set_y_axis({"name": "EUR", "num_format": "\u20ac#,##0"})
    chart_fc.set_size({"width": 860, "height": 400})
    chart_fc.set_legend({"position": "bottom"})
    ws4.insert_chart("B" + str(row + 3), chart_fc)

    # Chart: Monthly revenue + reps
    chart_dual = wb.add_chart({"type": "column"})
    chart_dual.add_series({
        "name": "Monatl. Umsatz", "categories": ["Forecast", data_start_f, 1, data_end_f, 1],
        "values": ["Forecast", data_start_f, 3, data_end_f, 3],
        "fill": {"color": "#1e3a5f"}, "gap": 50,
    })
    chart_dual2 = wb.add_chart({"type": "line"})
    chart_dual2.add_series({
        "name": "Sales Reps", "categories": ["Forecast", data_start_f, 1, data_end_f, 1],
        "values": ["Forecast", data_start_f, 5, data_end_f, 5],
        "line": {"color": "#d97706", "width": 2.5}, "y2_axis": True,
    })
    chart_dual.combine(chart_dual2)
    chart_dual.set_title({"name": "Monatl. Umsatz & Aussendienst-Aufbau"})
    chart_dual.set_y_axis({"name": "EUR/Monat", "num_format": "\u20ac#,##0"})
    chart_dual.set_y2_axis({"name": "Sales Reps", "num_format": "#,##0"})
    chart_dual.set_size({"width": 860, "height": 380})
    chart_dual.set_legend({"position": "bottom"})
    ws4.insert_chart("B" + str(row + 24), chart_dual)

    # ===================================================================
    # SHEET 5: DASHBOARD
    # ===================================================================
    ws5 = wb.add_worksheet("Dashboard")
    ws5.hide_gridlines(2)
    ws5.set_tab_color("#6366f1")
    ws5.set_column("A:A", 3)
    ws5.set_column("B:B", 38)
    ws5.set_column("C:E", 22)

    row = 1
    ws5.merge_range(row, 1, row, 4, "Executive Summary - Eye Care Franchise Portfolio", fmt["title"])

    row += 2
    ws5.merge_range(row, 1, row, 4, "Szenario-Vergleich (7-Jahres-Horizont)", fmt["section"])

    # Run all scenarios
    scenarios_def = {
        "Konservativ": {"t_launch": 60, "t_share": 0.12, "ff_peak": 35, "m_launch": 24,
                        "r_speed": 24, "m_speed": 30, "t_speed": 36, "r_share": 0.40},
        "Base Case": {"t_launch": 42, "t_share": 0.20, "ff_peak": 45, "m_launch": 18,
                      "r_speed": 18, "m_speed": 24, "t_speed": 30, "r_share": 0.50},
        "Aggressiv": {"t_launch": 30, "t_share": 0.25, "ff_peak": 60, "m_launch": 12,
                      "r_speed": 12, "m_speed": 18, "t_speed": 24, "r_share": 0.60},
    }
    scenario_results = {}
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
        scenario_results[sn] = sk

    row += 1
    ws5.write(row, 1, "")
    ws5.write(row, 2, "Konservativ", fmt["th"])
    ws5.write(row, 3, "Base Case", fmt["th_teal"])
    ws5.write(row, 4, "Aggressiv", fmt["th"])

    for label, key, vtype in [
        ("Portfolio-Umsatz 7J", "total_7y_revenue", "eur"),
        ("Portfolio-Gewinn 7J", "total_7y_profit", "eur"),
        ("GTM-Invest 7J", "total_7y_gtm_cost", "eur"),
        ("ROI (7J)", "final_roi", "mult"),
        ("Break-Even (Monat)", "breakeven_month", "month"),
        ("Peak monatl. Umsatz", "peak_monthly_revenue", "eur"),
        ("Peak Umsatz-Monat", "peak_revenue_month", "plain"),
        ("Umsatz Jahr 1", "revenue_year1", "eur"),
        ("Umsatz Jahre 1-3", "revenue_year3", "eur"),
        ("Verordner (final)", "total_prescribers_final", "plain"),
        ("RYZUMVI Umsatzanteil", "ryzumvi_revenue_share", "pct"),
        ("MR-141 Umsatzanteil", "mr141_revenue_share", "pct"),
        ("Tyrvaya Umsatzanteil", "tyrvaya_revenue_share", "pct"),
        ("RYZUMVI Umsatz 7J", "ryzumvi_total_revenue", "eur"),
        ("MR-141 Umsatz 7J", "mr141_total_revenue", "eur"),
        ("Tyrvaya Umsatz 7J", "tyrvaya_total_revenue", "eur"),
    ]:
        row += 1
        ws5.write(row, 1, label, fmt["label_bold"])
        for c, sn in enumerate(["Konservativ", "Base Case", "Aggressiv"]):
            val = scenario_results[sn].get(key, 0)
            if val is None:
                val = 0
            if vtype == "eur":
                ws5.write(row, 2 + c, val, fmt["eur"])
            elif vtype == "pct":
                ws5.write(row, 2 + c, val, fmt["pct"])
            elif vtype == "mult":
                ws5.write(row, 2 + c, f"{val:.1f}x", fmt["kpi_value_plain"])
            elif vtype == "month":
                ws5.write(row, 2 + c, f"M{val}" if val else "-", fmt["kpi_value_plain"])
            else:
                ws5.write(row, 2 + c, val, fmt["number"])

    # Investment rationale
    row += 3
    ws5.merge_range(row, 1, row, 4, "Investment-These", fmt["section"])
    row += 1
    for thesis in [
        "RYZUMVI: First-in-class DE, Cash-Cow ab Launch (Mydriase-Reversal = unmittelbarer Umsatz)",
        "MR-141: Potenziell transformativ (15M Presbyopie-Pat.), aber GKV-Huerde (Lifestyle-nah)",
        "Tyrvaya: Groesster Markt (DED EUR 430M), aber spaeter Launch + starker Wettbewerb (iKervis, Vevizye)",
        "Synergien: Shared Field Force senkt P2-Launch-Kosten um 30% und P3 um 20% vs. Standalone",
        "Break-Even: M15 (Base Case) dank sofortigem RYZUMVI-Umsatz, vgl. M24+ bei Single-Product-Launch",
        "MVZ-Kanal: Wachsender Zugang zu konsolidierten Praxen (2.250 Aerzte, +8% p.a.)",
    ]:
        ws5.merge_range(row, 1, row, 4, thesis, fmt["label"])
        ws5.set_row(row, 30)
        row += 1

    # ===================================================================
    # SHEET 6: METHODIK
    # ===================================================================
    ws6 = wb.add_worksheet("Methodik")
    ws6.hide_gridlines(2)
    ws6.set_tab_color("#6366f1")
    ws6.set_column("A:A", 3)
    ws6.set_column("B:B", 38)
    ws6.set_column("C:C", 32)
    ws6.set_column("D:D", 52)
    ws6.set_column("E:E", 42)

    row = 1
    ws6.merge_range(row, 1, row, 4, "Methodik & Transparenz-Matrix", fmt["title"])
    row += 1
    ws6.merge_range(row, 1, row, 4, "Jeder Datenpunkt ist klassifiziert: FAKT / ANNAHME / MODELL / LUECKE",
        wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    # Legend
    row += 2
    ws6.write(row, 1, "Legende:", fmt["label_bold"])
    ws6.write(row, 2, "FAKT", fmt["fact"])
    ws6.write(row, 3, "Aus oeffentlichen Quellen", fmt["label"])
    row += 1
    ws6.write(row, 2, "ANNAHME", fmt["assumption"])
    ws6.write(row, 3, "Steuerbar (gelbe Zellen)", fmt["label"])
    row += 1
    ws6.write(row, 2, "MODELL", fmt["model"])
    ws6.write(row, 3, "Mathematisches Modell", fmt["label"])
    row += 1
    ws6.write(row, 2, "LUECKE", fmt["gap"])
    ws6.write(row, 3, "Fuer Produktiveinsatz noetig", fmt["label"])

    # FACTS
    row += 2
    ws6.merge_range(row, 1, row, 4, "FAKTEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Datenpunkt", "Wert", "Quelle", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    facts = [
        ("Augenaerzte DE", "8.250+ (BAeK/KBV 2024)", "KBV Aerztestatistik", "FAKT"),
        ("GKV-Vertragsaerzte Ophth.", "~6.600", "KBV Aerztestatistik", "FAKT"),
        ("MVZ-Augenaerzte", "~2.250 (2024), +8% p.a.", "Gesundheitsmarkt.de / ZI", "FAKT"),
        ("DED-Praevalenz DE", "~10 Mio., 1.5-1.9 Mio. diagnostiziert", "Grand View Research", "FAKT"),
        ("DED Rx-Therapiequote", "36% der Diagnostizierten", "Epidemiologische Studien", "FAKT"),
        ("DED Markt DE (Rx+OTC)", "~EUR 430 Mio. (CAGR 5.7%)", "Grand View Research / IQVIA", "FAKT"),
        ("iKervis Preis/Mon.", "EUR 120-135 (schwere Keratitis)", "Lauer-Taxe / Santen", "FAKT"),
        ("Vevizye EU-Zulassung", "Oktober 2024 (Novaliq/Thea)", "EMA EPAR", "FAKT"),
        ("RYZUMVI FDA-Zulassung", "August 2023 (Phentolamin)", "FDA Public Assessment", "FAKT"),
        ("Tyrvaya FDA-Zulassung", "Oktober 2021 (Vareniclin)", "FDA / Oyster Point", "FAKT"),
        ("Tyrvaya: kein EMA-Filing", "Stand Feb. 2025: keine EU-Einreichung", "Pipeline-Daten / ClinTrials", "FAKT"),
        ("Oyster Point Akquisition", "2023, ~$785M", "Oeffentliche Pressemitteilungen", "FAKT"),
        ("Famy Life Sciences", "2023 erworben (RYZUMVI + MR-141)", "Oeffentliche Pressemitteilungen", "FAKT"),
        ("Presbyopie DE", "~15 Mio. Betroffene (40+)", "Epidemiologische Schaetzung", "FAKT"),
    ]
    for dp, val, source, cat in facts:
        row += 1
        ws6.write(row, 1, dp, fmt["label_bold"])
        ws6.write(row, 2, val, fmt["fact"])
        ws6.write(row, 3, source, fmt["label"])
        ws6.write(row, 4, cat, fmt["fact"])

    # ASSUMPTIONS
    row += 2
    ws6.merge_range(row, 1, row, 4, "ANNAHMEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Default", "Begruendung", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    assumptions = [
        ("RYZUMVI eligible Proz.", "800K/Jahr", "Dilatierte Untersuchungen mit Reversal-Wunsch", "ANNAHME"),
        ("RYZUMVI Preis", "EUR 25/Behandlung", "Einmalapplikation, IGeL-Benchmark", "ANNAHME"),
        ("RYZUMVI Peak Share", "50%", "First-in-class, kein Wettbewerb", "ANNAHME"),
        ("MR-141 addressable", "2% von 15M", "Konservativ: Rx statt Lesebrille", "ANNAHME"),
        ("MR-141 Preis", "EUR 45/Mon.", "Taegl. Rx, Lifestyle-Preispunkt", "ANNAHME"),
        ("Tyrvaya Preis", "EUR 140/Mon.", "Benchmark iKervis (EUR 120-135)", "ANNAHME"),
        ("Tyrvaya Launch Monat", "42 (3.5 Jahre)", "EMA-Filing + Zulassung + AMNOG", "ANNAHME"),
        ("AMNOG-Abschlag P1", "10%", "Einzigartig, milder Abschlag", "ANNAHME"),
        ("AMNOG-Abschlag P2", "25%", "Lifestyle-nah, haertere Verhandlung", "ANNAHME"),
        ("AMNOG-Abschlag P3", "15%", "Neuartiger MOA, moderate Verhandlung", "ANNAHME"),
        ("Synergy P2", "70% der Standalone-Kosten", "Shared Field Force", "ANNAHME"),
        ("Synergy P3", "80% der Standalone-Kosten", "Anderes Segment (DED), weniger Synergy", "ANNAHME"),
        ("Peak Sales Reps", "45", "1 Rep : ~150 Augenaerzte", "ANNAHME"),
        ("Peak MSLs", "12", "AMNOG-Support + KOL-Management", "ANNAHME"),
    ]
    for param, val, reason, cat in assumptions:
        row += 1
        ws6.write(row, 1, param, fmt["label_bold"])
        ws6.write(row, 2, val, fmt["assumption"])
        ws6.write(row, 3, reason, fmt["label"])
        ws6.write(row, 4, cat, fmt["assumption"])

    # MODELS
    row += 2
    ws6.merge_range(row, 1, row, 4, "MODELLE", fmt["section"])
    row += 1
    for c, h in enumerate(["Modell", "Formel / Logik", "Referenz", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    models = [
        ("Facharzt-Adoption", "Logistische S-Kurve: peak / (1 + exp(-k*(t-m)))", "Pharma Launch Diffusionsmodelle", "MODELL"),
        ("AMNOG-Pricing", "3-Phasen: Frei (6M) -> G-BA Cut -> Jaehrl. Erosion", "IQWiG / GKV-SV AMNOG-Verfahren", "MODELL"),
        ("Field Force Ramp", "Lineare Skalierung: Launch -> Peak ueber n Monate", "Pharma GTM Benchmarks", "MODELL"),
        ("Cross-Product Synergy", "P2: 70%, P3: 80% der Standalone-Kosten", "Portfolio-Skaleneffekte", "MODELL"),
        ("Competitive Erosion", "Jaehrl. Share-Reduktion: share * (1 + erosion_rate)^t", "Analogie: iKervis vs. Vevizye", "MODELL"),
        ("Patient Volume", "eligible * addressable * share * compliance", "Standard Pharma Forecast", "MODELL"),
        ("MVZ-Kanal", "Basis * (1 + growth_rate)^(t/12)", "ZI-Daten, 8% p.a. Konsolidierung", "MODELL"),
        ("Portfolio P&L", "Sum(Net_Revenue per product) - GTM_Cost", "Per-product COGS + Royalties", "MODELL"),
    ]
    for name, formula, ref, cat in models:
        row += 1
        ws6.set_row(row, 35)
        ws6.write(row, 1, name, fmt["label_bold"])
        ws6.write(row, 2, formula, fmt["model"])
        ws6.write(row, 3, ref, fmt["label"])
        ws6.write(row, 4, cat, fmt["model"])

    # GAPS
    row += 2
    ws6.merge_range(row, 1, row, 4, "LUECKEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Gap", "Beschreibung", "Datenquelle", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    gaps = [
        ("EMA-Filing Tyrvaya", "Zeitpunkt und Strategie der EU-Einreichung unklar", "Regulatory Intelligence", "LUECKE"),
        ("MR-141 Phase-III Daten", "Ergebnisse Presbyopie-Studie stehen noch aus", "ClinicalTrials.gov", "LUECKE"),
        ("AMNOG-Dossier Details", "IQWiG-Bewertung und G-BA-Ergebnis sind produktspez.", "IQWiG / G-BA Verhandlung", "LUECKE"),
        ("Vevizye DE-Launch Preis", "Erstattungsbetrag noch in Verhandlung (2025)", "Novaliq / GKV-SV", "LUECKE"),
        ("Real-World-Compliance", "Ophth. Compliance-Daten fuer Augentropfen/Spray", "Observational Studies / IQVIA", "LUECKE"),
        ("KBV-Verordnungsdaten", "Tatsaechl. ICD-basierte Verschreibungen pro Arzt", "KBV Verordnungsdaten (nicht-oeffentl.)", "LUECKE"),
        ("iKervis Marktanteile DE", "Monatl. Pack./Umsatz nach Indikation", "IQVIA Prescription Analytics", "LUECKE"),
        ("Field Force Benchmark", "Tatsaechl. Rep-Effizienz (Calls/Conversion) Ophth.", "IMS / Veeva CRM Data", "LUECKE"),
        ("Reimbursement Landscape", "Festbetraege, Rabattvertraege fuer CsA-Produkte", "GKV-SV / Lauer-Taxe Detail", "LUECKE"),
    ]
    for gap_name, desc, source, cat in gaps:
        row += 1
        ws6.write(row, 1, gap_name, fmt["label_bold"])
        ws6.write(row, 2, desc, fmt["gap"])
        ws6.write(row, 3, source, fmt["label"])
        ws6.write(row, 4, cat, fmt["gap"])

    row += 3
    ws6.merge_range(row, 1, row, 4,
        "Hinweis: Alle Daten synthetisch. Referenzen: FDA/EMA Public Assessments, "
        "KBV Aerztestatistik, Grand View Research (Dry Eye), Santen (iKervis), Novaliq (Vevizye), "
        "ClinicalTrials.gov, oeffentliche Investor Relations. Kein Bezug zu vertraulichen Daten.",
        fmt["hint"])

    wb.close()
    print(f"Excel model saved to: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    build_model()
