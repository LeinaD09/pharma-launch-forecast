# Sildenafil Rx-to-OTC Switch -- Patientenbasiertes Modell

**Datei:** `models/sildenafil_patient_engine.py` | **UI:** `app/sildenafil_patient.py`

---

## 1. Modell-Philosophie

Das patientenbasierte Modell folgt dem Best-Practice-Ansatz fuer Pharma-Launch-Forecasts:
Jede Volumenzahl wird aus einem transparenten Patientenfunnel abgeleitet.
Der OTC-Peak wird **berechnet** (nicht als Input gesetzt).

**Fluss:**

```
Epidemiologie (ED-Praevalenz, 5 Mio.)
  --> Therapiequote (30% behandelt, 70% unbehandelt)
  --> Adressierbarer Pool (15% der Unbehandelten = 525.000 Patienten)
  --> Patienten-Uptake (logistische S-Kurve)
  --> Tabletten = Patienten x Tabletten/Patient/Monat
  --> + Saisonalitaet + Preiselastizitaet
  --> + Tadalafil-Migration (Patienten --> Tabletten)
  --> Kanalverteilung, Marke/Generika
  --> Umsatz & Profitabilitaet
```

**Kernunterschied zum Volumenmodell:**
- Volumenmodell: OTC Peak = **Input** (2,1 Mio. Tabletten/Mon.)
- Patientenmodell: OTC Peak = **berechnet** (525.000 Patienten x 4,0 Tabl. = 2,1 Mio.)

Beide Modelle kommen im Base Case auf denselben Peak, aber das Patientenmodell
macht den Weg dorthin transparent und nachvollziehbar.

---

## 2. Parameter-Uebersicht

### 2.1 Epidemiologie & Patientenpool

| Parameter | Default | Beschreibung |
|---|---|---|
| `ed_prevalence_men` | 5.000.000 | ED-Praevalenz Maenner DE |
| `treatment_rate` | 30% | Aktuell in Behandlung |
| `addressable_pct` | 15% | Anteil der Unbehandelten, die OTC kaufen wuerden |
| `uptake_ramp_months` | 18 | Monate bis ~95% des adressierbaren Pools erreicht |
| `tablets_per_patient_per_month` | 4,0 | Durchschn. Nutzungsfrequenz |

**Abgeleitete Groessen:**
```
unbehandelt         = 5.000.000 x 70%  = 3.500.000
adressierbarer_pool = 3.500.000 x 15%  =   525.000 Patienten
otc_peak_tabletten  =   525.000 x 4,0  = 2.100.000 Tabletten/Monat
```

### 2.2 Patienten-Quellenverteilung

| Parameter | Default | Beschreibung |
|---|---|---|
| `new_patient_share` | 63% | Neue Patienten (nie Arzt gehabt) -- UK-Referenz |

Die verbleibenden 37% sind Rx-Migranten (Patienten, die von Rx zu OTC wechseln).

### 2.3 Rx-Markt (Baseline vor Switch)

| Parameter | Default | Beschreibung |
|---|---|---|
| `rx_patients_monthly` | 217.000 | Sildenafil Rx Patienten/Monat |
| `rx_tablets_per_patient` | 4,0 | Tabletten pro Rx-Patient/Monat |
| `rx_price_brand` | 11,19 EUR | Viagra Apothekenpreis/Tablette |
| `rx_price_generic` | 1,50 EUR | Generika Apothekenpreis/Tablette |
| `rx_brand_share` | 10% | Viagra-Anteil am Rx-Volumen |
| `rx_manufacturer_share` | 52% | Herstelleranteil am Apothekenpreis |

```
rx_tablets_baseline = 217.000 x 4,0 = 868.000 Tabletten/Monat
```

### 2.4 OTC-Preise

| Parameter | Default | Beschreibung |
|---|---|---|
| `otc_price_per_tablet` | 5,99 EUR | OTC Preis/Tablette |
| `price_elasticity` | -0,5 | Preiselastizitaet (gering) |
| `price_trend_annual` | -3% p.a. | Jaehrlicher Preisverfall |

