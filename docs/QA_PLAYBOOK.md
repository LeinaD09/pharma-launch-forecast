# QA-Playbook: Forecast-Engine Audit

> **Fuer Claude Code / Claude Co-Work.**
> Dieses Playbook kodifiziert die Learnings aus dem Sildenafil-Modell-Audit
> (Feb 2026). Wende es auf jedes Forecast-Modul an, um systematisch Bugs,
> Inkonsistenzen und Verbesserungspotential zu finden.
>
> **Siehe auch:** `docs/QUALITY_TESTS.md` fuer automatisierte Tests (T1-T8).

---

## Phase 1: Vorbereitung

Bevor du loslegst:

```
1. Engine-Datei lesen (models/*_engine.py)
2. UI-Datei lesen (app/*.py)
3. Excel-Export lesen (exports/build_*_excel.py)
4. Methodik-Expander in der UI lesen
5. README Use-Case-Abschnitt lesen
```

Ziel: Du musst die Dataclass-Parameter, die Forecast-Schleife, die
KPI-Berechnung, die UI-Darstellung UND die Doku als Gesamtbild verstehen,
bevor du einzelne Bugs suchst.

---

## Phase 2: Bug-Checkliste (B)

Diese Bugs wurden in mindestens einem Modul gefunden. Pruefe jedes davon
systematisch:

### B1: Rx- vs. OTC-Umsatz auf unterschiedlicher Ebene

**Problem:** Rx-Umsatz wird auf Apothekenebene (retail) berechnet, OTC-Umsatz
auf Herstellerebene (ex-factory). Dadurch sind die Umsatzkurven nicht
vergleichbar und der Crossover-Monat ist verfaelscht.

**Check:**
```python
# In der Engine: Wie wird rx_revenue berechnet?
# FALSCH: rx_revenue = rx_tablets * rx_avg_price  (= retail)
# RICHTIG: rx_revenue = rx_tablets * rx_avg_price * rx_manufacturer_share
```

**Fix:** Parameter `rx_manufacturer_share: float = 0.52` einfuehren.
Hersteller bekommt ~52% des Apothekenpreises (retail minus ~8% Grosshandel
minus ~40% Apothekenmarge).

**Pruefe auch:** Wird der Crossover-Monat auf Basis von `rx_revenue` vs.
`otc_manufacturer_revenue` berechnet? Beide muessen auf gleicher Ebene sein.

---

### B2: Brand Premium nur auf Total, nicht auf Kanaele verteilt

**Problem:** Der Brand-Premium-Bonus wird auf `total_otc_manufacturer_revenue`
addiert, aber nicht auf die einzelnen Kanaele (`ch_apotheke_revenue`,
`ch_online_revenue`). Dadurch: Summe der Kanaele != Total.

**Check:**
```python
# Muss gelten (Toleranz 1 wegen Rundung):
assert abs(ch_apotheke_revenue + ch_online_revenue - total_otc_mfr_revenue) < 2
```

**Fix:** Brand Premium proportional auf Kanaele verteilen:
```python
for ch_name, ch_data in channel_data.items():
    ch_fraction = ch_data["retail_revenue"] / (total_retail - brand_bonus)
    ch_data["revenue"] += brand_mfr_bonus * ch_fraction
```

---

### B3: Rx-Migration uebersteigt Rx-Pool

**Problem:** Bei hohen OTC-Annahmen kann die Migration mehr Patienten/Tabletten
aus dem Rx-Pool abziehen als tatsaechlich vorhanden sind. Ergebnis: negative
Rx-Werte oder Phantom-Migranten.

**Check:**
```python
# Gibt es negative Rx-Werte?
assert all(df["rx_tablets"] >= 0)
# Ist die Migration gedeckelt?
# MUSS im Code stehen:
# migration = min(migration, rx_baseline)
```

**Fix (Patientenmodell):**
```python
otc_rxmigration_patients = min(otc_rxmigration_patients, float(params.rx_patients_monthly))
```

**Fix (Volumenmodell):** Pruefe ob `rx_tablets_base = max(0, ...)` genuegt
oder ob ein expliziter Cap noetig ist.

---

### B4: Dead Code (ungenutzter `_rx_effect()`)

**Problem:** Alte Hilfsfunktionen bleiben nach Refactoring stehen. Sie
verwirren und suggerieren Logik, die nicht mehr aktiv ist.

