"""
Build a professional Excel forecast model for the GLP-1 Brand Competition scenario.

Patient-based model with per-indication revenue streams.

Sheets:
1. INPUTS          – All user-configurable parameters (yellow cells)
2. Marktdaten      – GLP-1 market context, products, differentiation
3. Lilly Forecast  – Mounjaro perspective (monthly forecast)
4. Novo Forecast   – Ozempic/Wegovy perspective (monthly forecast)
5. Dashboard       – Executive summary, scenario comparison
6. Methodik        – Transparency matrix: Facts vs. Assumptions vs. Models
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import xlsxwriter
import numpy as np
import pandas as pd
from models.brand_competition_engine import (
    IndicationParams, BrandParams, MarketParams,
    forecast_brand, calculate_kpis_brand,
    default_lilly_indications, default_novo_indications,
)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "GLP1_Brand_Competition_Forecast.xlsx")


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
    fmt["input_bool"] = wb.add_format({"bg_color": "#FFF9C4", "border": 1, "border_color": "#E0B800", "font_color": "#1a237e", "bold": True, "align": "center"})
    fmt["label"] = wb.add_format({"font_size": 10, "font_color": "#374151", "text_wrap": True, "valign": "vcenter"})
    fmt["label_bold"] = wb.add_format({"font_size": 10, "font_color": "#374151", "bold": True, "valign": "vcenter"})
    fmt["hint"] = wb.add_format({"font_size": 9, "font_color": "#9ca3af", "italic": True, "text_wrap": True, "valign": "vcenter"})
    fmt["number"] = wb.add_format({"num_format": "#,##0"})
    fmt["eur"] = wb.add_format({"num_format": "€#,##0"})
    fmt["eur_detail"] = wb.add_format({"num_format": "€#,##0.00"})
    fmt["pct"] = wb.add_format({"num_format": "0.0%"})
    fmt["mult"] = wb.add_format({"num_format": "0.000"})
    fmt["th"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#1e3a5f", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_orange"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#9a3412", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_blue"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#1e40af", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_green"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#166534", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["kpi_label"] = wb.add_format({"bold": True, "font_size": 11, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1})
    fmt["kpi_value"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "num_format": "0.0%", "align": "center"})
    fmt["kpi_value_orange"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#9a3412", "bg_color": "#fef3c7", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_orange_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#9a3412", "bg_color": "#fef3c7", "border": 1, "num_format": "0.0%", "align": "center"})
    fmt["kpi_value_blue"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e40af", "bg_color": "#dbeafe", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_blue_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e40af", "bg_color": "#dbeafe", "border": 1, "num_format": "0.0%", "align": "center"})
    fmt["kpi_value_green"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#166534", "bg_color": "#f0fdf4", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_plain"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "align": "center"})
    fmt["row_alt"] = wb.add_format({"bg_color": "#f8fafc"})
    fmt["row_alt_eur"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "€#,##0"})
    fmt["row_alt_pct"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "0.0%"})
    fmt["row_alt_num"] = wb.add_format({"bg_color": "#f8fafc", "num_format": "#,##0"})
    # Methodik formats
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
    ws.merge_range(row, 1, row, 3, "GLP-1 Brand Competition - Patientenbasiertes Forecast Modell", fmt["title"])
    row += 1
    ws.merge_range(row, 1, row, 3, "Mounjaro (Tirzepatid, Lilly) vs. Ozempic/Wegovy (Semaglutid, Novo Nordisk)", wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    # 1. Indikation: T2D
    row += 2
    ws.merge_range(row, 1, row, 3, "1. INDIKATION: DIABETES (T2D)", fmt["section"])
    for label, value, fk, hint in [
        ("Patienten in Deutschland", 6_330_000, "input", "GKV-Versicherte mit Diabetes mellitus Typ 2"),
        ("GLP-1-Behandlungsrate aktuell", 0.139, "input_pct", "13.9% der T2D-Patienten auf GLP-1 (BARMER 2025)"),
        ("GLP-1-Behandlungsrate Ziel", 0.22, "input_pct", "Erwartete Penetration durch Leitlinien-Shift"),
        ("Mein Marktanteil Start (Lilly)", 0.08, "input_pct", "Mounjaro aktuell ~8% und steigend"),
        ("Mein Marktanteil Peak (Lilly)", 0.25, "input_pct", "Angestrebter Spitzenanteil T2D"),
        ("Wettbewerber Start (Novo)", 0.36, "input_pct", "Ozempic + Wegovy kombiniert ~36%"),
        ("Wettbewerber Peak (Novo)", 0.30, "input_pct", "Verteidigbare Position"),
        ("Preis / Monat Mounjaro (EUR)", 350.00, "input_eur", "~EUR 206-490/Monat, Durchschn. ~EUR 350"),
        ("Preis / Monat Ozempic (EUR)", 300.00, "input_eur", "~EUR 300/Monat (1mg Erhaltungsdosis)"),
        ("Therapietreue nach 12 Monaten", 0.70, "input_pct", "70% der Patienten noch auf Therapie"),
        ("GKV-Erstattung", "JA", "input_bool", "Vollstaendig GKV-erstattet"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 2. Indikation: Adipositas
    row += 2
    ws.merge_range(row, 1, row, 3, "2. INDIKATION: ADIPOSITAS", fmt["section"])
    for label, value, fk, hint in [
        ("Patienten in Deutschland", 8_000_000, "input", "BMI >= 30 in Deutschland"),
        ("Behandlungsrate aktuell", 0.006, "input_pct", "~50K von 8M (0.6%, meist Selbstzahler)"),
        ("Behandlungsrate Ziel (ohne GKV)", 0.015, "input_pct", "1.5% = nur Selbstzahler"),
        ("Behandlungsrate Ziel (mit GKV)", 0.05, "input_pct", "5% bei GKV-Erstattung = 400K Patienten"),
        ("Mein Marktanteil Peak (Lilly)", 0.35, "input_pct", "Mounjaro Spitzenanteil Adipositas"),
        ("Wettbewerber Peak (Novo)", 0.15, "input_pct", "Wegovy (eingeschraenkt, kein GKV)"),
        ("Preis / Monat Mounjaro (EUR)", 300.00, "input_eur", "Adipositas-Dosis"),
        ("Preis / Monat Wegovy (EUR)", 277.00, "input_eur", "Wegovy Preis nach April 2025 Reduktion"),
        ("Therapietreue nach 12 Monaten", 0.45, "input_pct", "Niedrigere Adhaerenz als T2D"),
        ("GKV-Erstattung Adipositas", "NEIN", "input_bool", "G-BA Juni 2024: Lifestyle-Arzneimittel"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 3. Indikation: CV-Risiko
    row += 2
    ws.merge_range(row, 1, row, 3, "3. INDIKATION: CV-RISIKOREDUKTION (optional)", fmt["section"])
    for label, value, fk, hint in [
        ("Patienten in Deutschland", 2_000_000, "input", "Patienten mit erhoehtem CV-Risiko"),
        ("Behandlungsrate Ziel", 0.05, "input_pct", "5% der Zielpopulation"),
        ("Mein Marktanteil Peak", 0.20, "input_pct", "Abhaengig von Studiendaten"),
        ("Preis / Monat (EUR)", 350.00, "input_eur", "Gleiches Preisniveau wie T2D"),
        ("Therapietreue nach 12 Monaten", 0.65, "input_pct", "Chronische Indikation"),
        ("Indikation aktiv", "NEIN", "input_bool", "Noch nicht zugelassen (Studien laufen)"),
        ("Verzoegerung (Monate)", 6, "input", "Monate nach Forecast-Start bis Marktzugang"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 4. Indikation: MASH
    row += 2
    ws.merge_range(row, 1, row, 3, "4. INDIKATION: MASH / NASH (optional)", fmt["section"])
    for label, value, fk, hint in [
        ("Patienten in Deutschland", 1_500_000, "input", "MASH/NASH Patienten"),
        ("Behandlungsrate Ziel", 0.03, "input_pct", "3% der Zielpopulation"),
        ("Mein Marktanteil Peak", 0.25, "input_pct", "Lilly fuehrend in MASH-Entwicklung"),
        ("Preis / Monat (EUR)", 350.00, "input_eur", "Premium-Indikation"),
        ("Therapietreue nach 12 Monaten", 0.60, "input_pct", "Lebererkrankung"),
        ("Indikation aktiv", "NEIN", "input_bool", "Studien laufen"),
        ("Verzoegerung (Monate)", 18, "input", "Spaetere Zulassung erwartet"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 5. Kosten
    row += 2
    ws.merge_range(row, 1, row, 3, "5. KOSTEN & PROFITABILITAET", fmt["section"])
    for label, value, fk, hint in [
        ("COGS (% vom Umsatz)", 0.20, "input_pct", "Biologika/Peptide: typisch 15-25%"),
        ("SG&A / Monat (EUR)", 800_000, "input", "Vertrieb, KAM, Marketing"),
        ("Medical Affairs / Monat (EUR)", 200_000, "input", "MSL, Studien, Kongresse"),
        ("Preistrend p.a.", -0.03, "input_pct", "Jaehrliche Preiserosion (-3%)"),
        ("Forecast-Horizont (Jahre)", 5, "input", "Prognosezeitraum"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 6. Szenarien
    row += 2
    ws.merge_range(row, 1, row, 4, "6. SZENARIO-DEFINITIONEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Base Case", "Bull (Lilly)", "Bull (Novo)"]):
        ws.write(row, 1 + c, h, fmt["th"])
    for param, base, bull_l, bull_n in [
        ("Mounjaro Peak Share T2D", 0.25, 0.35, 0.15),
        ("Mounjaro Peak Share Adipositas", 0.35, 0.45, 0.20),
        ("Monate bis Peak", 36, 24, 48),
        ("Novo Peak Share T2D", 0.30, 0.25, 0.38),
        ("Adipositas GKV-Erstattung", "Nein", "Ja", "Nein"),
        ("Behandlungsrate T2D Ziel", 0.22, 0.28, 0.20),
    ]:
        row += 1
        ws.write(row, 1, param, fmt["label_bold"])
        for c, val in enumerate([base, bull_l, bull_n]):
            if isinstance(val, float):
                ws.write(row, 2 + c, val, fmt["input_pct"])
            elif isinstance(val, int):
                ws.write(row, 2 + c, val, fmt["input"])
            else:
                ws.write(row, 2 + c, val, fmt["input_text"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 2: MARKTDATEN
    # ═══════════════════════════════════════════════════════════════════
    ws2 = wb.add_worksheet("Marktdaten")
    ws2.hide_gridlines(2)
    ws2.set_tab_color("#1e3a5f")
    ws2.set_column("A:A", 3)
    ws2.set_column("B:B", 32)
    ws2.set_column("C:H", 18)

    row = 1
    ws2.merge_range(row, 1, row, 7, "GLP-1 Wettbewerbslandschaft - Deutschland (Mid-2025)", fmt["title"])
    row += 2
    for c, h in enumerate(["Produkt", "Hersteller", "Marktanteil\n(TRx)", "Preis/Mon.\n(EUR)", "Indikation", "GKV", "Lieferung"]):
        ws2.write(row, 1 + c, h, fmt["th"])
    ws2.set_row(row, 30)

    products = [
        ("Ozempic (Semaglutid s.c.)", "Novo Nordisk", 0.32, 300.00, "T2D", "Ja", "Engpass"),
        ("Trulicity (Dulaglutid)", "Eli Lilly", 0.38, 178.00, "T2D", "Ja", "OK"),
        ("Mounjaro (Tirzepatid)", "Eli Lilly", 0.08, 350.00, "T2D + Adipositas", "Ja (T2D)", "OK"),
        ("Rybelsus (Semaglutid oral)", "Novo Nordisk", 0.07, 280.00, "T2D", "Ja", "OK"),
        ("Victoza (Liraglutid)", "Novo Nordisk", 0.06, 195.00, "T2D", "Ja", "Engpass"),
        ("Wegovy (Semaglutid 2.4mg)", "Novo Nordisk", 0.04, 277.00, "Adipositas", "NEIN", "Engpass"),
        ("Sonstige (Exenatid etc.)", "Diverse", 0.05, 150.00, "T2D", "Ja", "OK"),
    ]
    for pn, co, sh, pr, ind, gkv, supply in products:
        row += 1
        ws2.write(row, 1, pn, fmt["label_bold"])
        ws2.write(row, 2, co, fmt["label"])
        ws2.write(row, 3, sh, fmt["pct"])
        ws2.write(row, 4, pr, fmt["eur_detail"])
        ws2.write(row, 5, ind, fmt["label"])
        ws2.write(row, 6, gkv, fmt["label"])
        ws2.write(row, 7, supply, fmt["label"])

    # Differentiation
    row += 3
    ws2.merge_range(row, 1, row, 7, "Wettbewerbsdifferenzierung: Mounjaro vs. Ozempic", fmt["section"])
    row += 1
    for c, h in enumerate(["Dimension", "Mounjaro (Tirzepatid)", "Ozempic (Semaglutid)", "Vorteil"]):
        ws2.write(row, 1 + c, h, fmt["th"])
    diffs = [
        ("Mechanismus", "Dual GIP/GLP-1 RA", "Mono GLP-1 RA", "Mounjaro"),
        ("HbA1c-Reduktion", "-2.4 %-Punkte", "-1.8 %-Punkte", "Mounjaro"),
        ("Gewichtsverlust", "-22.5%", "-15.0%", "Mounjaro"),
        ("Evidenzbasis", "Wachsend (SURPASS/SURMOUNT)", "Am breitesten (SUSTAIN/STEP/SELECT)", "Ozempic"),
        ("GKV Adipositas", "Ja (via Mounjaro)", "Nein (Wegovy ausgeschlossen)", "Mounjaro"),
        ("Versorgungslage", "Gut", "Lieferengpass seit 2022", "Mounjaro"),
        ("Marktpraesenz", "Seit Nov 2023 (kurz)", "Seit Feb 2020 (etabliert)", "Ozempic"),
        ("AMNOG-Preis", "Vertraulich (ab Aug 2025)", "Vereinbart (oeffentlich)", "Neutral"),
    ]
    for dim, mj, oz, adv in diffs:
        row += 1
        ws2.write(row, 1, dim, fmt["label_bold"])
        ws2.write(row, 2, mj, fmt["label"])
        ws2.write(row, 3, oz, fmt["label"])
        color = fmt["fact"] if adv == "Mounjaro" else (fmt["model"] if adv == "Ozempic" else fmt["assumption"])
        ws2.write(row, 4, adv, color)

    # Growth drivers
    row += 3
    ws2.merge_range(row, 1, row, 5, "Marktwachstumstreiber", fmt["section"])
    row += 1
    for c, h in enumerate(["Treiber", "Auswirkung", "Zeithorizont", "Sicherheit"]):
        ws2.write(row, 1 + c, h, fmt["th"])
    drivers = [
        ("Leitlinien-Shift T2D", "GLP-1 frueher in Therapie: 14% -> 25-30%", "2025-2030", "Hoch"),
        ("Adipositas GKV-Erstattung", "8M potenzielle Patienten", "Fruehestens 2027", "Mittel"),
        ("CV-Risikoreduktion (SELECT)", "-20% CV-Events -> breitere Zielgruppe", "2025-2026", "Hoch"),
        ("MASH/NASH-Indikation", "Neue Patientenpopulation", "2026-2028", "Mittel"),
        ("Orales Semaglutid 25/50mg", "Convenience-Shift weg von Injektion", "2025-2026", "Hoch"),
        ("Behebung Lieferengpaesse", "Aufholen unterdrueckter Nachfrage", "2025", "Hoch"),
    ]
    for driver, impact, timeline, certainty in drivers:
        row += 1
        ws2.write(row, 1, driver, fmt["label_bold"])
        ws2.write(row, 2, impact, fmt["label"])
        ws2.write(row, 3, timeline, fmt["label"])
        cert_fmt = fmt["fact"] if certainty == "Hoch" else fmt["assumption"]
        ws2.write(row, 4, certainty, cert_fmt)

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 3 & 4: FORECAST (Lilly + Novo)
    # ═══════════════════════════════════════════════════════════════════
    def write_forecast_sheet(ws, brand, sheet_name, color_key, th_fmt_key):
        ws.hide_gridlines(2)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 12)
        ws.set_column("C:T", 15)

        df = forecast_brand(brand, forecast_months=60)
        kpis = calculate_kpis_brand(df)

        row = 1
        ws.merge_range(row, 1, row, 14, f"{brand.company} Perspektive - {brand.name} (Base Case)", fmt["title"])

        # KPI row
        row += 2
        ot = kpis.get("overtake_month")
        ot_text = f"Monat {ot}" if ot else "–"
        kpi_data = [
            ("Umsatz Jahr 1", kpis["year1_revenue"], f"kpi_value_{color_key}"),
            ("Umsatz 5J", kpis["total_5y_revenue"], f"kpi_value_{color_key}"),
            ("Peak Patienten", kpis["peak_patients"], "kpi_value_plain"),
            ("Market Leader ab", ot_text, "kpi_value_plain"),
            ("Gewinn 5J", kpis["total_5y_profit"], "kpi_value_green"),
        ]
        for c, (label, value, vfmt) in enumerate(kpi_data):
            col = 1 + c * 2
            ws.merge_range(row, col, row, col + 1, label, fmt["kpi_label"])
            ws.merge_range(row + 1, col, row + 1, col + 1, value, fmt[vfmt])

        # Data headers
        row += 4
        headers = [
            "Monat", "Mon.\nvon Start",
            "Patienten\nGesamt", "Patienten\nT2D", "Patienten\nAdipo",
            "Patienten\nCV", "Patienten\nMASH",
            "Umsatz\nGesamt (EUR)", "Umsatz\nT2D (EUR)", "Umsatz\nAdipo (EUR)",
            "Mein Anteil\n(gewichtet)", "Comp.\nAnteil",
            "Comp.\nPatienten", "Comp.\nUmsatz (EUR)",
            "Oper. Gewinn\n(EUR)", "Kum. Umsatz\n(EUR)", "Kum. Gewinn\n(EUR)",
            "Supply\nGap",
        ]
        for c, h in enumerate(headers):
            ws.write(row, 1 + c, h, fmt[th_fmt_key])
        ws.set_row(row, 35)
        data_start = row + 1

        for i, (_, r) in enumerate(df.iterrows()):
            row += 1
            is_alt = i % 2 == 1
            ws.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
            ws.write(row, 2, r["months_from_start"], fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 3, r["my_patients"], fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 4, r.get("patients_t2d", 0), fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 5, r.get("patients_adipositas", 0), fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 6, r.get("patients_cvrisiko", 0), fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 7, r.get("patients_mash", 0), fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 8, r["my_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 9, r.get("revenue_t2d", 0), fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 10, r.get("revenue_adipositas", 0), fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 11, r["my_share_weighted"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
            ws.write(row, 12, r["comp_share_weighted"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
            ws.write(row, 13, r["comp_patients"], fmt["row_alt_num"] if is_alt else fmt["number"])
            ws.write(row, 14, r["comp_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 15, r["my_operating_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 16, r["cumulative_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 17, r["cumulative_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
            ws.write(row, 18, r["supply_gap"], fmt["row_alt_num"] if is_alt else fmt["number"])
        data_end = row

        # Chart 1: Market Share Race
        chart1 = wb.add_chart({"type": "line"})
        chart1.add_series({
            "name": brand.name.split("(")[0].strip(),
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 11, data_end, 11],
            "line": {"color": "#f59e0b" if color_key == "orange" else "#2563eb", "width": 2.5},
        })
        chart1.add_series({
            "name": "Wettbewerber",
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 12, data_end, 12],
            "line": {"color": "#2563eb" if color_key == "orange" else "#f59e0b", "width": 2.5, "dash_type": "dash"},
        })
        chart1.set_title({"name": "Marktanteils-Wettlauf (gewichtet)"})
        chart1.set_y_axis({"name": "Marktanteil", "num_format": "0%"})
        chart1.set_size({"width": 800, "height": 380})
        chart1.set_legend({"position": "bottom"})
        ws.insert_chart("B" + str(row + 3), chart1)

        # Chart 2: Revenue Build-up (stacked by indication)
        chart2 = wb.add_chart({"type": "column", "subtype": "stacked"})
        chart2.add_series({
            "name": "T2D",
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 9, data_end, 9],
            "fill": {"color": "#3b82f6"},
        })
        chart2.add_series({
            "name": "Adipositas",
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 10, data_end, 10],
            "fill": {"color": "#22c55e"},
        })
        chart2_line = wb.add_chart({"type": "line"})
        chart2_line.add_series({
            "name": "Kum. Umsatz",
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 16, data_end, 16],
            "line": {"color": "#166534", "width": 2.5},
            "y2_axis": True,
        })
        chart2.combine(chart2_line)
        chart2.set_title({"name": "Umsatz nach Indikation"})
        chart2.set_y_axis({"name": "Monatl. Umsatz (EUR)"})
        chart2.set_y2_axis({"name": "Kumuliert (EUR)"})
        chart2.set_size({"width": 800, "height": 380})
        chart2.set_legend({"position": "bottom"})
        ws.insert_chart("J" + str(row + 3), chart2)

        # Chart 3: Patients by Indication (stacked area)
        chart3 = wb.add_chart({"type": "area", "subtype": "stacked"})
        chart3.add_series({
            "name": "T2D",
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 4, data_end, 4],
            "fill": {"color": "#93c5fd"}, "line": {"color": "#3b82f6", "width": 1},
        })
        chart3.add_series({
            "name": "Adipositas",
            "categories": [sheet_name, data_start, 1, data_end, 1],
            "values": [sheet_name, data_start, 5, data_end, 5],
            "fill": {"color": "#86efac"}, "line": {"color": "#22c55e", "width": 1},
        })
        chart3.set_title({"name": "Patienten nach Indikation"})
        chart3.set_y_axis({"name": "Patienten / Monat", "num_format": "#,##0"})
        chart3.set_size({"width": 800, "height": 380})
        ws.insert_chart("B" + str(row + 23), chart3)

        return df, kpis

    # Lilly sheet
    ws3 = wb.add_worksheet("Lilly Forecast")
    ws3.set_tab_color("#f59e0b")
    brand_lilly = BrandParams(
        name="Mounjaro (Tirzepatid)", company="Eli Lilly",
        indications=default_lilly_indications(),
    )
    df_lilly, kpis_lilly = write_forecast_sheet(ws3, brand_lilly, "Lilly Forecast", "orange", "th_orange")

    # Novo sheet
    ws4 = wb.add_worksheet("Novo Forecast")
    ws4.set_tab_color("#2563eb")
    brand_novo = BrandParams(
        name="Ozempic / Wegovy (Semaglutid)", company="Novo Nordisk",
        indications=default_novo_indications(),
    )
    df_novo, kpis_novo = write_forecast_sheet(ws4, brand_novo, "Novo Forecast", "blue", "th_blue")

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
    ws5.merge_range(row, 1, row, 4, "Executive Summary - GLP-1 Brand Competition 2026-2030", fmt["title"])

    # Head-to-head comparison
    row += 2
    ws5.merge_range(row, 1, row, 3, "Head-to-Head Vergleich (Base Case)", fmt["section"])
    row += 1
    ws5.write(row, 1, "", fmt["th"])
    ws5.write(row, 2, "Mounjaro (Lilly)", fmt["th_orange"])
    ws5.write(row, 3, "Ozempic (Novo)", fmt["th_blue"])

    comparisons = [
        ("Umsatz Jahr 1", kpis_lilly["year1_revenue"], kpis_novo["year1_revenue"], "eur"),
        ("Umsatz 5J kumuliert", kpis_lilly["total_5y_revenue"], kpis_novo["total_5y_revenue"], "eur"),
        ("Gewinn 5J kumuliert", kpis_lilly["total_5y_profit"], kpis_novo["total_5y_profit"], "eur"),
        ("Peak Marktanteil", kpis_lilly["peak_share"], kpis_novo["peak_share"], "pct"),
        ("Peak Patienten", kpis_lilly["peak_patients"], kpis_novo["peak_patients"], "num"),
        ("Share Monat 12", kpis_lilly["share_month_12"], kpis_novo["share_month_12"], "pct"),
        ("Share Monat 36", kpis_lilly["share_month_36"], kpis_novo["share_month_36"], "pct"),
        ("Durchschn. Preis/Mon.", kpis_lilly["avg_price"], kpis_novo["avg_price"], "eur"),
    ]
    for label, val_l, val_n, vtype in comparisons:
        row += 1
        ws5.write(row, 1, label, fmt["label_bold"])
        for c, val in enumerate([val_l, val_n]):
            if vtype == "eur":
                ws5.write(row, 2 + c, val, fmt["eur"])
            elif vtype == "pct":
                ws5.write(row, 2 + c, val, fmt["pct"])
            elif vtype == "num":
                ws5.write(row, 2 + c, val, fmt["number"])

    # Indication breakdown
    row += 3
    ws5.merge_range(row, 1, row, 3, "Umsatz nach Indikation (5J, Base Case)", fmt["section"])
    row += 1
    ws5.write(row, 1, "Indikation", fmt["th"])
    ws5.write(row, 2, "Mounjaro (Lilly)", fmt["th_orange"])
    ws5.write(row, 3, "Ozempic (Novo)", fmt["th_blue"])
    for ind_key, ind_label in [("t2d", "T2D"), ("adipositas", "Adipositas"), ("cvrisiko", "CV-Risiko"), ("mash", "MASH")]:
        row += 1
        ws5.write(row, 1, ind_label, fmt["label_bold"])
        ws5.write(row, 2, kpis_lilly["revenue_by_indication"].get(ind_key, 0), fmt["eur"])
        ws5.write(row, 3, kpis_novo["revenue_by_indication"].get(ind_key, 0), fmt["eur"])

    # Scenario comparison for Lilly
    row += 3
    ws5.merge_range(row, 1, row, 4, "Lilly (Mounjaro) - Szenario-Vergleich", fmt["section"])

    scenario_results_lilly = {}
    for sn, overrides in [
        ("Base Case", {}),
        ("Bull (Lilly)", {"t2d_peak": 0.35, "adipo_peak": 0.45, "months": 24, "cv_enabled": True, "adipo_pen": 0.05}),
        ("Bull (Novo)", {"t2d_peak": 0.15, "adipo_peak": 0.20, "months": 48}),
    ]:
        inds = default_lilly_indications()
        if "t2d_peak" in overrides:
            inds[0].my_share_peak = overrides["t2d_peak"]
        if "adipo_peak" in overrides:
            inds[1].my_share_peak = overrides["adipo_peak"]
        if "months" in overrides:
            for ind in inds:
                ind.months_to_peak_share = overrides["months"]
        if overrides.get("cv_enabled"):
            inds[2].enabled = True
        if "adipo_pen" in overrides:
            inds[1].treated_pct_peak = overrides["adipo_pen"]
        b = BrandParams(name="Mounjaro", company="Lilly", indications=inds)
        scenario_results_lilly[sn] = calculate_kpis_brand(forecast_brand(b))

    row += 1
    ws5.write(row, 1, "")
    ws5.write(row, 2, "Base Case", fmt["th"])
    ws5.write(row, 3, "Bull (Lilly)", fmt["th_orange"])
    ws5.write(row, 4, "Bull (Novo)", fmt["th_blue"])

    for label, key, vtype in [
        ("Umsatz Jahr 1", "year1_revenue", "eur"),
        ("Umsatz 5J kumuliert", "total_5y_revenue", "eur"),
        ("Gewinn 5J kumuliert", "total_5y_profit", "eur"),
        ("Peak Marktanteil", "peak_share", "pct"),
        ("Peak Patienten", "peak_patients", "num"),
    ]:
        row += 1
        ws5.write(row, 1, label, fmt["label_bold"])
        for c, sn in enumerate(["Base Case", "Bull (Lilly)", "Bull (Novo)"]):
            val = scenario_results_lilly[sn].get(key, 0) or 0
            if vtype == "eur":
                ws5.write(row, 2 + c, val, fmt["eur"])
            elif vtype == "pct":
                ws5.write(row, 2 + c, val, fmt["pct"])
            elif vtype == "num":
                ws5.write(row, 2 + c, val, fmt["number"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 6: METHODIK
    # ═══════════════════════════════════════════════════════════════════
    ws6 = wb.add_worksheet("Methodik")
    ws6.hide_gridlines(2)
    ws6.set_tab_color("#6366f1")
    ws6.set_column("A:A", 3)
    ws6.set_column("B:B", 34)
    ws6.set_column("C:C", 24)
    ws6.set_column("D:D", 52)
    ws6.set_column("E:E", 42)

    row = 1
    ws6.merge_range(row, 1, row, 4, "Methodik & Transparenz-Matrix", fmt["title"])
    row += 1
    ws6.merge_range(row, 1, row, 4,
        "Patientenbasiertes Forecast-Modell. Jeder Datenpunkt ist klassifiziert: FAKT / ANNAHME / MODELL / LUECKE",
        wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    # Legend
    row += 2
    ws6.write(row, 1, "Legende:", fmt["label_bold"])
    ws6.write(row, 2, "FAKT", fmt["fact"])
    ws6.write(row, 3, "Aus oeffentlichen Quellen ableitbar", fmt["label"])
    row += 1
    ws6.write(row, 2, "ANNAHME", fmt["assumption"])
    ws6.write(row, 3, "Vom User steuerbar (gelbe Zellen)", fmt["label"])
    row += 1
    ws6.write(row, 2, "MODELL", fmt["model"])
    ws6.write(row, 3, "Mathematisches Modell (branchenvalidiert)", fmt["label"])
    row += 1
    ws6.write(row, 2, "LUECKE", fmt["gap"])
    ws6.write(row, 3, "Fuer Produktiveinsatz benoetigt", fmt["label"])

    # Model architecture
    row += 2
    ws6.merge_range(row, 1, row, 4, "MODELL-ARCHITEKTUR: Patientenbasiert", fmt["section"])
    row += 1
    ws6.merge_range(row, 1, row, 4,
        "Pro Indikation, pro Monat:\n"
        "  Patienten = Zielpopulation x Behandlungsrate x Marktanteil x Therapietreue\n"
        "  Umsatz = Patienten x Preis/Monat (mit Erosion)\n"
        "Summe ueber Indikationen -> Gesamtumsatz -> Supply Constraint -> Profitabilitaet",
        wb.add_format({"font_size": 10, "font_color": "#374151", "text_wrap": True, "valign": "vcenter", "bg_color": "#f0f4ff", "border": 1}))
    ws6.set_row(row, 60)

    # Models
    row += 2
    ws6.merge_range(row, 1, row, 4, "MATHEMATISCHE MODELLE", fmt["section"])
    row += 1
    for c, h in enumerate(["Modell", "Formel / Logik", "Validierung / Referenz", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    models = [
        ("Behandlungsrate (S-Kurve)",
         "Rate(t) = Start + (Peak - Start) * sigmoid(t, midpoint, steepness)",
         "Rogers Adoption Curve; Standard bei Therapie-Penetration", "MODELL"),
        ("Marktanteils-Ramp (S-Kurve)",
         "Share(t) = Start + (Peak - Start) * sigmoid(t, midpoint, steepness)",
         "Logistic Share Shift; Standard bei Brand-Launch-Forecasts", "MODELL"),
        ("Therapietreue (Persistence)",
         "avg_persistence = (1 + persistence_12m) / 2; Steady-State-Durchschnitt",
         "Vereinfachtes Modell; Kalibriert auf 12-Monats-Persistenzrate", "MODELL"),
        ("Supply Constraint",
         "min(Demand, Capacity) bis Normalisierungsmonat",
         "Historisch validierbar durch Ozempic-Engpass 2022-2025", "MODELL"),
        ("Preiserosion",
         "Price(t) = Base * (1 + annual_trend)^(t/12) * (1 - AMNOG_cut); Floor EUR 100",
         "AMNOG Erstattungsbetrag-Mechanik; jaehrliche Preisentwicklung", "MODELL"),
        ("Share-Normalisierung",
         "Wenn my_share + comp_share > 90%: proportionale Skalierung",
         "Garantiert Rest-of-Market >= 10% (Trulicity, Rybelsus etc.)", "MODELL"),
    ]
    for name, formula, ref, cat in models:
        row += 1
        ws6.set_row(row, 40)
        ws6.write(row, 1, name, fmt["label_bold"])
        ws6.write(row, 2, formula, fmt["model"])
        ws6.write(row, 3, ref, fmt["label"])
        ws6.write(row, 4, cat, fmt["model"])

    # Facts
    row += 2
    ws6.merge_range(row, 1, row, 4, "FAKTEN (aus oeffentlichen Quellen)", fmt["section"])
    row += 1
    for c, h in enumerate(["Datenpunkt", "Wert im Modell", "Quelle", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    facts = [
        ("T2D-Patienten Deutschland", "6.33M GKV-Versicherte", "BARMER Gesundheitswesen aktuell 2025", "FAKT"),
        ("GLP-1-Penetration T2D (2024)", "13.9%", "BARMER GLP-1-Versorgungsanalyse 2025", "FAKT"),
        ("Adipositas-Patienten Deutschland", "8M (BMI >= 30)", "RKI Gesundheitsmonitoring", "FAKT"),
        ("Mounjaro EU-Zulassung T2D", "Sep 2022", "EMA EPAR Mounjaro", "FAKT"),
        ("Mounjaro EU-Zulassung Adipositas", "Dez 2023", "EMA EPAR Mounjaro", "FAKT"),
        ("Wegovy GKV-Ausschluss", "G-BA Juni 2024", "G-BA Beschluss: Lifestyle-Arzneimittel", "FAKT"),
        ("Tirzepatid Wirksamkeit", "-2.4% HbA1c, -22.5% Gewicht", "SURPASS / SURMOUNT", "FAKT"),
        ("Semaglutid Wirksamkeit", "-1.8% HbA1c, -15% Gewicht", "SUSTAIN / STEP", "FAKT"),
        ("Ozempic Lieferengpass", "Seit 2022, weltweit", "BfArM Lieferengpass-DB", "FAKT"),
    ]
    for dp, val, source, cat in facts:
        row += 1
        ws6.write(row, 1, dp, fmt["label_bold"])
        ws6.write(row, 2, val, fmt["fact"])
        ws6.write(row, 3, source, fmt["label"])
        ws6.write(row, 4, cat, fmt["fact"])

    # Assumptions
    row += 2
    ws6.merge_range(row, 1, row, 4, "ANNAHMEN (User-steuerbar pro Indikation)", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Default-Wert", "Begruendung", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    assumptions = [
        ("T2D Behandlungsrate Ziel", "22%", "Leitlinien-Shift treibt Penetration nach oben", "ANNAHME"),
        ("T2D Marktanteil Peak (Lilly)", "25%", "Abhaengig von KOL-Ueberzeugung, Leitlinien", "ANNAHME"),
        ("T2D Therapietreue 12M", "70%", "Chronische Therapie, gute Adhaerenz", "ANNAHME"),
        ("Adipositas Behandlungsrate", "1.5% (ohne GKV)", "Nur Selbstzahler; mit GKV: 5%", "ANNAHME"),
        ("Adipositas Therapietreue 12M", "45%", "Niedrigere Adhaerenz als T2D", "ANNAHME"),
        ("Preis Mounjaro T2D", "EUR 350/Mon.", "~EUR 206-490/Mon., Durchschn. ~EUR 350", "ANNAHME"),
        ("Preis Ozempic T2D", "EUR 300/Mon.", "~EUR 300/Mon. (1mg Erhaltungsdosis)", "ANNAHME"),
        ("Preistrend p.a.", "-3%", "Erfahrungswert bei etablierten Biologika", "ANNAHME"),
        ("COGS", "20%", "Peptid-Biologika: 15-25% typisch", "ANNAHME"),
    ]
    for param, val, reason, cat in assumptions:
        row += 1
        ws6.write(row, 1, param, fmt["label_bold"])
        ws6.write(row, 2, val, fmt["assumption"])
        ws6.write(row, 3, reason, fmt["label"])
        ws6.write(row, 4, cat, fmt["assumption"])

    # Gaps
    row += 2
    ws6.merge_range(row, 1, row, 4, "LUECKEN (fuer Produktiveinsatz benoetigt)", fmt["section"])
    row += 1
    for c, h in enumerate(["Gap", "Beschreibung", "Datenquelle", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    gaps = [
        ("Echte IQVIA-Daten", "TRx, NRx auf Monatsebene pro GLP-1-Produkt", "IQVIA Midas / DPM", "LUECKE"),
        ("Reale Persistenzdaten", "Therapietreue pro Indikation und Produkt", "GKV-Routinedaten / IQVIA", "LUECKE"),
        ("Mounjaro vertraulicher Preis", "Tatsaechlicher GKV-Erstattungsbetrag", "Lilly intern / GKV-SV", "LUECKE"),
        ("Regionale Verschreibungsdaten", "KV-Regionen: GLP-1-Adoption", "IQVIA Regional / KBV", "LUECKE"),
        ("Pipeline-Timing", "FDA/EMA fuer CV/MASH-Indikationen", "ClinicalTrials.gov", "LUECKE"),
        ("Patienten-Switching", "Umstellungsraten zwischen Produkten", "Real World Evidence", "LUECKE"),
    ]
    for name, desc, source, cat in gaps:
        row += 1
        ws6.write(row, 1, name, fmt["label_bold"])
        ws6.write(row, 2, desc, fmt["gap"])
        ws6.write(row, 3, source, fmt["label"])
        ws6.write(row, 4, cat, fmt["gap"])

    # Key difference vs Eliquis model
    row += 3
    ws6.merge_range(row, 1, row, 4, "Strukturelle Unterschiede vs. Generic-Entry-Modell (Eliquis)", fmt["section"])
    row += 1
    for c, h in enumerate(["Dimension", "Generic Entry (Eliquis)", "Brand Competition (GLP-1)"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    comparisons = [
        ("Modelltyp", "TRx-basiert (Markt x Share)", "Patientenbasiert (pro Indikation)"),
        ("Marktdynamik", "Markt stagniert/schrumpft", "Markt expandiert (Indikationen)"),
        ("Wettbewerber", "Multiple Generika vs. 1 Originator", "2 Branded Originatoren"),
        ("Preis-Mechanik", "Festbetrag / Generika-Erosion", "AMNOG Erstattungsbetrag"),
        ("Substitution", "Aut-idem (Apotheke)", "Keine; Arzt entscheidet"),
        ("Indikationen", "Single Indication", "Multi-Indication (T2D, Adipo, CV, MASH)"),
        ("Therapietreue", "Nicht modelliert", "Persistenz pro Indikation (Steady-State)"),
        ("Supply", "Normalerweise kein Engpass", "Reale Supply Constraints"),
    ]
    for dim, eliquis, glp1 in comparisons:
        row += 1
        ws6.write(row, 1, dim, fmt["label_bold"])
        ws6.write(row, 2, eliquis, fmt["label"])
        ws6.write(row, 3, glp1, fmt["label"])

    # Disclaimer
    row += 3
    ws6.merge_range(row, 1, row, 4,
        "Hinweis: Alle Daten sind synthetisch und dienen der Illustration. "
        "Angelehnt an oeffentlich verfuegbare Quellen: BARMER 2025, G-BA, IQVIA, EMA. "
        "Kein Bezug zu vertraulichen Daten.",
        fmt["hint"])

    wb.close()
    print(f"Excel model saved to: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    build_model()