### 2.5 Tadalafil-Migration

| Parameter | Default | Beschreibung |
|---|---|---|
| `tadalafil_patients_monthly` | 120.000 | Tadalafil Rx Patienten/Monat |
| `tadalafil_tablets_per_patient` | 4,0 | Tabletten/Tadalafil-Patient/Monat |
| `tadalafil_switch_pct` | 12% | Migration zu Sildenafil OTC |
| `tadalafil_migration_months` | 24 | Logistische Migrationsdauer |

```
tada_peak_tablets = 120.000 x 4,0 x 12% = 57.600 Tabletten/Monat
```

### 2.6 Marke vs. Generika

| Parameter | Default | Beschreibung |
|---|---|---|
| `brand_otc_share` | 25% | Viagra Connect Startanteil OTC |
| `brand_otc_share_trend` | -3% p.a. | Jaehrliche Erosion |
| `brand_price_premium` | 1,8x | Preisfaktor Marke vs. Generika |

### 2.7 Kanalverteilung

Identisch zum Volumenmodell (apothekenpflichtig, 2 Kanaele):

| Kanal | Start-Anteil | Trend p.a. | Marge | Distribution | Diskretionsfaktor |
|---|---|---|---|---|---|
| Stationaere Apotheke | 55% | -2 Pp. | 42% | 6% | 0,70 |
| Online-Apotheke | 45% | +2 Pp. | 30% | 10% | 1,00 |

### 2.8 Saisonalitaet

Identisch zum Volumenmodell:
```
Jan=0.90  Feb=1.05  Marz=1.00  Apr=1.00  Mai=1.05  Jun=1.10
Jul=1.05  Aug=1.00  Sep=0.95   Okt=0.95  Nov=0.95  Dez=1.00
```

### 2.9 Marketing

| Parameter | Default | Beschreibung |
|---|---|---|
| `marketing_monthly_eur` | 500.000 | Monatliches Marketing-Budget |
| `marketing_ramp_months` | 18 | Vollbudget-Phase |
| `marketing_maintenance_factor` | 0,5 | Maintenance = 50% |
| `marketing_taper_months` | 6 | Linearer Uebergang |

Taper-Logik identisch zum Volumenmodell (siehe dort).

### 2.10 Kosten & Diskretionseffekt

| Parameter | Default | Beschreibung |
|---|---|---|
| `cogs_pct` | 12% | COGS als % vom Herstellerumsatz |
| `discretion_baseline` | 0,70 | Basis-Diskretionsfaktor |
| `discretion_sensitivity` | 0,15 | Staerke des Kanal-Shifts |

---

## 3. Berechnungslogik (Schritt fuer Schritt)

### Schritt 1: Patientenzahlen

```
addressable_patients = ed_prevalence * (1 - treatment_rate) * addressable_pct
                     = 5.000.000 * 0.70 * 0.15 = 525.000

otc_patients_active = logistic_ramp(monat, peak=525.000, ramp=18)
```

Patienten-Quellenverteilung:
```
otc_new_patients          = otc_patients_active * new_patient_share (63%)
otc_rxmigration_patients  = otc_patients_active * (1 - new_patient_share) (37%)
otc_rxmigration_patients  = min(otc_rxmigration_patients, rx_patients_monthly)  <-- Cap!
```

> **Migrations-Cap:** Die Rx-Migration kann nicht mehr Patienten umfassen als
> tatsaechlich im Rx-Pool existieren. Dies verhindert Phantom-Migranten bei
> hohen OTC-Annahmen.

Rx-Patienten nach Migration:
```
rx_patients = max(0, rx_patients_monthly - otc_rxmigration_patients)
```

### Schritt 2: Tabletten (Patienten x Frequenz)

```
otc_base_tablets = otc_patients_active * tablets_per_patient_per_month
otc_seasonal     = otc_base_tablets * season_factor
price_vol_effect = 1 + ((1+price_trend)^(m/12) - 1) * price_elasticity
otc_tablets      = otc_seasonal * price_vol_effect
```