**Check:**
```bash
# Alle Funktionsdefinitionen in Engine:
grep "^def " models/*_engine.py
# Alle Funktionsaufrufe in Engine:
grep -oP "(?<=\s)\w+\(" models/*_engine.py | sort -u
# Differenz = Dead Code
```

**Fix:** Entfernen. Kein Kommentar "deprecated", einfach loeschen.

---

### B5: `forecast_months=0` wird zu Default statt 0

**Problem:** `months = forecast_months or params.forecast_months` -- wenn
`forecast_months=0` uebergeben wird, evaluiert `0 or 60` zu `60`.

**Check:**
```python
# FALSCH:
months = forecast_months or params.forecast_months
# RICHTIG:
months = forecast_months if forecast_months is not None else params.forecast_months
```

**Tipp:** Dieses Pattern kommt in JEDER Engine vor. Suche nach `or params.`
in allen Engines.

---

## Phase 3: Logik-Inkonsistenz-Checkliste (L)

### L1: Szenario-Vergleich nutzt Fresh Defaults statt User-Params

**Problem:** Szenario-Vergleichstabelle erstellt `Params(**overrides)` statt
`dataclasses.replace(user_params, **overrides)`. Dadurch ignoriert der
Vergleich alle Aenderungen, die der User in der Sidebar gemacht hat.

**Check:**
```python
# FALSCH:
p = SomeParams(**overrides)
# RICHTIG:
from dataclasses import replace
p = replace(params, **overrides) if overrides else params
```

**Wo:** Suche nach `scenarios = {` oder `comp_rows` in `app/*.py`.

---

### L2: Slider-Reset bei Szenario-Wechsel

**Problem:** Streamlit ignoriert `value=` auf Widgets wenn der `key` schon in
`session_state` existiert. Beim Szenario-Wechsel bleiben alte Slider-Werte
stehen.

**Fix:**
```python
prev = st.session_state.get("_prev_scenario")
if prev is not None and prev != scenario:
    for key in ["slider1", "slider2", ...]:
        st.session_state.pop(key, None)
    st.session_state["_prev_scenario"] = scenario
    st.rerun()
st.session_state["_prev_scenario"] = scenario
```

**Check:** Szenario wechseln, Slider pruefen. Wenn alter Wert bleibt = Bug.

---

### L3: Tadalafil/Wettbewerber-Migration ohne Saisonalitaet

**Problem:** Haupt-OTC-Volumen wird mit `* season_factor` multipliziert, aber
die Tadalafil-Migration nicht. Dadurch summieren sich die Teile nicht zum
Ganzen.

**Check:**
```python
# Tadalafil-Migration MUSS auch season_factor haben:
tada_tablets = tada_migration * season_factor  # Volumenmodell
tada_tablets = tada_patients * tablets_per_patient * season_factor  # Patientenmodell
```

---

### L4: Magic Numbers ohne Parametrisierung

**Problem:** Formeln enthalten hartcodierte Zahlen (z.B. `* 0.7`, `* 0.15`),
die weder dokumentiert noch ueber die Sidebar steuerbar sind.

**Check:**
```bash
# Suche nach verdaechtigen Literalen in der Forecast-Schleife:
grep -n "[0-9]\.[0-9]" models/*_engine.py | grep -v "def\|#\|import\|0.0\|1.0"
```

**Fix:** Als benannte Parameter in die Dataclass aufnehmen mit Docstring:
```python
# FALSCH:
bonus = 1.0 + (factor - 0.7) * 0.15
# RICHTIG:
discretion_baseline: float = 0.70   # Basis ohne Bonus
discretion_sensitivity: float = 0.15  # Staerke des Shifts
bonus = 1.0 + (factor - params.discretion_baseline) * params.discretion_sensitivity
```

---

## Phase 4: Qualitative Verbesserungen (Q)

### Q1: Breakeven-KPI fehlt

**Check:** Gibt es `breakeven_month` in `calculate_kpis_*()`?

**Berechnung:**
```python
breakeven = df[df["cumulative_profit"] > 0]
breakeven_month = int(breakeven.iloc[0]["month"]) if len(breakeven) > 0 else None
```

---

### Q2: Marketing-ROI fehlt

**Check:** Gibt es `marketing_roi` in `calculate_kpis_*()`?

**Berechnung:**
```python
marketing_roi = cumulative_profit / cumulative_marketing if cumulative_marketing > 0 else 0
```

---

