"""
Build a professional Excel forecast model for the Sildenafil Rx-to-OTC Switch scenario.

Sheets:
1. INPUTS          – All user-configurable parameters (yellow cells)
2. Marktdaten      – ED market, PDE5 landscape, channel structure, UK reference
3. Apothekenverteilung – Channel-level forecast with share evolution
4. Forecast        – Monthly dual-channel forecast (Rx + OTC)
5. Dashboard       – Executive summary with scenario comparison
6. Methodik        – Transparency matrix: Facts vs. Assumptions vs. Models
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import xlsxwriter
import numpy as np
import pandas as pd
from models.sildenafil_otc_engine import (
    SildenafilOtcParams,
    forecast_sildenafil_otc, calculate_kpis_sildenafil,
)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Sildenafil_OTC_Switch_Forecast.xlsx")


def build_model():
    wb = xlsxwriter.Workbook(OUTPUT_PATH)

    # ─── Format Definitions ─────────────────────────────────────────
    fmt = {}
    fmt["title"] = wb.add_format({"bold": True, "font_size": 16, "font_color": "#1e3a5f", "bottom": 2, "bottom_color": "#1e3a5f"})
    fmt["section"] = wb.add_format({"bold": True, "font_size": 12, "font_color": "#1e3a5f", "bg_color": "#e8f0fe", "border": 1, "border_color": "#b0c4de"})
    fmt["subsection"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "#374151", "bottom": 1, "bottom_color": "#d1d5db"})
    fmt["input"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "num_format": "#,##0", "font_color": "#1a237e", "bold": True})
    fmt["input_pct"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "num_format": "0.0%", "font_color": "#1a237e", "bold": True})
    fmt["input_eur"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "num_format": "€#,##0.00", "font_color": "#1a237e", "bold": True})
    fmt["input_text"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "font_color": "#1a237e", "bold": True})
    fmt["label"] = wb.add_format({"font_size": 10, "font_color": "#374151", "text_wrap": True, "valign": "vcenter"})
    fmt["label_bold"] = wb.add_format({"font_size": 10, "font_color": "#374151", "bold": True, "valign": "vcenter"})
    fmt["hint"] = wb.add_format({"font_size": 9, "font_color": "#9ca3af", "italic": True, "text_wrap": True, "valign": "vcenter"})
    fmt["number"] = wb.add_format({"num_format": "#,##0"})
    fmt["eur"] = wb.add_format({"num_format": "€#,##0"})
    fmt["eur_detail"] = wb.add_format({"num_format": "€#,##0.00"})
    fmt["pct"] = wb.add_format({"num_format": "0.0%"})
    fmt["mult"] = wb.add_format({"num_format": "0.00"})
    fmt["th"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#1e3a5f", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_teal"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#134e4a", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_purple"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#4c1d95", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["kpi_label"] = wb.add_format({"bold": True, "font_size": 11, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1})
    fmt["kpi_value"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#134e4a", "bg_color": "#f0fdf4", "border": 1, "num_format": "0.0%", "align": "center"})
    fmt["kpi_value_plain"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "align": "center"})
    fmt["row_alt"] = wb.add_format({"bg_color": "#f8fafc"})
    fmt["row_alt_eur"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "€#,##0"})
    fmt["row_alt_pct"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "0.0%"})
    fmt["row_alt_num"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "#,##0"})
    fmt["fact"] = wb.add_format({"bg_color": "#dcfce7", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})
    fmt["assumption"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})
    fmt["model"] = wb.add_format({"bg_color": "#dbeafe", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})
    fmt["gap"] = wb.add_format({"bg_color": "#fef2f2", "border": 1, "text_wrap": True, "valign": "vcenter", "font_size": 10})

    def write_input_row(ws, row, label, value, fmt_key, hint):
        ws.write(row, 1, label, fmt["label_bold"])
        ws.write(row, 2, value, fmt[fmt_key])
        ws.write(row, 3, hint, fmt["hint"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 1: INPUTS
    # ═══════════════════════════════════════════════════════════════════
    ws = wb.add_worksheet("INPUTS")
    ws.hide_gridlines(2)
    ws.set_tab_color("#E0B800")
    ws.set_column("A:A", 3)
    ws.set_column("B:B", 44)
    ws.set_column("C:C", 18)
    ws.set_column("D:D", 55)

    row = 1
    ws.merge_range(row, 1, row, 3, "Sildenafil Rx-to-OTC Switch - Forecast Modell", fmt["title"])
    row += 1
    ws.merge_range(row, 1, row, 3, "Viatris / Viagra Connect 50mg | Referenz: UK OTC Launch 2018",
        wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    row += 2
    ws.merge_range(row, 1, row, 3, "1. PRODUKT & EPIDEMIOLOGIE", fmt["section"])
    for label, value, fk, hint in [
        ("Produkt", "Viagra Connect 50mg", "input_text", "Viatris-Marke fuer OTC"),
        ("Molekuel", "Sildenafil", "input_text", "PDE5-Hemmer"),
        ("Unternehmen", "Viatris", "input_text", "Inhaber der Marke Viagra"),
        ("Switch-Datum (hypothetisch)", "2027", "input_text", "BMG koennte SVA ueberstimmen"),
        ("ED-Praevalenz DE", 5_000_000, "input", "Maenner mit moderater-schwerer ED"),
        ("Therapiequote aktuell", 0.30, "input_pct", "Nur 30% werden behandelt (May et al. 2007)"),
        ("Therapieluecke", 3_500_000, "input", "Unbehandelte Maenner (berechnet)"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    row += 2
    ws.merge_range(row, 1, row, 3, "2. RX-MARKT (vor Switch)", fmt["section"])
    for label, value, fk, hint in [
        ("Sildenafil Rx Tabl./Monat", 868_000, "input", "65% von ~2.6M PDE5 Pack./Jahr × 4 Tabl."),
        ("Viagra Preis/Tablette (EUR)", 11.19, "input_eur", "Markenpreis 50mg (4er Pack)"),
        ("Generika Preis/Tablette (EUR)", 1.50, "input_eur", "Durchschnitt (Spanne 0.95-2.30)"),
        ("Viagra Markenanteil (Rx)", 0.10, "input_pct", "~10% der Sildenafil-Packs"),
        ("Rx-Rueckgang durch OTC", 0.08, "input_pct", "UK: Rx stieg sogar! Konservativ: -8%"),
        ("GKV-Erstattung", "NEIN", "input_text", "Patient zahlt 100% (Lifestyle-AM)"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    row += 2
    ws.merge_range(row, 1, row, 3, "3. OTC-KANAL", fmt["section"])
    for label, value, fk, hint in [
        ("OTC Preis/Tablette (EUR)", 5.99, "input_eur", "Zwischen UK GBP 5 und Rx-Generika EUR 1.50"),
        ("OTC Peak Tabletten/Monat", 2_100_000, "input", "Alle Kanaele zusammen"),
        ("Monate bis Peak", 18, "input", "Ramp-up-Dauer"),
        ("Neue Patienten (% OTC-Vol.)", 0.63, "input_pct", "UK-Referenz: 63% nie vorher behandelt"),
        ("Preiselastizitaet", -0.50, "input_eur", "Niedrig: Patient zahlt ohnehin 100% Rx"),
        ("Preistrend p.a.", -0.03, "input_pct", "Generikadruck auf OTC-Preis"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    row += 2
    ws.merge_range(row, 1, row, 3, "4. APOTHEKENVERTEILUNG (apothekenpflichtig)", fmt["section"])
    for label, value, fk, hint in [
        ("Stationaere Apotheke (%)", 0.55, "input_pct", "Face-to-face, Beratung, Sofortabholung"),
        ("Online-Apotheke (%)", 0.45, "input_pct", "DocMorris, Shop Apotheke – Anonymitaet!"),
        ("Online-Wachstum p.a. (Pp.)", 0.02, "input_pct", "ABDA ZDF 2024: ~+1.5-2 Pp./Jahr"),
        ("Apothekenmarge (stationaer)", 0.42, "input_pct", "Freie OTC-Preisgestaltung"),
        ("Online-Marge", 0.30, "input_pct", "Wettbewerbsdruck, niedrigere Kosten"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    row += 2
    ws.merge_range(row, 1, row, 3, "5. MARKE vs. GENERIKA OTC", fmt["section"])
    for label, value, fk, hint in [
        ("Viagra Connect Anteil (OTC)", 0.25, "input_pct", "Markenstaerke vs. Generikadruck"),
        ("Markenanteil-Erosion p.a.", -0.03, "input_pct", "Generikahersteller dringen in OTC"),
        ("Preispremium Marke", 1.80, "input", "Marke ist 1.8x teurer als Generika OTC"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    row += 2
    ws.merge_range(row, 1, row, 3, "6. SZENARIO-DEFINITIONEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Konservativ", "Base Case", "Optimistisch"]):
        ws.write(row, 1 + c, h, fmt["th"])
    for param, cons, base, opti in [
        ("OTC Peak Tabl./Mon.", 1_200_000, 2_100_000, 2_700_000),
        ("Monate bis Peak", 24, 18, 12),
        ("Marketing/Monat (EUR)", 300_000, 500_000, 750_000),
        ("Neue Patienten (%)", 0.55, 0.63, 0.70),
        ("Rx-Rueckgang", 0.12, 0.08, 0.05),
        ("Viagra Markenanteil OTC", 0.20, 0.25, 0.35),
    ]:
        row += 1
        ws.write(row, 1, param, fmt["label_bold"])
        for c, val in enumerate([cons, base, opti]):
            if isinstance(val, float) and val < 1:
                ws.write(row, 2 + c, val, fmt["input_pct"])
            else:
                ws.write(row, 2 + c, val, fmt["input"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 2: MARKTDATEN
    # ═══════════════════════════════════════════════════════════════════
    ws2 = wb.add_worksheet("Marktdaten")
    ws2.hide_gridlines(2)
    ws2.set_tab_color("#1e3a5f")
    ws2.set_column("A:A", 3)
    ws2.set_column("B:B", 38)
    ws2.set_column("C:G", 18)

    row = 1
    ws2.merge_range(row, 1, row, 5, "ED-Markt Deutschland & PDE5-Wettbewerb", fmt["title"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "Epidemiologie & Therapieluecke", fmt["section"])
    for label, value in [
        ("ED-Praevalenz (DE)", "4-6 Mio. Maenner (bis 8 Mio. mild)"),
        ("Cologne Male Survey (n=4.489)", "19.2% ED-Praevalenz gesamt"),
        ("Moderate-schwere ED (Viatris 2023)", "~5 Mio. Maenner"),
        ("Therapiequote", "Nur 30% erhalten Behandlung (May et al. 2007)"),
        ("Primaere Barriere", "Scham / Stigma (GoSpring-Studie)"),
        ("GKV-Erstattung", "NEIN – Patient zahlt 100%"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "PDE5-Hemmer Wettbewerb", fmt["section"])
    row += 1
    for c, h in enumerate(["Molekuel", "Marktanteil\n(Packs)", "Marke", "Generika\nPreis/Tab", "OTC?"]):
        ws2.write(row, 1 + c, h, fmt["th"])
    ws2.set_row(row, 30)
    for mol, share, brand, gen_p, otc in [
        ("Sildenafil", 0.55, "Viagra (Viatris)", 1.50, "3x abgelehnt (BfArM SVA)"),
        ("Tadalafil", 0.36, "Cialis (Lilly)", 1.80, "Abgelehnt (Juli 2023)"),
        ("Vardenafil", 0.04, "Levitra (Bayer)", 2.50, "Kein Antrag"),
        ("Avanafil", 0.01, "Spedra (Menarini)", 5.00, "Kein Antrag"),
    ]:
        row += 1
        ws2.write(row, 1, mol, fmt["label_bold"])
        ws2.write(row, 2, share, fmt["pct"])
        ws2.write(row, 3, brand, fmt["label"])
        ws2.write(row, 4, gen_p, fmt["eur_detail"])
        ws2.write(row, 5, otc, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "UK Viagra Connect – Referenzfall", fmt["section"])
    for label, value in [
        ("OTC-Launch", "Maerz 2018 (MHRA)"),
        ("Dosierung OTC", "50mg, apothekenpflichtig"),
        ("Preis (Boots)", "GBP 19.99 / 4 Tabletten = GBP 5.00/Tab"),
        ("Umsatz Q1 (12 Wochen)", "GBP 4.3 Mio."),
        ("Umsatz Jahr 1 (hochgerechnet)", "GBP 16 Mio."),
        ("Neupatienten (nie vorher behandelt)", "63% (UK Real-World-Studie, n=1.162)"),
        ("NHS Rx-Effekt", "Rx-Verordnungen STIEGEN ebenfalls"),
        ("UK ED-Markt (2023)", "USD 260 Mio. (CAGR 7.2%)"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    row += 2
    ws2.merge_range(row, 1, row, 5, "BfArM SVA-Entscheidungen", fmt["section"])
    for label, value in [
        ("Januar 2022", "1. Ablehnung (50mg)"),
        ("Oktober 2022", "BMG erklaert: WILL OTC-Switch"),
        ("Juli 2023", "2. Ablehnung (25mg + 50mg Sild. + Tadalafil)"),
        ("Januar 2025", "3. Ablehnung (keine neuen Daten)"),
        ("Status", "BMG hat noch nie SVA ueberstimmt – waere Praezedenzfall"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"])
        ws2.merge_range(row, 2, row, 5, value, fmt["label"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 3: OMNICHANNEL
    # ═══════════════════════════════════════════════════════════════════
    ws3 = wb.add_worksheet("Apothekenverteilung")
    ws3.hide_gridlines(2)
    ws3.set_tab_color("#7c3aed")
    ws3.set_column("A:A", 3)
    ws3.set_column("B:B", 12)
    ws3.set_column("C:N", 14)

    params = SildenafilOtcParams()
    df = forecast_sildenafil_otc(params)
    kpis = calculate_kpis_sildenafil(df)

    row = 1
    ws3.merge_range(row, 1, row, 8, "Apothekenverteilung – OTC Sildenafil (apothekenpflichtig)", fmt["title"])

    row += 2
    headers_ch = [
        "Monat", "Apotheke\nTabl.", "Apotheke\nAnteil", "Apotheke\nUmsatz",
        "Online\nTabl.", "Online\nAnteil", "Online\nUmsatz",
        "Gesamt\nOTC Tabl.",
    ]
    for c, h in enumerate(headers_ch):
        ws3.write(row, 1 + c, h, fmt["th_purple"])
    ws3.set_row(row, 35)
    data_start_ch = row + 1

    for i, (_, r) in enumerate(df.iterrows()):
        row += 1
        is_alt = i % 2 == 1
        ws3.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
        ws3.write(row, 2, r["ch_apotheke_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 3, r["ch_apotheke_share"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws3.write(row, 4, r["ch_apotheke_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 5, r["ch_online_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 6, r["ch_online_share"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws3.write(row, 7, r["ch_online_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 8, r["otc_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
    data_end_ch = row

    # Channel chart
    chart_ch = wb.add_chart({"type": "area", "subtype": "stacked"})
    chart_ch.add_series({"name": "Apotheke", "categories": ["Apothekenverteilung", data_start_ch, 1, data_end_ch, 1],
        "values": ["Apothekenverteilung", data_start_ch, 2, data_end_ch, 2], "fill": {"color": "#1e3a5f"}})
    chart_ch.add_series({"name": "Online", "categories": ["Apothekenverteilung", data_start_ch, 1, data_end_ch, 1],
        "values": ["Apothekenverteilung", data_start_ch, 5, data_end_ch, 5], "fill": {"color": "#0d9488"}})
    chart_ch.set_title({"name": "OTC-Volumen nach Vertriebskanal"})
    chart_ch.set_y_axis({"name": "Tabletten", "num_format": "#,##0"})
    chart_ch.set_size({"width": 800, "height": 380})
    chart_ch.set_legend({"position": "bottom"})
    ws3.insert_chart("B" + str(row + 3), chart_ch)

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 4: FORECAST
    # ═══════════════════════════════════════════════════════════════════
    ws4 = wb.add_worksheet("Forecast")
    ws4.hide_gridlines(2)
    ws4.set_tab_color("#0d9488")
    ws4.set_column("A:A", 3)
    ws4.set_column("B:B", 12)
    ws4.set_column("C:Q", 14)

    row = 1
    ws4.merge_range(row, 1, row, 12, "Sildenafil Rx-to-OTC Forecast – Dual Channel (Base Case)", fmt["title"])

    row += 2
    co = kpis.get("crossover_month")
    co_text = f"Monat {co}" if co else "–"
    kpi_data = [
        ("OTC Umsatz Jahr 1", kpis["year1_otc_revenue"], "kpi_value"),
        ("Gesamtumsatz 5J", kpis["total_5y_revenue"], "kpi_value"),
        ("Gewinn 5J", kpis["total_5y_profit"], "kpi_value"),
        ("Online-Anteil M24", kpis["online_share_m24"], "kpi_value_pct"),
        ("OTC > Rx ab", co_text, "kpi_value_plain"),
    ]
    for c, (label, value, vfmt) in enumerate(kpi_data):
        col = 1 + c * 2
        ws4.merge_range(row, col, row, col + 1, label, fmt["kpi_label"])
        ws4.merge_range(row + 1, col, row + 1, col + 1, value, fmt[vfmt])

    row += 4
    headers = [
        "Monat", "Rx\nTabl.", "Rx\nUmsatz",
        "OTC\nTabl.", "OTC Preis\n/Tab", "OTC Retail\nUmsatz", "OTC Herst.\nUmsatz",
        "Marke\nTabl.", "Generika\nTabl.", "Marke\n%",
        "Saison",
        "Gesamt\nUmsatz", "Oper.\nGewinn",
        "Kum.\nUmsatz", "Kum.\nGewinn",
    ]
    for c, h in enumerate(headers):
        ws4.write(row, 1 + c, h, fmt["th_teal"])
    ws4.set_row(row, 35)
    data_start = row + 1

    for i, (_, r) in enumerate(df.iterrows()):
        row += 1
        is_alt = i % 2 == 1
        ws4.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
        ws4.write(row, 2, r["rx_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 3, r["rx_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 4, r["otc_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 5, r["otc_price_per_tablet"], fmt["row_alt_eur"] if is_alt else fmt["eur_detail"])
        ws4.write(row, 6, r["otc_retail_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 7, r["otc_manufacturer_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 8, r["otc_brand_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 9, r["otc_generic_tablets"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 10, r["otc_brand_share"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws4.write(row, 11, r["season_factor"], fmt["row_alt"] if is_alt else fmt["mult"])
        ws4.write(row, 12, r["total_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 13, r["operating_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 14, r["cumulative_total_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 15, r["cumulative_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
    data_end = row

    # Chart: Dual channel packs
    chart1 = wb.add_chart({"type": "line"})
    chart1.add_series({"name": "Rx Tabletten", "categories": ["Forecast", data_start, 1, data_end, 1],
        "values": ["Forecast", data_start, 2, data_end, 2], "line": {"color": "#2563eb", "width": 2.5}})
    chart1.add_series({"name": "OTC Tabletten", "categories": ["Forecast", data_start, 1, data_end, 1],
        "values": ["Forecast", data_start, 4, data_end, 4], "line": {"color": "#0d9488", "width": 2.5}})
    chart1.set_title({"name": "Dual-Kanal: Rx vs. OTC Tabletten"})
    chart1.set_y_axis({"name": "Tabletten / Monat", "num_format": "#,##0"})
    chart1.set_size({"width": 800, "height": 380})
    chart1.set_legend({"position": "bottom"})
    ws4.insert_chart("B" + str(row + 3), chart1)

    # Chart: Brand vs Generic
    chart2 = wb.add_chart({"type": "area", "subtype": "stacked"})
    chart2.add_series({"name": "Viagra Connect", "categories": ["Forecast", data_start, 1, data_end, 1],
        "values": ["Forecast", data_start, 8, data_end, 8], "fill": {"color": "#1e40af"}})
    chart2.add_series({"name": "Generika OTC", "categories": ["Forecast", data_start, 1, data_end, 1],
        "values": ["Forecast", data_start, 9, data_end, 9], "fill": {"color": "#94a3b8"}})
    chart2.set_title({"name": "OTC: Viagra Connect vs. Generika"})
    chart2.set_y_axis({"name": "Tabletten / Monat", "num_format": "#,##0"})
    chart2.set_size({"width": 800, "height": 380})
    chart2.set_legend({"position": "bottom"})
    ws4.insert_chart("J" + str(row + 3), chart2)

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 5: DASHBOARD
    # ═══════════════════════════════════════════════════════════════════
    ws5 = wb.add_worksheet("Dashboard")
    ws5.hide_gridlines(2)
    ws5.set_tab_color("#6366f1")
    ws5.set_column("A:A", 3)
    ws5.set_column("B:B", 38)
    ws5.set_column("C:E", 22)

    row = 1
    ws5.merge_range(row, 1, row, 4, "Executive Summary – Sildenafil OTC Switch", fmt["title"])

    row += 2
    ws5.merge_range(row, 1, row, 4, "Szenario-Vergleich", fmt["section"])

    scenario_results = {}
    for sn, sp in [
        ("Konservativ", {"otc_peak_tablets_per_month": 1_200_000, "otc_ramp_months": 24,
                         "marketing_monthly_eur": 300_000, "new_patient_share": 0.55,
                         "rx_decline_rate": 0.12, "brand_otc_share": 0.20}),
        ("Base Case", {}),
        ("Optimistisch", {"otc_peak_tablets_per_month": 2_700_000, "otc_ramp_months": 12,
                          "marketing_monthly_eur": 750_000, "new_patient_share": 0.70,
                          "rx_decline_rate": 0.05, "brand_otc_share": 0.35}),
    ]:
        p = SildenafilOtcParams(**sp)
        scenario_results[sn] = calculate_kpis_sildenafil(forecast_sildenafil_otc(p))

    row += 1
    ws5.write(row, 1, "")
    ws5.write(row, 2, "Konservativ", fmt["th"])
    ws5.write(row, 3, "Base Case", fmt["th_teal"])
    ws5.write(row, 4, "Optimistisch", fmt["th"])

    for label, key, vtype in [
        ("OTC Umsatz Jahr 1", "year1_otc_revenue", "eur"),
        ("Gesamtumsatz 5J (Rx+OTC)", "total_5y_revenue", "eur"),
        ("OTC Umsatz 5J", "total_5y_otc_revenue", "eur"),
        ("Rx Umsatz 5J", "total_5y_rx_revenue", "eur"),
        ("Gewinn 5J", "total_5y_profit", "eur"),
        ("OTC-Anteil M12 (Tabletten)", "otc_share_m12", "pct"),
        ("OTC-Anteil M24 (Tabletten)", "otc_share_m24", "pct"),
        ("Viagra Markenanteil M12", "brand_share_m12", "pct"),
        ("Online-Anteil M24", "online_share_m24", "pct"),
        ("Rx-Rueckgang gesamt", "rx_decline_total", "pct"),
        ("Therapiequote (neu)", "treatment_rate_final", "pct"),
        ("Marketing-Invest 5J", "total_5y_marketing", "eur"),
    ]:
        row += 1
        ws5.write(row, 1, label, fmt["label_bold"])
        for c, sn in enumerate(["Konservativ", "Base Case", "Optimistisch"]):
            val = scenario_results[sn].get(key, 0) or 0
            if vtype == "eur":
                ws5.write(row, 2 + c, val, fmt["eur"])
            elif vtype == "pct":
                ws5.write(row, 2 + c, val, fmt["pct"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 6: METHODIK
    # ═══════════════════════════════════════════════════════════════════
    ws6 = wb.add_worksheet("Methodik")
    ws6.hide_gridlines(2)
    ws6.set_tab_color("#6366f1")
    ws6.set_column("A:A", 3)
    ws6.set_column("B:B", 38)
    ws6.set_column("C:C", 28)
    ws6.set_column("D:D", 52)
    ws6.set_column("E:E", 42)

    row = 1
    ws6.merge_range(row, 1, row, 4, "Methodik & Transparenz-Matrix", fmt["title"])
    row += 1
    ws6.merge_range(row, 1, row, 4, "Jeder Datenpunkt ist klassifiziert: FAKT / ANNAHME / MODELL / LUECKE",
        wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

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

    row += 2
    ws6.merge_range(row, 1, row, 4, "FAKTEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Datenpunkt", "Wert", "Quelle", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    facts = [
        ("ED-Praevalenz DE", "4-6 Mio. (Cologne Male Survey)", "Nature / Braun et al.", "FAKT"),
        ("Therapiequote", "30% (May et al. 2007; Arnold 2023)", "Viatris DE / Handelsblatt", "FAKT"),
        ("PDE5-Markt DE", "~2.6 Mio. Pack./Jahr", "IQVIA / Apotheke Adhoc", "FAKT"),
        ("Sildenafil-Anteil", "55-65% der PDE5-Packs", "Apotheke Adhoc / Handelsblatt", "FAKT"),
        ("Viagra Markenanteil", "~10% der Sild.-Packs", "Apotheke Adhoc", "FAKT"),
        ("Generika-Preis", "EUR 0.95-2.30/Tablette", "GoSpring / Zava", "FAKT"),
        ("BfArM SVA: 3x abgelehnt", "2022, 2023, 2025", "Citeline / Apotheke Adhoc", "FAKT"),
        ("BMG will Switch", "Okt. 2022 erklaert", "Citeline / HBW Insight", "FAKT"),
        ("UK Viagra Connect", "Maerz 2018, GBP 5/Tab", "MHRA / Boots", "FAKT"),
        ("UK: 63% Neupatienten", "n=1.162, Lee et al. 2021", "PMC / IJCP", "FAKT"),
        ("UK: Rx STIEG post-Switch", "NHS Rx nicht kannibalisiert", "PAGB/Frontier Economics", "FAKT"),
        ("GKV: keine Erstattung ED", "Lifestyle-AM (SGB V)", "GKV-SV", "FAKT"),
        ("Online-Apotheke CAGR OTC", "12.6% durch 2030", "Grand View Research", "FAKT"),
    ]
    for dp, val, source, cat in facts:
        row += 1
        ws6.write(row, 1, dp, fmt["label_bold"])
        ws6.write(row, 2, val, fmt["fact"])
        ws6.write(row, 3, source, fmt["label"])
        ws6.write(row, 4, cat, fmt["fact"])

    row += 2
    ws6.merge_range(row, 1, row, 4, "ANNAHMEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Default", "Begruendung", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    assumptions = [
        ("OTC Peak Vol.", "2.1M Tabl./Mon.", "Hochrechnung: UK + DE-Marktgroesse", "ANNAHME"),
        ("OTC Preis", "EUR 5.99/Tab", "Zwischen UK GBP 5 und Rx-Generika EUR 1.50", "ANNAHME"),
        ("Neue Patienten", "63%", "UK-Referenz: 63% nie vorher behandelt", "ANNAHME"),
        ("Rx-Rueckgang", "8%", "UK: Rx stieg sogar! Konservativ: -8%", "ANNAHME"),
        ("Online-Anteil", "45% (steigend)", "Anonymitaet = Kernvorteil bei ED/Stigma", "ANNAHME"),
        ("Markenanteil", "25% (sinkend)", "Viagra-Brand stark, aber Generikadruck", "ANNAHME"),
        ("Marketing", "EUR 500K/Mon.", "Hoeher als PPI: DTC Brand Building", "ANNAHME"),
    ]
    for param, val, reason, cat in assumptions:
        row += 1
        ws6.write(row, 1, param, fmt["label_bold"])
        ws6.write(row, 2, val, fmt["assumption"])
        ws6.write(row, 3, reason, fmt["label"])
        ws6.write(row, 4, cat, fmt["assumption"])

    row += 2
    ws6.merge_range(row, 1, row, 4, "MODELLE", fmt["section"])
    row += 1
    for c, h in enumerate(["Modell", "Formel / Logik", "Referenz", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    models = [
        ("OTC-Ramp", "Logistic S-Curve (peak, midpoint, steepness)", "UK Viagra Connect Launch-Kurve", "MODELL"),
        ("Rx-Effekt", "Exp. Decay mit hohem Floor (92%)", "UK: Rx stieg – konservativ modelliert", "MODELL"),
        ("Apothekenverteilung", "2 Kanaele (apothekenpflichtig)", "Online CAGR 12.6%, Discretion-Faktor", "MODELL"),
        ("Discretion-Bonus", "Kanal-Volumen * (1 + (disc-0.7)*0.15)", "ED-Stigma treibt anonyme Kanaele", "MODELL"),
        ("Markenanteil-Erosion", "Linear: -3Pp/Jahr, Floor 10%", "Generikadruck analog UK", "MODELL"),
        ("Tadalafil-Migration", "Logistic: 12% der Tada-Tabl. zu OTC Sild.", "Convenience-Vorteil OTC", "MODELL"),
    ]
    for name, formula, ref, cat in models:
        row += 1
        ws6.set_row(row, 35)
        ws6.write(row, 1, name, fmt["label_bold"])
        ws6.write(row, 2, formula, fmt["model"])
        ws6.write(row, 3, ref, fmt["label"])
        ws6.write(row, 4, cat, fmt["model"])

    row += 2
    ws6.merge_range(row, 1, row, 4, "LUECKEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Gap", "Beschreibung", "Datenquelle", "Kat."]):
        ws6.write(row, 1 + c, h, fmt["th"])
    gaps = [
        ("IQVIA PDE5-Detaildaten", "Monatl. Pack./Umsatz pro Produkt + Kanal", "IQVIA Prescription Analytics", "LUECKE"),
        ("Apotheken-Empfehlungsverhalten", "Substitutionspraeferenzen bei OTC-Beratung", "IQVIA / GfK Panel", "LUECKE"),
        ("Consumer-Tracking ED", "Awareness, Consideration, Trial auf Produktebene", "GfK / Kantar Consumer Panel", "LUECKE"),
        ("Preiselastizitaet (gemessen)", "Conjoint-Analyse fuer OTC ED-Preispunkte", "Primaerforschung / Scanner-Daten", "LUECKE"),
        ("Online-Kanal Split", "Marktanteile DocMorris vs. Shop Apotheke fuer ED", "SEMPORA / IQVIA", "LUECKE"),
        ("BfArM Switch-Wahrscheinlichkeit", "Politische Dynamik BMG vs. SVA", "Regulatorische Intelligence", "LUECKE"),
    ]
    for gap_name, desc, source, cat in gaps:
        row += 1
        ws6.write(row, 1, gap_name, fmt["label_bold"])
        ws6.write(row, 2, desc, fmt["gap"])
        ws6.write(row, 3, source, fmt["label"])
        ws6.write(row, 4, cat, fmt["gap"])

    row += 3
    ws6.merge_range(row, 1, row, 4,
        "Hinweis: Alle Daten synthetisch. Referenzen: UK Viagra Connect (2018), IQVIA PDE5-Markt DE, "
        "BfArM SVA-Protokolle, PMC Lee et al. 2021, Viatris Investor Relations. Kein Bezug zu vertraulichen Daten.",
        fmt["hint"])

    wb.close()
    print(f"Excel model saved to: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    build_model()