Tadalafil-Migration (in Tabletten, mit Saisonalitaet):
```
tada_migration_patients = logistic(m, peak=120.000*12%, midpoint, steepness)
tada_tablets = tada_migration_patients * tadalafil_tablets_per_patient * season_factor
otc_tablets += tada_tablets
```

Rx-Tabletten:
```
rx_tablets = rx_patients * rx_tablets_per_patient * season_factor
```

### Schritt 3: Volumen-Dekomposition (in Tabletten)
```
otc_from_tadalafil    = tada_tablets
otc_from_new_patients = (otc_tablets - tada_tablets) * new_patient_share
otc_from_rx_migration = (otc_tablets - tada_tablets) - otc_from_new_patients
```

### Schritt 4: Kanalverteilung

Identisch zum Volumenmodell:
1. Basis-Shares mit Zeittrend
2. Normalisierung
3. Diskretions-Bonus
4. Erneute Normalisierung
5. Tabletten und Umsatz pro Kanal

### Schritt 5: Brand vs. Generika

Identisch zum Volumenmodell: Anteil mit linearer Erosion, Preispremium,
proportionale Verteilung des Brand-Bonus auf Kanaele.

### Schritt 6: Rx-Umsatz
```
rx_avg_retail_price = rx_brand_share * rx_price_brand + (1-rx_brand_share) * rx_price_generic
rx_revenue = rx_tablets * rx_avg_retail_price * rx_manufacturer_share
```

### Schritt 7: Profitabilitaet
```
rx_gross_profit  = rx_revenue * (1 - cogs_pct)
otc_gross_profit = otc_mfr_revenue * (1 - cogs_pct)
gross_profit     = rx_gross_profit + otc_gross_profit
operating_profit = gross_profit - marketing_spend
```

### Schritt 8: Therapiequote (abgeleitet!)
```
active_new_patients      = otc_new_patients  (aktive OTC-Kaeufer, die neu sind)
treatment_rate_effective = treatment_rate + active_new_patients / ed_prevalence
```

> **Konsistenz:** Die Therapiequote wird aus den tatsaechlich aktiven
> OTC-Neupatienten abgeleitet, nicht unabhaengig gesetzt. Sie steigt
> nur so schnell, wie tatsaechlich neue Patienten in den OTC-Markt eintreten.

---

## 4. KPI-Definitionen

| KPI | Berechnung |
|---|---|
| OTC Umsatz M12 | Summe `otc_manufacturer_revenue` fuer Monate 1-12 |
| Gesamtumsatz M12 | Summe `total_revenue` (Rx+OTC) fuer Monate 1-12 |
| OTC > Rx ab | Erster Monat wo OTC-Umsatz > Rx-Umsatz / OTC-Tabletten > Rx-Tabletten |
| Gewinn 5J | Kumulierter Operating Profit nach 60 Monaten |
| OTC Patienten Peak | Maximum von `otc_patients_active` |
| Neue OTC-Patienten | Maximum von `active_new_patients` |
| Rx-Rueckgang | (Rx Y1 - Rx letzte 12 Mon.) / Rx Y1 (saisonbereinigt) |
| Therapiequote 5J | Effektive Therapiequote in Monat 60 |
| Breakeven | Erster Monat mit kumulativem Gewinn > 0 |
| Marketing-ROI | Kumulierter Gewinn / Kumuliertes Marketing (5J) |
| Marketing 5J | Kumulierte Marketing-Ausgaben nach 60 Monaten |
| Umsatz 5J | Kumulierter Gesamtumsatz (Rx+OTC) nach 60 Monaten |

---

## 5. Szenarien

| Parameter | Konservativ | Base Case | Optimistisch |
|---|---|---|---|
| Erreichbare Unbehandelte | 8% | 15% | 19% |
| Tabletten/Patient/Mon. | 3,5 | 4,0 | 4,5 |
| Ramp (Monate) | 24 | 18 | 12 |
| Marketing/Mon. | 300.000 | 500.000 | 750.000 |
| Neue Patienten (%) | 55% | 63% | 70% |
| Markenanteil (%) | 20% | 25% | 35% |