### Q3: Marketing als Stufenfunktion statt Taper

**Problem:** Marketing springt von 100% auf 50% (Maintenance) in einem
einzigen Monat. Unrealistisch.

**Fix:** Linearer Taper ueber `marketing_taper_months`:
```python
marketing_taper_months: int = 6  # Neuer Parameter

if m > params.marketing_ramp_months:
    taper_progress = min(1.0, (m - params.marketing_ramp_months) / max(1, params.marketing_taper_months))
    mktg_factor = 1.0 + (params.marketing_maintenance_factor - 1.0) * taper_progress
    marketing_spend *= mktg_factor
```

---

### Q4: Profitabilitaet nicht nach Rx/OTC aufgeschluesselt

**Check:** Gibt es `rx_gross_profit` und `otc_gross_profit` als separate Spalten?

**Fix:**
```python
rx_cogs = rx_revenue * params.cogs_pct
otc_cogs = otc_mfr_revenue * params.cogs_pct
rx_gross_profit = rx_revenue - rx_cogs
otc_gross_profit = otc_mfr_revenue - otc_cogs
```

Ermoeglicht 2x2-Grid im Profitabilitaets-Tab.

---

## Phase 5: UI-Checkliste

### U1: KPI-Kacheln vollstaendig?

Pruefe ob alle berechneten KPIs auch angezeigt werden:
```python
# Alle Keys aus calculate_kpis_*():
kpi_keys = set(calculate_kpis(df).keys())
# Alle kpis['...'] Referenzen in app/*.py:
# grep -oP "kpis\['\w+'\]" app/*.py
# Differenz = nicht angezeigte KPIs
```

### U2: Header vorhanden?

Jede Seite braucht:
- Modell-Titel
- Szenario-Anzeige
- Modell-Typ (z.B. "Volume-Based" oder "Patient-Based")

### U3: Profitabilitaets-Tab als 2x2-Grid?

Vier Charts:
1. Rx vs. OTC Bruttogewinn (grouped bars)
2. Kanal-Profitabilitaet (grouped bars)
3. Kumuliert: Umsatz + Gewinn + Marketing (Linien)
4. Monatlich: Bruttogewinn vs. Marketing (Balken + Linie)

### U4: Methodik-Expander aktuell?

Checke gegen Engine-Code:
- Stimmen die Methodik-Beschreibungen mit der tatsaechlichen Logik ueberein?
- Werden entfernte Features noch erwaehnt? (z.B. "Telemedizin", "Drogerie")
- Stimmen die Default-Werte in der Methodik mit der Dataclass ueberein?

---

## Phase 6: Cross-File-Konsistenz

### C1: Engine <-> UI Spaltenreferenzen

```bash
# Alle DataFrame-Spalten aus Engine:
grep -oP '"[a-z_]+"(?=\s*:)' models/*_engine.py | sort -u > /tmp/cols.txt
# Alle Spaltenreferenzen aus UI:
grep -oP 'df\["[a-z_]+"\]' app/*.py | grep -oP '"[a-z_]+"' | sort -u > /tmp/refs.txt
# Fehlende:
comm -23 /tmp/refs.txt /tmp/cols.txt
```

### C2: Engine <-> Excel-Export

Gleicher Check fuer `exports/build_*_excel.py`.

### C3: Params <-> Sidebar

Pruefe ob jeder steuerbare Parameter auch als Slider/Input in der Sidebar ist.
Neue Engine-Parameter vergisst man leicht in der UI.

### C4: Zwei Modelle konsistent (wenn vorhanden)

Falls Volume- UND Patient-Modell existieren:
- Gleiche Kanal-Logik?
- Gleiche Brand-Premium-Logik?
- Gleiche Profitabilitaets-Berechnung?
- Gleiche KPI-Definitionen (ausser modellspezifische)?
- Gleiches UI-Layout (KPI-Kacheln, Tab-Struktur, Styling)?

---

## Phase 7: Ergebnis-Report

Kategorisiere alle Funde:

| Kategorie | Prioritaet | Kriterium |
|---|---|---|
| **B (Bug)** | SOFORT fixen | Falsche Zahlen, Crashes, Dateninkonsistenz |
| **L (Logik)** | Vor naechstem Release | Inkonsistente Annahmen, fehlende Kopplung |
| **Q (Qualitaet)** | Backlog | Fehlende Features, UX-Verbesserungen |

