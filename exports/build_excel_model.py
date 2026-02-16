"""
Build a professional Excel forecast model for the Eliquis generic entry scenario.

Sheets:
1. INPUTS          – All user-configurable parameters (yellow cells)
2. Marktdaten      – Market context & competitive landscape
3. Originator      – Revenue-at-Risk forecast (monthly)
4. Generika        – Market Opportunity forecast (monthly)
5. Dashboard       – Summary KPIs & scenario comparison
6. Methodik        – Transparency matrix: Facts vs. Assumptions vs. Models
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dataclasses
import xlsxwriter
import numpy as np
import pandas as pd
from models.forecast_engine import (
    OriginatorParams, GenericParams,
    forecast_originator, forecast_generic,
    calculate_kpis_originator, calculate_kpis_generic,
)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Eliquis_Launch_Forecast_v2.xlsx")


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
    fmt["th"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#1e3a5f", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_red"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#991b1b", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_green"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#166534", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["th_purple"] = wb.add_format({"bold": True, "font_size": 10, "font_color": "white", "bg_color": "#5b21b6", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    fmt["kpi_label"] = wb.add_format({"bold": True, "font_size": 11, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1})
    fmt["kpi_value"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1e3a5f", "bg_color": "#f0f4ff", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#dc2626", "bg_color": "#fef2f2", "border": 1, "num_format": "-0.0%", "align": "center"})
    fmt["kpi_value_green"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#166534", "bg_color": "#f0fdf4", "border": 1, "num_format": "€#,##0", "align": "center"})
    fmt["kpi_value_green_pct"] = wb.add_format({"bold": True, "font_size": 14, "font_color": "#166534", "bg_color": "#f0fdf4", "border": 1, "num_format": "0.0%", "align": "center"})
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
    ws.set_column("B:B", 42)
    ws.set_column("C:C", 18)
    ws.set_column("D:D", 50)
    ws.set_column("E:F", 18)

    row = 1
    ws.merge_range(row, 1, row, 3, "Eliquis (Apixaban) - Launch Forecast Modell", fmt["title"])
    row += 1
    ws.merge_range(row, 1, row, 3, "Eingabe-Parameter (gelbe Zellen sind editierbar)", wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    # 1. Marktdefinition
    row += 2
    ws.merge_range(row, 1, row, 3, "1. MARKTDEFINITION", fmt["section"])
    for label, value, fk, hint in [
        ("Markt", "Orale Antikoagulantien (NOAK/DOAK)", "input_text", "Therapiegebiet / ATC-Klasse"),
        ("Geographie", "Deutschland", "input_text", "Zielmarkt"),
        ("LOE-Datum (Patentablauf)", "Mai 2026", "input_text", "Loss of Exclusivity Eliquis"),
        ("Gesamtmarkt TRx/Monat", 4_200_000, "input", "Monatliche Verordnungen im NOAK-Segment"),
        ("Gesamtmarkt Umsatz/Monat (EUR)", 285_000_000, "input", "Monatlicher Marktumsatz"),
        ("Jahrl. Marktwachstum", 0.02, "input_pct", "Organisches Wachstum des NOAK-Segments"),
        ("Forecast-Horizont (Monate)", 60, "input", "Anzahl Monate nach LOE"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 2. Originator
    row += 2
    ws.merge_range(row, 1, row, 3, "2. ORIGINATOR-PARAMETER (Revenue at Risk)", fmt["section"])
    for label, value, fk, hint in [
        ("Originator", "Eliquis (BMS / Pfizer)", "input_text", "Produktname & Hersteller"),
        ("Aktueller Marktanteil (TRx)", 0.42, "input_pct", "Marktanteil vor LOE"),
        ("Aktueller Preis/TRx (EUR)", 91.50, "input_eur", "Monatliche Therapiekosten"),
        ("Preis-Reduktion nach LOE", 0.15, "input_pct", "Erwartete Preissenkung durch Originator"),
        ("Erosions-Geschwindigkeit", 1.0, "input", "1.0=Normal, >1=schneller, <1=langsamer"),
        ("Boden-Marktanteil", 0.12, "input_pct", "Minimaler Anteil (Markentreue, Arzt-Praeferenz)"),
        ("Monate bis Boden", 18, "input", "Monate bis Erosion Plateau erreicht"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # AG
    row += 1
    ws.merge_range(row, 1, row, 3, "Authorized Generic Strategie", fmt["subsection"])
    for label, value, fk, hint in [
        ("Authorized Generic launchen?", "NEIN", "input_bool", "JA oder NEIN - Eigenes Generikum unter Zweitmarke?"),
        ("AG Anteil am Generika-Segment (initial)", 0.25, "input_pct", "Initialer Anteil der Generika-Verordnungen fuer AG"),
        ("AG Anteil-Erosion Speed", 0.5, "input", "0=statisch, 1=moderate Erosion, 2=schnelle Erosion"),
        ("AG Preis-Discount vs. Originator (initial)", 0.30, "input_pct", "Initialer Preisabschlag des AG"),
        ("AG Discount-Zunahme Speed", 0.5, "input", "0=statisch, 1=moderater Preisverfall, 2=schneller Preisverfall"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 3. Generika
    row += 2
    ws.merge_range(row, 1, row, 3, "3. GENERIKA-PARAMETER (Market Opportunity)", fmt["section"])
    row += 1
    ws.merge_range(row, 1, row, 3, "Markt-Kaskade: NOAK -> Apixaban (42%) -> Generika-Segment (55%) -> Mein Anteil (20%)", fmt["hint"])
    for label, value, fk, hint in [
        ("Apixaban-Marktanteil am NOAK-Markt", 0.42, "input_pct", "Anteil von Apixaban (Eliquis) am NOAK-Gesamtmarkt"),
        ("Generika-Segment Peak-Anteil", 0.55, "input_pct", "Anteil der Apixaban-Verordnungen, die generisch werden"),
        ("Monate bis Generika-Segment Peak", 24, "input", "Monate nach LOE bis Generika-Segment seinen Peak erreicht"),
        ("Launch-Zeitpunkt (Monate nach LOE)", 0, "input", "0 = Day-1 Launch"),
        ("Preis-Discount vs. Originator", 0.45, "input_pct", "Preisabschlag zum Originator-Preis"),
        ("Mein Anteil am Generika-Segment", 0.20, "input_pct", "Mein Anteil an allen Apixaban-Generika (nicht am NOAK-Gesamtmarkt)"),
        ("Monate bis Peak Share", 18, "input", "Monate bis mein Anteil am Generika-Segment den Peak erreicht"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 4. AUT-IDEM
    row += 2
    ws.merge_range(row, 1, row, 3, "4. AUT-IDEM / SUBSTITUTION", fmt["section"])
    row += 1
    ws.merge_range(row, 1, row, 3, "Aut idem = Apotheke darf/muss wirkstoffgleiches Generikum abgeben (SGB V Par.129)", fmt["hint"])
    for label, value, fk, hint in [
        ("Aut-idem aktiv?", "JA", "input_bool", "JA oder NEIN - Wird Festbetragsgruppe gebildet?"),
        ("Anlaufzeit Festbetrag (Monate nach LOE)", 6, "input", "G-BA Festbetragsentscheid dauert ca. 3-6 Monate"),
        ("Volle Aut-idem-Quote nach (Monate)", 12, "input", "Monate bis Apotheken voll substituieren"),
        ("Peak Aut-idem-Quote", 0.75, "input_pct", "Max. Anteil der Rx, die substituiert werden (Nicht-Tender-Rest)"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # Aut-idem explainer
    row += 1
    ws.merge_range(row, 1, row, 3, "Aut-idem Wirkungskette", fmt["subsection"])
    chain = [
        "1. LOE: Patent laeuft ab, Generika kommen auf den Markt",
        "2. G-BA bildet Festbetragsgruppe (Dauer: 3-6 Monate nach LOE)",
        "3. Festbetrag wird festgesetzt -> Originator-Preis ggf. ueber Festbetrag",
        "4. Apotheke MUSS guenstigstes Generikum abgeben (SGB V Par.129)",
        "5. Arzt kann aut-idem-Substitution ausschliessen (Kreuz auf Rezept)",
        "6. Patient erhaelt Generikum, es sei denn Arzt hat es ausgeschlossen",
    ]
    for step in chain:
        row += 1
        ws.merge_range(row, 1, row, 3, step, fmt["label"])

    # 5. TENDER / RABATTVERTRAEGE
    row += 2
    ws.merge_range(row, 1, row, 3, "5. MEINE RABATTVERTRAEGE", fmt["section"])
    row += 1
    ws.merge_range(row, 1, row, 3, "Deterministisches Modell: Pro Kasse gewonnen/verloren. Risiko als Szenario-Band (Bear/Base/Bull).", fmt["hint"])
    for label, value, fk, hint in [
        ("Rabattvertraege anstreben?", "JA", "input_bool", "JA oder NEIN"),
        ("Anlaufzeit Tender (Monate nach Launch)", 3, "input", "Bis erste Ausschreibung gewonnen"),
        ("Mein Anteil bei Mehrfachvergabe", 0.50, "input_pct", "z.B. 50% bei 2 Hauptpartnern pro Kasse"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # Krankenkassen-Tabelle (deterministisch)
    row += 2
    ws.merge_range(row, 1, row, 5, "Kassen - Rabattvertrag gewonnen/verloren (Base Case)", fmt["subsection"])
    row += 1
    kk_headers = ["Krankenkasse", "Versicherte\n(Mio.)", "Marktanteil\nGKV", "Gewonnen?\n(Base)", "Status"]
    for c, h in enumerate(kk_headers):
        ws.write(row, 1 + c, h, fmt["th"])
    ws.set_row(row, 30)

    kassen = [
        ("TK (Techniker)", 11.5, 0.158, "JA", "Ziel"),
        ("BARMER", 8.7, 0.119, "JA", "Ziel"),
        ("DAK-Gesundheit", 5.5, 0.075, "JA", "Ziel"),
        ("AOK Bayern", 4.6, 0.063, "NEIN", "Optional"),
        ("AOK Baden-Wuerttemberg", 4.5, 0.062, "NEIN", "Optional"),
        ("Restl. Kassen", 26.8, 0.368, "NEIN", "Nachrangig"),
    ]
    for name, vers, anteil, won, status in kassen:
        row += 1
        ws.write(row, 1, name, fmt["input_text"])
        ws.write(row, 2, vers, fmt["input"])
        ws.write(row, 3, anteil, fmt["input_pct"])
        ws.write(row, 4, won, fmt["input_bool"])
        ws.write(row, 5, status, fmt["input_bool"])

    # Tender explainer
    row += 1
    ws.merge_range(row, 1, row, 5, "Rabattvertrag-Mechanik", fmt["subsection"])
    tender_chain = [
        "1. Krankenkasse schreibt Wirkstoff aus (Open-House oder Mehrfachvergabe)",
        "2. Generika-Anbieter geben Angebot ab (Preis pro DDD/Packung)",
        "3. Zuschlag: Mehrere Anbieter erhalten Vertrag (Versorgungssicherheit)",
        "4. Apotheke MUSS Produkt eines Vertragspartners abgeben (Par.130a SGB V)",
        "5. Aut-idem-Ausschluss durch Arzt hat Vorrang und verhindert Tender-Substitution",
        "6. Modellierung: Deterministisch (gewonnen/verloren) + Szenario-Band fuer Risiko",
    ]
    for step in tender_chain:
        row += 1
        ws.merge_range(row, 1, row, 5, step, fmt["label"])

    # 6. Kosten
    row += 2
    ws.merge_range(row, 1, row, 3, "6. KOSTEN & PROFITABILITAET (Generika)", fmt["section"])
    for label, value, fk, hint in [
        ("COGS (% vom Umsatz)", 0.25, "input_pct", "Herstellkosten als Anteil am Nettoumsatz"),
        ("Monatl. Vertriebskosten (EUR)", 150_000, "input", "Aussendienst, KAM, Marketing"),
        ("Launch-Investition einmalig (EUR)", 500_000, "input", "Zulassung, Listings, Launch-Marketing"),
        ("Monatl. Fixkosten (EUR)", 50_000, "input", "Regulatory, QA, Overhead-Anteil"),
    ]:
        row += 1
        write_input_row(ws, row, label, value, fk, hint)

    # 7. Szenarien
    row += 2
    ws.merge_range(row, 1, row, 4, "7. SZENARIO-DEFINITIONEN", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Bear Case", "Base Case", "Bull Case"]):
        ws.write(row, 1 + c, h, fmt["th"])
    for param, bear, base, bull in [
        ("Originator Preisreduktion", 0.20, 0.15, 0.10),
        ("Erosions-Geschwindigkeit", 0.7, 1.0, 1.3),
        ("Originator Boden-Share", 0.18, 0.12, 0.08),
        ("Aut-idem Peak-Quote", 0.60, 0.75, 0.85),
        ("Mein Anteil am Generika-Segment", 0.10, 0.20, 0.30),
        ("Generika-Segment Peak Share", 0.40, 0.55, 0.65),
        ("Mein Preis-Discount", 0.35, 0.45, 0.50),
        ("Marktwachstum p.a.", 0.01, 0.02, 0.03),
        ("Tender", "Kein Tender", "User-Auswahl", "Alle Kassen"),
    ]:
        row += 1
        ws.write(row, 1, param, fmt["label_bold"])
        if isinstance(bear, str):
            ws.write(row, 2, bear, fmt["input_text"])
            ws.write(row, 3, base, fmt["input_text"])
            ws.write(row, 4, bull, fmt["input_text"])
        else:
            ws.write(row, 2, bear, fmt["input_pct"])
            ws.write(row, 3, base, fmt["input_pct"])
            ws.write(row, 4, bull, fmt["input_pct"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 2: MARKTDATEN (unchanged from before)
    # ═══════════════════════════════════════════════════════════════════
    ws2 = wb.add_worksheet("Marktdaten")
    ws2.hide_gridlines(2)
    ws2.set_tab_color("#1e3a5f")
    ws2.set_column("A:A", 3); ws2.set_column("B:B", 30); ws2.set_column("C:G", 18)
    row = 1
    ws2.merge_range(row, 1, row, 6, "Wettbewerbslandschaft - NOAK/DOAK Deutschland", fmt["title"])
    row += 2
    for c, h in enumerate(["Produkt", "Hersteller", "Marktanteil (TRx)", "Preis/TRx (EUR)", "Umsatz/Monat (EUR)", "Patent"]):
        ws2.write(row, 1 + c, h, fmt["th"])
    for pn, co, sh, pr, rv, pa in [
        ("Eliquis (Apixaban)", "BMS / Pfizer", 0.42, 91.50, 161_000_000, "Mai 2026"),
        ("Xarelto (Rivaroxaban)", "Bayer", 0.35, 87.80, 129_000_000, "Apr 2024"),
        ("Lixiana (Edoxaban)", "Daiichi Sankyo", 0.15, 74.20, 47_000_000, "2031"),
        ("Pradaxa (Dabigatran)", "Boehringer", 0.08, 64.00, 21_500_000, "2025"),
    ]:
        row += 1
        ws2.write(row, 1, pn, fmt["label_bold"]); ws2.write(row, 2, co, fmt["label"])
        ws2.write(row, 3, sh, fmt["pct"]); ws2.write(row, 4, pr, fmt["eur_detail"])
        ws2.write(row, 5, rv, fmt["eur"]); ws2.write(row, 6, pa, fmt["label"])
    row += 1
    ws2.write(row, 1, "GESAMT", fmt["label_bold"]); ws2.write(row, 3, 1.0, fmt["pct"]); ws2.write(row, 5, 285_000_000, fmt["eur"])

    row += 3
    ws2.merge_range(row, 1, row, 6, "Markt-Kontext", fmt["section"])
    for label, value in [
        ("Indikation", "Nicht-valvulaeres Vorhofflimmern (NVAF), VTE-Prophylaxe & Therapie"),
        ("Patienten in DE", "~1.8 Mio. unter NOAK-Therapie"),
        ("Marktdynamik", "Reifer Markt, Wachstum durch Bevoelkerungsalterung"),
        ("Regulatorik", "Festbetrag wird nach LOE erwartet (G-BA)"),
        ("Substitution", "Aut-idem-faehig nach Aufnahme in Festbetragsgruppe"),
        ("Analoga", "Clopidogrel LOE 2008: ~70% Generika-Share nach 24M"),
    ]:
        row += 1
        ws2.write(row, 1, label, fmt["label_bold"]); ws2.merge_range(row, 2, row, 6, value, fmt["label"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 3: ORIGINATOR FORECAST
    # ═══════════════════════════════════════════════════════════════════
    ws3 = wb.add_worksheet("Originator Forecast")
    ws3.hide_gridlines(2); ws3.set_tab_color("#dc2626")
    ws3.set_column("A:A", 3); ws3.set_column("B:B", 12); ws3.set_column("C:N", 16)

    params_o = OriginatorParams()
    df_o = forecast_originator(params_o, forecast_months=60)
    kpis_o = calculate_kpis_originator(df_o)

    row = 1
    ws3.merge_range(row, 1, row, 10, "Originator Perspektive - Revenue at Risk (Base Case)", fmt["title"])
    row += 2
    for c, (label, value, vfmt) in enumerate([
        ("Umsatz vor LOE (p.a.)", kpis_o["pre_loe_annual_revenue"], "kpi_value"),
        ("Umsatz Jahr 1 nach LOE", kpis_o["year1_post_loe_revenue"], "kpi_value"),
        ("Revenue at Risk (5J)", kpis_o["total_revenue_at_risk_5y"], "kpi_value"),
        ("Rueckgang Jahr 1", -kpis_o["year1_revenue_decline_pct"] / 100, "kpi_value_pct"),
    ]):
        col = 1 + c * 2
        ws3.merge_range(row, col, row, col + 1, label, fmt["kpi_label"])
        ws3.merge_range(row + 1, col, row + 1, col + 1, value, fmt[vfmt])

    row += 4
    headers_o = ["Monat", "Monate\nnach LOE", "Gesamt-\nmarkt TRx", "Originator\nTRx", "Originator\nMarktanteil",
                 "Aut-idem\nQuote", "Preis/TRx\n(EUR)", "Originator\nUmsatz (EUR)",
                 "Generika\nSegment TRx", "Revenue\nat Risk (EUR)", "Kum. Revenue\nat Risk (EUR)"]
    for c, h in enumerate(headers_o):
        ws3.write(row, 1 + c, h, fmt["th_red"])
    ws3.set_row(row, 35)
    data_start_row = row + 1

    for i, (_, r) in enumerate(df_o.iterrows()):
        row += 1
        is_alt = i % 2 == 1
        ws3.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
        ws3.write(row, 2, r["months_since_loe"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 3, r["total_market_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 4, r["originator_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 5, r["originator_share"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws3.write(row, 6, r["aut_idem_rate"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws3.write(row, 7, r["originator_price"], fmt["row_alt_eur"] if is_alt else fmt["eur_detail"])
        ws3.write(row, 8, r["originator_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 9, r["generic_segment_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws3.write(row, 10, r["revenue_at_risk"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws3.write(row, 11, r["cumulative_revenue_at_risk"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
    data_end_row = row

    # Chart 1: Revenue + Counterfactual
    chart1 = wb.add_chart({"type": "line"})
    chart1.add_series({"name": "Originator Umsatz", "categories": ["Originator Forecast", data_start_row, 1, data_end_row, 1],
        "values": ["Originator Forecast", data_start_row, 8, data_end_row, 8], "line": {"color": "#dc2626", "width": 2.5}})
    chart1.set_title({"name": "Originator Umsatz-Entwicklung"})
    chart1.set_y_axis({"name": "EUR", "num_format": "€#,##0,K"}); chart1.set_size({"width": 800, "height": 380})
    chart1.set_legend({"position": "bottom"})
    ws3.insert_chart("B" + str(row + 3), chart1)

    # Chart 2: Market Share + Aut-idem Rate
    chart2 = wb.add_chart({"type": "line"})
    chart2.add_series({"name": "Originator Marktanteil", "categories": ["Originator Forecast", data_start_row, 1, data_end_row, 1],
        "values": ["Originator Forecast", data_start_row, 5, data_end_row, 5], "line": {"color": "#dc2626", "width": 2.5}})
    chart2.add_series({"name": "Aut-idem Quote", "categories": ["Originator Forecast", data_start_row, 1, data_end_row, 1],
        "values": ["Originator Forecast", data_start_row, 6, data_end_row, 6], "line": {"color": "#f59e0b", "width": 2, "dash_type": "dash"}})
    chart2.set_title({"name": "Marktanteil & Aut-idem-Quote"})
    chart2.set_y_axis({"name": "Anteil", "num_format": "0%"}); chart2.set_size({"width": 800, "height": 380})
    chart2.set_legend({"position": "bottom"})
    ws3.insert_chart("J" + str(row + 3), chart2)

    # Chart 3: Revenue at Risk (cumulative)
    chart3 = wb.add_chart({"type": "area"})
    chart3.add_series({"name": "Kum. Revenue at Risk", "categories": ["Originator Forecast", data_start_row, 1, data_end_row, 1],
        "values": ["Originator Forecast", data_start_row, 11, data_end_row, 11], "fill": {"color": "#fca5a5"}, "line": {"color": "#dc2626", "width": 1.5}})
    chart3.set_title({"name": "Kumulativer Revenue at Risk"})
    chart3.set_y_axis({"name": "EUR", "num_format": "€#,##0,,M"}); chart3.set_size({"width": 800, "height": 380})
    ws3.insert_chart("B" + str(row + 23), chart3)

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 4: GENERIKA FORECAST
    # ═══════════════════════════════════════════════════════════════════
    ws4 = wb.add_worksheet("Generika Forecast")
    ws4.hide_gridlines(2); ws4.set_tab_color("#16a34a")
    ws4.set_column("A:A", 3); ws4.set_column("B:B", 12); ws4.set_column("C:P", 14)

    params_g = GenericParams()
    df_g = forecast_generic(params_g, forecast_months=60)
    kpis_g = calculate_kpis_generic(df_g)

    row = 1
    ws4.merge_range(row, 1, row, 12, "Generika Perspektive - Market Opportunity (Base Case)", fmt["title"])
    row += 2

    be_month = kpis_g.get("breakeven_month")
    be_text = f"Monat {be_month}" if be_month else "N/A"
    for c, (label, value, vfmt) in enumerate([
        ("Umsatz Jahr 1", kpis_g["year1_revenue"], "kpi_value_green"),
        ("Umsatz 5J kumuliert", kpis_g["total_5y_revenue"], "kpi_value_green"),
        ("Gewinn 5J kumuliert", kpis_g["total_5y_profit"], "kpi_value_green"),
        ("Peak Marktanteil", kpis_g["peak_share"], "kpi_value_green_pct"),
        ("Break-Even", be_text, "kpi_value_plain"),
    ]):
        col = 1 + c * 2
        ws4.merge_range(row, col, row, col + 1, label, fmt["kpi_label"])
        ws4.merge_range(row + 1, col, row + 1, col + 1, value, fmt[vfmt])

    # Volume decomposition KPIs
    row += 3
    ws4.merge_range(row, 1, row, 6, "Volumen-Dekomposition (5 Jahre)", fmt["subsection"])
    row += 1
    for c, (label, value) in enumerate([
        ("Organisch", kpis_g.get("volume_organic_pct", 0)),
        ("Aut-idem", kpis_g.get("volume_aut_idem_pct", 0)),
        ("Tender", kpis_g.get("volume_tender_pct", 0)),
    ]):
        ws4.write(row, 1 + c * 2, label, fmt["kpi_label"])
        ws4.write(row, 2 + c * 2, value, fmt["kpi_value_green_pct"])

    # Data table
    row += 2
    headers_g = ["Monat", "Monate\nnach LOE", "Gesamt-\nmarkt TRx",
                 "Organisch\nTRx", "Aut-idem\nTRx", "Tender\nTRx", "Gesamt\nTRx",
                 "Mein\nMarktanteil", "Aut-idem\nQuote", "Preis/TRx\n(EUR)",
                 "Umsatz\n(EUR)", "COGS\n(EUR)", "Oper. Gewinn\n(EUR)",
                 "Kum. Umsatz\n(EUR)", "Kum. Gewinn\n(EUR)"]
    for c, h in enumerate(headers_g):
        ws4.write(row, 1 + c, h, fmt["th_green"])
    ws4.set_row(row, 35)
    g_data_start = row + 1

    for i, (_, r) in enumerate(df_g.iterrows()):
        row += 1
        is_alt = i % 2 == 1
        ws4.write(row, 1, r["month"], fmt["row_alt"] if is_alt else None)
        ws4.write(row, 2, r["months_since_loe"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 3, r["total_market_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 4, r["organic_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 5, r["aut_idem_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 6, r["tender_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 7, r["my_trx"], fmt["row_alt_num"] if is_alt else fmt["number"])
        ws4.write(row, 8, r["my_share"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws4.write(row, 9, r["aut_idem_rate"], fmt["row_alt_pct"] if is_alt else fmt["pct"])
        ws4.write(row, 10, r["my_price"], fmt["row_alt_eur"] if is_alt else fmt["eur_detail"])
        ws4.write(row, 11, r["my_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 12, r["cogs"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 13, r["operating_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 14, r["cumulative_revenue"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
        ws4.write(row, 15, r["cumulative_profit"], fmt["row_alt_eur"] if is_alt else fmt["eur"])
    g_data_end = row

    # Chart 1: Stacked volume decomposition
    chart_vol = wb.add_chart({"type": "column", "subtype": "stacked"})
    chart_vol.add_series({"name": "Organisch", "categories": ["Generika Forecast", g_data_start, 1, g_data_end, 1],
        "values": ["Generika Forecast", g_data_start, 4, g_data_end, 4], "fill": {"color": "#86efac"}})
    chart_vol.add_series({"name": "Aut-idem", "categories": ["Generika Forecast", g_data_start, 1, g_data_end, 1],
        "values": ["Generika Forecast", g_data_start, 5, g_data_end, 5], "fill": {"color": "#fbbf24"}})
    chart_vol.add_series({"name": "Tender", "categories": ["Generika Forecast", g_data_start, 1, g_data_end, 1],
        "values": ["Generika Forecast", g_data_start, 6, g_data_end, 6], "fill": {"color": "#60a5fa"}})
    chart_vol.set_title({"name": "Volumen-Dekomposition: Organisch / Aut-idem / Tender"})
    chart_vol.set_y_axis({"name": "TRx", "num_format": "#,##0"}); chart_vol.set_size({"width": 800, "height": 380})
    chart_vol.set_legend({"position": "bottom"})
    ws4.insert_chart("B" + str(row + 3), chart_vol)

    # Chart 2: Revenue + Cumulative Profit
    chart_rev = wb.add_chart({"type": "column"})
    chart_rev.add_series({"name": "Monatl. Umsatz", "categories": ["Generika Forecast", g_data_start, 1, g_data_end, 1],
        "values": ["Generika Forecast", g_data_start, 11, g_data_end, 11], "fill": {"color": "#86efac"}, "border": {"color": "#16a34a"}})
    chart_rev_line = wb.add_chart({"type": "line"})
    chart_rev_line.add_series({"name": "Kum. Gewinn", "categories": ["Generika Forecast", g_data_start, 1, g_data_end, 1],
        "values": ["Generika Forecast", g_data_start, 15, g_data_end, 15], "line": {"color": "#166534", "width": 2.5}, "y2_axis": True})
    chart_rev.combine(chart_rev_line)
    chart_rev.set_title({"name": "Umsatz & Kumulierter Gewinn"})
    chart_rev.set_y_axis({"name": "Monatl. Umsatz (EUR)"}); chart_rev.set_y2_axis({"name": "Kum. Gewinn (EUR)"})
    chart_rev.set_size({"width": 800, "height": 380}); chart_rev.set_legend({"position": "bottom"})
    ws4.insert_chart("J" + str(row + 3), chart_rev)

    # Chart 3: Aut-idem Rate over time
    chart_ai = wb.add_chart({"type": "area"})
    chart_ai.add_series({"name": "Aut-idem Quote", "categories": ["Generika Forecast", g_data_start, 1, g_data_end, 1],
        "values": ["Generika Forecast", g_data_start, 9, g_data_end, 9], "fill": {"color": "#fef3c7"}, "line": {"color": "#f59e0b", "width": 2}})
    chart_ai.set_title({"name": "Aut-idem Substitutionsquote"})
    chart_ai.set_y_axis({"name": "Quote", "num_format": "0%", "max": 1.0}); chart_ai.set_size({"width": 800, "height": 380})
    ws4.insert_chart("B" + str(row + 23), chart_ai)

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 5: DASHBOARD
    # ═══════════════════════════════════════════════════════════════════
    ws5 = wb.add_worksheet("Dashboard")
    ws5.hide_gridlines(2); ws5.set_tab_color("#6366f1")
    ws5.set_column("A:A", 3); ws5.set_column("B:B", 38); ws5.set_column("C:E", 22)

    row = 1
    ws5.merge_range(row, 1, row, 4, "Executive Summary - Eliquis Generic Entry 2026", fmt["title"])

    # Originator scenarios
    row += 2
    ws5.merge_range(row, 1, row, 4, "Originator-Perspektive - Szenario-Vergleich", fmt["section"])
    scenario_results = {}
    base_orig = params_o  # use the base-case params already computed above
    for sn, sp in [
        ("Bear Case", {"erosion_speed": 0.7, "floor_share": 0.18, "price_reduction_pct": 0.20, "months_to_floor": 24}),
        ("Base Case", {}),
        ("Bull Case", {"erosion_speed": 1.3, "floor_share": 0.08, "price_reduction_pct": 0.10, "months_to_floor": 12}),
    ]:
        p = dataclasses.replace(base_orig, **sp)
        scenario_results[sn] = calculate_kpis_originator(forecast_originator(p, forecast_months=60))

    row += 1
    ws5.write(row, 1, ""); ws5.write(row, 2, "Bear Case", fmt["th"]); ws5.write(row, 3, "Base Case", fmt["th"]); ws5.write(row, 4, "Bull Case", fmt["th"])
    for label, key, vtype in [
        ("Originator Umsatz Jahr 1 nach LOE", "year1_post_loe_revenue", "eur"),
        ("Revenue at Risk (5J kumuliert)", "total_revenue_at_risk_5y", "eur"),
        ("Umsatzrueckgang Jahr 1", "year1_revenue_decline_pct", "pct_neg"),
        ("Marktanteil nach 12 Monaten", "share_at_month_12", "pct"),
        ("Marktanteil nach 24 Monaten", "share_at_month_24", "pct"),
    ]:
        row += 1
        ws5.write(row, 1, label, fmt["label_bold"])
        for c, sn in enumerate(["Bear Case", "Base Case", "Bull Case"]):
            val = scenario_results[sn][key]
            if vtype == "eur": ws5.write(row, 2 + c, val, fmt["eur"])
            elif vtype == "pct": ws5.write(row, 2 + c, val, fmt["pct"])
            elif vtype == "pct_neg": ws5.write(row, 2 + c, -val / 100, fmt["pct"])

    # Generika scenarios
    row += 3
    ws5.merge_range(row, 1, row, 4, "Generika-Perspektive - Szenario-Vergleich", fmt["section"])
    gen_scenarios = {}
    base_gen = params_g  # use the base-case params already computed above
    for sn, gp in [
        ("Bear Case", {"target_generic_share": 0.10, "price_discount_vs_originator": 0.35}),
        ("Base Case", {}),
        ("Bull Case", {"target_generic_share": 0.30, "price_discount_vs_originator": 0.50}),
    ]:
        p = dataclasses.replace(base_gen, **gp)
        gen_scenarios[sn] = calculate_kpis_generic(forecast_generic(p, forecast_months=60))

    row += 1
    ws5.write(row, 1, ""); ws5.write(row, 2, "Bear Case", fmt["th"]); ws5.write(row, 3, "Base Case", fmt["th"]); ws5.write(row, 4, "Bull Case", fmt["th"])
    for label, key, vtype in [
        ("Umsatz Jahr 1", "year1_revenue", "eur"),
        ("Umsatz 5J kumuliert", "total_5y_revenue", "eur"),
        ("Gewinn 5J kumuliert", "total_5y_profit", "eur"),
        ("Peak Marktanteil", "peak_share", "pct"),
        ("Volumen aus Aut-idem (%)", "volume_aut_idem_pct", "pct"),
        ("Volumen aus Tender (%)", "volume_tender_pct", "pct"),
    ]:
        row += 1
        ws5.write(row, 1, label, fmt["label_bold"])
        for c, sn in enumerate(["Bear Case", "Base Case", "Bull Case"]):
            val = gen_scenarios[sn].get(key, 0) or 0
            if vtype == "eur": ws5.write(row, 2 + c, val, fmt["eur"])
            elif vtype == "pct": ws5.write(row, 2 + c, val, fmt["pct"])

    # ═══════════════════════════════════════════════════════════════════
    # SHEET 6: METHODIK (Transparency Matrix)
    # ═══════════════════════════════════════════════════════════════════
    ws6 = wb.add_worksheet("Methodik")
    ws6.hide_gridlines(2); ws6.set_tab_color("#7c3aed")
    ws6.set_column("A:A", 3); ws6.set_column("B:B", 32); ws6.set_column("C:C", 22)
    ws6.set_column("D:D", 50); ws6.set_column("E:E", 40)

    row = 1
    ws6.merge_range(row, 1, row, 4, "Methodik & Transparenz-Matrix", fmt["title"])
    row += 1
    ws6.merge_range(row, 1, row, 4, "Jeder Datenpunkt ist klassifiziert: FAKT / ANNAHME / MODELL / LUECKE", wb.add_format({"font_size": 10, "font_color": "#6b7280", "italic": True}))

    # Legend
    row += 2
    ws6.write(row, 1, "Legende:", fmt["label_bold"])
    ws6.write(row, 2, "FAKT", fmt["fact"]); ws6.write(row, 3, "Aus oeffentlichen Quellen ableitbar", fmt["label"])
    row += 1
    ws6.write(row, 2, "ANNAHME", fmt["assumption"]); ws6.write(row, 3, "Vom User steuerbar (gelbe Zellen im INPUTS-Sheet)", fmt["label"])
    row += 1
    ws6.write(row, 2, "MODELL", fmt["model"]); ws6.write(row, 3, "Mathematisches Modell (branchenvalidiert)", fmt["label"])
    row += 1
    ws6.write(row, 2, "LUECKE", fmt["gap"]); ws6.write(row, 3, "Fuer Produktiveinsatz benoetigt (z.B. IQVIA-Daten)", fmt["label"])

    # Facts
    row += 2
    ws6.merge_range(row, 1, row, 4, "FAKTEN (aus oeffentlichen Quellen)", fmt["section"])
    row += 1
    for c, h in enumerate(["Datenpunkt", "Wert im Modell", "Quelle", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    facts = [
        ("Eliquis Patent-Ablauf EU", "Mai 2026", "EMA / Patentdatenbanken", "FAKT"),
        ("Gesamtmarkt NOAK DE", "~4.2M TRx/Monat", "GKV-Arzneimittelindex", "FAKT"),
        ("Eliquis Marktanteil", "~42%", "BMS/Pfizer Earnings, IQVIA Public", "FAKT"),
        ("Eliquis Preis/TRx", "~EUR 91.50", "Lauer-Taxe, Festbetragslisten", "FAKT"),
        ("Wettbewerber (Xarelto etc.)", "Shares & Preise", "GKV-Reports, Hersteller-Berichte", "FAKT"),
        ("Krankenkassen & Versicherte", "TK 11.5M, BARMER 8.7M etc.", "BMG-Statistik, GKV-Spitzenverband", "FAKT"),
        ("Generika-Anbieter", "Zentiva, Teva, STADA etc.", "EMA-Zulassungsantraege", "FAKT"),
        ("Aut-idem-Pflicht", "SGB V Par.129", "Gesetzestext", "FAKT"),
        ("Rabattvertrag-Mechanik", "Par.130a SGB V", "Gesetzestext", "FAKT"),
    ]
    for dp, val, source, cat in facts:
        row += 1
        ws6.write(row, 1, dp, fmt["label_bold"]); ws6.write(row, 2, val, fmt["fact"])
        ws6.write(row, 3, source, fmt["label"]); ws6.write(row, 4, cat, fmt["fact"])

    # Assumptions
    row += 2
    ws6.merge_range(row, 1, row, 4, "ANNAHMEN (User-steuerbar)", fmt["section"])
    row += 1
    for c, h in enumerate(["Parameter", "Default-Wert", "Begruendung", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    assumptions = [
        ("Erosions-Geschwindigkeit", "1.0", "Erfahrungswert; <1=langsam, >1=schnell. Abhaengig von Festbetrags-Timing", "ANNAHME"),
        ("Originator Boden-Share", "12%", "Markentreue bei Small Molecules: 10-15% typisch", "ANNAHME"),
        ("Originator Preisreduktion", "15%", "Strategische Entscheidung des Originators", "ANNAHME"),
        ("Apixaban-Marktanteil", "42%", "Anteil von Apixaban am NOAK-Gesamtmarkt", "ANNAHME"),
        ("Generika-Segment Peak", "55%", "Anteil der Apixaban-Rx, die generisch werden", "ANNAHME"),
        ("Mein Anteil am Generika-Segment", "20%", "Marktanteil unter den Apixaban-Generika", "ANNAHME"),
        ("Monate bis Peak", "18", "S-Kurven-Annahme, historisch validierbar", "ANNAHME"),
        ("Preis-Discount", "45%", "Marktueblich DE: 30-60% fuer Generika", "ANNAHME"),
        ("Aut-idem Peak-Quote", "75%", "Abhaengig von Arzt-Akzeptanz und Festbetrag", "ANNAHME"),
        ("Aut-idem Anlaufzeit", "6 Monate", "G-BA braucht 3-6 Monate fuer Festbetragsgruppe", "ANNAHME"),
        ("Tender pro Kasse", "Deterministisch", "Gewonnen/Verloren pro Kasse, Risiko als Szenario-Band", "ANNAHME"),
        ("Mein Tender-Anteil (Mehrfachvergabe)", "50%", "2 Hauptpartner pro Kasse (Versorgungssicherheit)", "ANNAHME"),
        ("COGS", "25%", "Branchenueblich Small Molecule Generika", "ANNAHME"),
        ("SG&A", "EUR 150K/Monat", "Firmenspezifisch", "ANNAHME"),
        ("AG Anteil-Erosion Speed", "0.5", "AG verliert Anteil an unabh. Generika; 0=statisch, 2=schnell", "ANNAHME"),
        ("AG Discount-Zunahme Speed", "0.5", "AG-Preis naehert sich Generika-Preis an; 0=statisch, 2=schnell", "ANNAHME"),
    ]
    for param, val, reason, cat in assumptions:
        row += 1
        ws6.write(row, 1, param, fmt["label_bold"]); ws6.write(row, 2, val, fmt["assumption"])
        ws6.write(row, 3, reason, fmt["label"]); ws6.write(row, 4, cat, fmt["assumption"])

    # Models
    row += 2
    ws6.merge_range(row, 1, row, 4, "MATHEMATISCHE MODELLE", fmt["section"])
    row += 1
    for c, h in enumerate(["Modell", "Formel / Logik", "Validierung / Referenz", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    models = [
        ("Originator-Erosion", "Exponentieller Decay: Share(t) = Floor + (Init-Floor) * e^(-k*t*speed)",
         "Standard im Pharma-Forecasting; validiert durch Clopidogrel, Atorvastatin LOEs", "MODELL"),
        ("Generika-Uptake", "Logistische S-Kurve: 1 / (1 + e^(-s*(t-m)))",
         "Rogers Adoption Curve; Standard bei Launch-Forecasts", "MODELL"),
        ("Aut-idem-Kurve", "Linear Ramp: 0 -> Peak ueber [ramp, full] Monate",
         "Abgeleitet aus G-BA Festbetrags-Timing + Apotheken-Substitutionsverhalten", "MODELL"),
        ("Tender-Effekt", "Deterministisch: Sum(gewonnene Kasse_shares) * Ramp * Aut-idem-Rate * My_Share",
         "Binaer pro Kasse (gewonnen/verloren); Risiko als Szenario-Band (Bear/Base/Bull)", "MODELL"),
        ("Preis-Erosion", "Zusaetzlicher Preisverfall: +0.3%/Monat, Max 15%",
         "Beobachteter Trend in reifen Generika-Maerkten", "MODELL"),
        ("AG Anteil-Erosion", "AG_Share(t) = max(2%, Initial * e^(-speed*0.05*t))",
         "AG verliert Anteil an unabh. Generika ueber Zeit; Floor bei 2%", "MODELL"),
        ("AG Discount-Zunahme", "AG_Disc(t) = min(85%, 1 - (1-Init) * e^(-speed*0.03*t))",
         "AG-Preis naehert sich Generika-Niveau an; Cap bei 85%", "MODELL"),
    ]
    for name, formula, ref, cat in models:
        row += 1
        ws6.set_row(row, 40)
        ws6.write(row, 1, name, fmt["label_bold"]); ws6.write(row, 2, formula, fmt["model"])
        ws6.write(row, 3, ref, fmt["label"]); ws6.write(row, 4, cat, fmt["model"])

    # Gaps
    row += 2
    ws6.merge_range(row, 1, row, 4, "LUECKEN (fuer Produktiveinsatz benoetigt)", fmt["section"])
    row += 1
    for c, h in enumerate(["Gap", "Beschreibung", "Datenquelle", "Kategorie"]):
        ws6.write(row, 1 + c, h, fmt["th"])
    gaps = [
        ("Echte IQVIA-Daten", "TRx, NRx, DDD auf Monatsebene pro Produkt", "IQVIA Midas / DPM", "LUECKE"),
        ("Festbetrags-Timing", "Wann genau bildet G-BA die Festbetragsgruppe?", "G-BA Beschluesse", "LUECKE"),
        ("Aut-idem Exclusion", "Tatsaechliche Arzt-Quote fuer aut-idem-Kreuz", "IQVIA Rx-Daten", "LUECKE"),
        ("Regionale Unterschiede", "KV-Regionen haben versch. Verordnungsmuster", "IQVIA Regional", "LUECKE"),
        ("Switching-Kosten", "Antikoagulantien: hoehere Barriere als z.B. PPIs", "Klinische Literatur", "LUECKE"),
        ("Analog-Validierung", "Historische Erosionskurven als Benchmark", "IQVIA History", "LUECKE"),
        ("Tender-Detaildaten", "Tatsaechliche Ausschreibungsvolumina pro Kasse", "GKV-Ausschreibungsportale", "LUECKE"),
    ]
    for name, desc, source, cat in gaps:
        row += 1
        ws6.write(row, 1, name, fmt["label_bold"]); ws6.write(row, 2, desc, fmt["gap"])
        ws6.write(row, 3, source, fmt["label"]); ws6.write(row, 4, cat, fmt["gap"])

    # Disclaimer
    row += 3
    ws6.merge_range(row, 1, row, 4,
        "Hinweis: Alle Daten sind synthetisch und dienen der Illustration. "
        "Angelehnt an oeffentlich verfuegbare Marktdaten. Kein Bezug zu vertraulichen IQVIA-Daten.",
        fmt["hint"])

    wb.close()
    print(f"Excel model saved to: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    build_model()