**Resultierende OTC Peaks:**
- Konservativ: 3.500.000 x 8% x 3,5 = 980.000 Tabletten/Mon.
- Base Case: 3.500.000 x 15% x 4,0 = 2.100.000 Tabletten/Mon.
- Optimistisch: 3.500.000 x 19% x 4,5 = 2.992.500 Tabletten/Mon.

---

## 6. UI-Aufbau

### Dashboard-Header
- Titel: "Sildenafil Rx-to-OTC Switch Patient-Based Forecast"
- Szenario-Anzeige, Modell-Typ

### KPI-Kacheln (3 Reihen)
- **Reihe 1 "Was bringt der Switch?":** OTC Umsatz M12, Gesamtumsatz M12, OTC>Rx ab, Gewinn 5J
- **Reihe 2 "Wie verteilt sich der Markt?":** OTC Patienten Peak, Neue OTC-Patienten, Rx-Rueckgang, Therapiequote 5J
- **Reihe 3 "Lohnt es sich?":** Breakeven, Marketing-ROI, Marketing 5J, Umsatz 5J

### Chart-Tabs (4 Tabs)
1. **Patienten & Therapieluecke** -- 2x2: Uptake + Herkunft (oben), Treatment Gap + Therapiequote (unten), Funnel-Tabelle
2. **Rx vs. OTC** -- Tabletten-Linien + Umsatz-Balken
3. **Kanal & Marke** -- 2x2 + Kanal-Umsatz: Kanalvolumen, Kanal-Anteile, Marke/Generika, Markenanteil-Erosion
4. **Profitabilitaet** -- 2x2: Rx/OTC Bruttogewinn, Kanal-Profit, Kumuliert, Monatlich

### Patienten-Funnel-Tabelle (in Tab 1)
Zeigt den kompletten Funnel von ED-Praevalenz bis Peak OTC-Patienten.

### Szenario-Vergleichstabelle
Nutzt `dataclasses.replace(params, **overrides)` um aktuelle Sidebar-Werte beizubehalten.

---

## 7. Unterschiede zum Volumenmodell

| Aspekt | Volumenmodell | Patientenmodell |
|---|---|---|
| OTC Peak | Direkter Input (Tabletten) | Berechnet: Patienten x Frequenz |
| Steuergroesse | `otc_peak_tablets_per_month` | `addressable_pct` + `tablets_per_patient` |
| Patienten explizit? | Nein (nur abgeleitet) | Ja (Kerngroesse) |
| Rx-Input | Tabletten/Monat | Patienten/Monat + Tabl./Patient |
| Tadalafil-Input | Tabletten/Monat | Patienten/Monat + Tabl./Patient |
| Rx-Migration-Cap | Nein (theoretisch unbegrenzt) | Ja: min(migration, rx_patients) |
| Therapiequote | Aus OTC-Tabletten abgeleitet | Aus OTC-Patienten abgeleitet |
| Rx-Rueckgang (5J) | ~92% (Tabletten direkt subtrahiert) | ~84% (Patienten subtrahiert, dann x Tabl.) |
| Patienten-Funnel | Nicht vorhanden | Vollstaendige Tabelle in UI |
| Tab-Struktur | 5 Tabs | 4 Tabs (Patienten & Therapieluecke als eigener Tab) |

**Warum unterschiedlicher Rx-Rueckgang (84% vs. 92%)?**

Das Volumenmodell subtrahiert OTC-Tabletten direkt vom Rx-Tablettenpool.
Das Patientenmodell subtrahiert Patienten und multipliziert dann mit
`tablets_per_patient * season_factor`. Da die Saisonalitaet auf die
OTC-Tabletten wirkt (nicht auf die Patienten), ergibt die Migration
in Tabletten nicht exakt `migration_patients * 4.0` in jedem Monat.
Dieser Unterschied ist erwartet und korrekt -- beide Modelle sind in sich konsistent.

---

## 8. Datenquellen

Identisch zum Volumenmodell (siehe `Modell_Volumen.md`, Abschnitt 7).