Format:
```
B1: [Kurzbeschreibung] -- [Datei:Zeile] -- [Fix-Aufwand: gering/mittel/hoch]
L1: [Kurzbeschreibung] -- [Datei:Zeile] -- [Fix-Aufwand]
Q1: [Kurzbeschreibung] -- [Wo] -- [Fix-Aufwand]
```

---

## Tipps & Hinweise

### PowerShell-Probleme (Windows)

- **`&&` funktioniert nicht** in aelteren PowerShell-Versionen. Nutze `;`
  oder einzelne Befehle.
- **Unicode-Fehler** (`UnicodeEncodeError: cp1252`): Setze
  `PYTHONIOENCODING=utf-8` oder vermeide Sonderzeichen in Print-Statements.
  Betroffen: `≈`, `→`, `✓`, Umlaute.
- **Inline-Python in PowerShell**: Komplexe f-Strings mit Klammern brechen.
  Schreibe den Code in eine `.py`-Datei und fuehre diese aus.

### Streamlit-spezifisch

- **Bytecode-Cache auf Streamlit Cloud**: Nach Deploy koennen alte
  `.pyc`-Dateien aktiv bleiben. Fix: `importlib.reload(module)` vor dem
  Import im UI-File.
- **`value=` wird ignoriert**: Streamlit ignoriert `value=` wenn `key` schon
  in `session_state` ist. Fix: `session_state.pop(key)` + `st.rerun()`.
- **Widget-Keys muessen unique sein** pro Seite. Bei Multi-Page-Apps
  Praefix nutzen (z.B. `silpat_`, `sil_`).

### Modell-Architektur-Patterns

- **Rx-Rueckgang immer ABLEITEN**, nie als unabhaengigen Parameter setzen.
  Sonst: Doppelzaehlung (Tabletten in Rx UND OTC gleichzeitig).
- **Alle Umsaetze auf gleicher Ebene** (Hersteller ODER Retail, nie gemischt).
- **Brand Premium proportional verteilen**, nicht nur auf Total addieren.
- **Saisonalitaet auf ALLE Volumenkomponenten** anwenden (auch Migration).
- **Marketing hat KEINEN Volumen-Effekt** in diesen Modellen. Reiner
  Kostenfaktor. Wenn Volumen-Feedback gewuenscht: als separates Feature
  implementieren.
- **`dataclasses.replace()`** fuer Szenario-Vergleiche, nicht `Params(**overrides)`.

### Reihenfolge der Fixes

1. Bugs (B) zuerst -- falsche Zahlen sind das Schlimmste
2. Logik (L) danach -- Inkonsistenzen verwirren Nutzer
3. Qualitaet (Q) zum Schluss -- neue Features sind nice-to-have
4. Tests nach JEDEM Schritt laufen lassen
5. Nach allen Fixes: UI + Excel + Methodik + README pruefen

---

## Checkliste zum Abhaken

```
Engine:
[ ] B1: Rx/OTC Umsatz auf gleicher Ebene (Hersteller)?
[ ] B2: Brand Premium auf Kanaele verteilt?
[ ] B3: Rx-Migration gedeckelt?
[ ] B4: Kein Dead Code?
[ ] B5: `forecast_months=0` korrekt behandelt?
[ ] L1: Szenario-Vergleich nutzt User-Params?
[ ] L3: Alle Migrationen mit Saisonalitaet?
[ ] L4: Keine Magic Numbers in Forecast-Schleife?
[ ] Q1: Breakeven-KPI vorhanden?
[ ] Q2: Marketing-ROI vorhanden?
[ ] Q3: Marketing-Taper (nicht Stufe)?
[ ] Q4: Rx/OTC Bruttogewinn separat?

UI:
[ ] L2: Slider-Reset bei Szenario-Wechsel?
[ ] U1: Alle KPIs angezeigt?
[ ] U2: Header mit Titel + Szenario?
[ ] U3: Profitabilitaet als 2x2-Grid?
[ ] U4: Methodik-Expander aktuell?

Cross-File:
[ ] C1: Engine-Spalten == UI-Referenzen?
[ ] C2: Engine-Spalten == Excel-Referenzen?
[ ] C3: Params == Sidebar-Widgets?
[ ] C4: Zwei Modelle konsistent (falls vorhanden)?

Doku:
[ ] README Use-Case-Abschnitt aktuell?
[ ] Methodik in UI aktuell?
[ ] docs/*.md aktuell?
```
