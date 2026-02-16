# Sildenafil Rx-to-OTC Switch -- Volumenbasiertes Modell

**Datei:** `models/sildenafil_otc_engine.py` | **UI:** `app/sildenafil.py`

---

## 1. Modell-Philosophie

Das Volumenmodell setzt den OTC-Peak direkt als Input-Parameter (Tabletten/Monat)
und leitet daraus alle weiteren Groessen ab. Der Nutzer steuert also das Ergebnis
ueber eine explizite Volumenannahme.

**Fluss:**

```
OTC Peak (Input, Tabletten/Mon.)
  --> Logistische S-Kurve (Ramp)
  --> + Saisonalitaet
  --> + Preiselastizitaet
  --> + Tadalafil-Migration
  --> Volumen-Dekomposition (Neue Patienten / Rx-Migration / Tadalafil)
  --> Kanalverteilung (Apotheke / Online)
  --> Marke vs. Generika
  --> Umsatz & Profitabilitaet
```

---

## 2. Parameter-Uebersicht

### 2.1 Produkt & Epidemiologie

| Parameter | Default | Beschreibung |
|---|---|---|
| `ed_prevalence_men` | 5.000.000 | ED-Praevalenz Maenner DE (Braun et al. 2000) |
| `treatment_rate` | 30% | Aktuell in Behandlung (May et al. 2007) |

### 2.2 Rx-Markt (Baseline vor Switch)

| Parameter | Default | Beschreibung |
|---|---|---|
| `rx_tablets_per_month` | 868.000 | Sildenafil Rx Tabletten/Monat (217K Packungen x 4) |
| `rx_price_brand` | 11,19 EUR | Viagra Apothekenverkaufspreis/Tablette |
| `rx_price_generic` | 1,50 EUR | Generika Apothekenverkaufspreis/Tablette |
| `rx_brand_share` | 10% | Viagra-Anteil am Rx-Volumen |
| `rx_manufacturer_share` | 52% | Herstelleranteil am Apothekenpreis (ex-factory) |

**Rx-Umsatz-Berechnung:**
```
rx_avg_retail_price = rx_brand_share * rx_price_brand + (1 - rx_brand_share) * rx_price_generic
rx_revenue = rx_tablets * rx_avg_retail_price * rx_manufacturer_share
```

> **Wichtig:** Rx-Umsatz wird auf Herstellerebene (ex-factory) berechnet, nicht
> auf Apothekenebene. Dies stellt Konsistenz mit dem OTC-Umsatz her, der ebenfalls
> als Herstellerumsatz (nach Abzug von Apothekenmarge und Distributionskosten)
> ausgewiesen wird.

### 2.3 OTC-Markt

| Parameter | Default | Beschreibung |
|---|---|---|
| `otc_price_per_tablet` | 5,99 EUR | OTC Preis/Tablette (Apothekenabgabe) |
| `otc_peak_tablets_per_month` | 2.100.000 | Peak OTC-Volumen (direkt als Input) |
| `otc_ramp_months` | 18 | Monate bis Peak (logistische S-Kurve) |
| `new_patient_share` | 63% | Anteil neue Patienten (UK-Referenz: Lee et al. 2021) |
| `tablets_per_patient_per_month` | 4,0 | Durchschn. Tabletten/Patient/Monat |

### 2.4 Marke vs. Generika

| Parameter | Default | Beschreibung |
|---|---|---|
| `brand_otc_share` | 25% | Viagra Connect Anteil am OTC-Volumen |
| `brand_otc_share_trend` | -3% p.a. | Jaehrliche Erosion durch Generika-OTC |
| `brand_price_premium` | 1,8x | Preisfaktor Marke vs. Generika |

### 2.5 Kanalverteilung (Omnichannel)

Sildenafil OTC waere apothekenpflichtig -- nur zwei Kanaele:

| Kanal | Start-Anteil | Trend p.a. | Marge | Distribution | Diskretionsfaktor |
|---|---|---|---|---|---|
| Stationaere Apotheke | 55% | -2 Pp. | 42% | 6% | 0,70 |
| Online-Apotheke | 45% | +2 Pp. | 30% | 10% | 1,00 |

**Herstellerumsatz pro Kanal:**
```
mfr_share = 1.0 - margin_pct - distribution_cost_pct
ch_mfr_revenue = ch_tablets * otc_price * mfr_share
```

### 2.6 Tadalafil-Migration

| Parameter | Default | Beschreibung |
|---|---|---|
| `tadalafil_rx_tablets_monthly` | 480.000 | Tadalafil Rx Tabletten/Monat |
| `tadalafil_switch_to_sildenafil_otc` | 12% | Anteil der Tadalafil-Nutzer, die zu OTC wechseln |
| `tadalafil_migration_months` | 24 | Logistische Migrationsdauer |

### 2.7 Preisentwicklung

| Parameter | Default | Beschreibung |
|---|---|---|
| `price_elasticity` | -0,5 | Preiselastizitaet (gering: Selbstzahler-Markt) |
| `price_trend_annual` | -3% p.a. | Jaehrlicher Preisverfall (Generika-Druck) |

### 2.8 Saisonalitaet

```
Jan=0.90  Feb=1.05  Marz=1.00  Apr=1.00  Mai=1.05  Jun=1.10
Jul=1.05  Aug=1.00  Sep=0.95   Okt=0.95  Nov=0.95  Dez=1.00
```

Begruendung: Valentinstag (Feb), Sommer (Jun/Jul) erhoehen Nachfrage; Herbst/Winter reduzieren.

### 2.9 Marketing

| Parameter | Default | Beschreibung |
|---|---|---|
| `marketing_monthly_eur` | 500.000 | Monatliches Marketing-Budget |
| `marketing_ramp_months` | 18 | Vollbudget-Phase (Launch) |
| `marketing_maintenance_factor` | 0,5 | Maintenance = 50% des Vollbudgets |
| `marketing_taper_months` | 6 | Uebergangsdauer (linearer Taper) |

**Taper-Logik:**
```
Wenn m > ramp_months:
  taper_progress = min(1.0, (m - ramp_months) / taper_months)
  faktor = 1.0 + (maintenance_factor - 1.0) * taper_progress
  marketing_spend = budget * faktor
```

Beispiel (Base Case): Monat 1-18: 500K/Mon. | Monat 19-24: linearer Uebergang | ab Monat 25: 250K/Mon.

> Marketing ist ein reiner Kostenfaktor -- es hat keinen Einfluss auf das OTC-Volumen.

### 2.10 Kosten & Profitabilitaet

| Parameter | Default | Beschreibung |
|---|---|---|
| `cogs_pct` | 12% | COGS (Herstellungskosten als % vom Herstellerumsatz) |

```
rx_gross_profit  = rx_revenue * (1 - cogs_pct)
otc_gross_profit = otc_mfr_revenue * (1 - cogs_pct)
gross_profit     = rx_gross_profit + otc_gross_profit
operating_profit = gross_profit - marketing_spend
```

### 2.11 Diskretionseffekt (Stigma-getriebener Kanal-Shift)

| Parameter | Default | Beschreibung |
|---|---|---|
| `discretion_baseline` | 0,70 | Baseline-Diskretionsfaktor (stationaer) |
| `discretion_sensitivity` | 0,15 | Staerke des Kanal-Shifts |

```
discretion_bonus = 1.0 + (ch.discretion_factor - baseline) * sensitivity
```

Beispiel: Online (factor=1.0): bonus = 1.0 + (1.0 - 0.7) * 0.15 = 1.045 (+4,5%)

Gewichtete Anteile werden normalisiert -- der Effekt verschiebt das Mix, nicht das Gesamtvolumen.

---

## 3. Berechnungslogik (Schritt fuer Schritt)

### Schritt 1: OTC-Basisvolumen
```
otc_base = logistic_ramp(monat, peak=otc_peak_tablets, ramp=otc_ramp_months)
otc_seasonal = otc_base * season_factor[monat]
price_change = (1 + price_trend)^(m/12) - 1
price_vol_effect = 1 + price_change * price_elasticity
otc_tablets = otc_seasonal * price_vol_effect
```

### Schritt 2: Tadalafil-Migration
```
tada_migration = logistic(m, peak=tada_tablets*switch_pct, midpoint, steepness) * season_factor
otc_tablets += tada_migration
```

### Schritt 3: Volumen-Dekomposition
```
otc_from_tadalafil    = tada_migration
otc_excl_tada         = otc_tablets - otc_from_tadalafil
otc_from_new_patients = otc_excl_tada * new_patient_share
otc_from_rx_migration = otc_excl_tada - otc_from_new_patients
```

### Schritt 4: Rx-Rueckgang (abgeleitet!)
```
rx_tablets_base = max(0, rx_baseline - otc_from_rx_migration)
rx_tablets = rx_tablets_base * season_factor
```

> **Zentrale Konsistenzregel:** Der Rx-Rueckgang ist **kein** unabhaengiger Parameter,
> sondern wird direkt aus der OTC-Rx-Migration abgeleitet. Tabletten koennen nicht
> gleichzeitig im Rx- und OTC-Pool sein.

### Schritt 5: Kanalverteilung (mit Diskretionseffekt)
```
1. Basis-Shares berechnen (zeitabhaengig)
2. Normalisieren auf Summe = 1.0
3. Discretion-Bonus anwenden
4. Erneut normalisieren
5. Tabletten und Umsatz pro Kanal berechnen
```

### Schritt 6: Brand Premium
```
brand_bonus = brand_tablets * (brand_price - generic_price)
brand_mfr_bonus = brand_bonus * avg_mfr_pct
--> Proportional auf Kanaele verteilt
```

### Schritt 7: Profitabilitaet
```
Umsatz (Herstellerebene):
  - Rx: rx_tablets * avg_retail_price * rx_manufacturer_share
  - OTC: Summe der Kanal-Herstellerumsaetze + Brand Premium

Kosten:
  - COGS: 12% vom Herstellerumsatz (Rx + OTC separat)
  - Marketing: Taper-Logik (siehe oben)

Gewinn:
  - Bruttogewinn = Umsatz - COGS
  - Operating Profit = Bruttogewinn - Marketing
```

---

## 4. KPI-Definitionen

| KPI | Berechnung |
|---|---|
| OTC Umsatz M12 | Summe `otc_manufacturer_revenue` fuer Monate 1-12 |
| Gesamtumsatz M12 | Summe `total_revenue` (Rx+OTC) fuer Monate 1-12 |
| OTC > Rx ab (Umsatz) | Erster Monat wo `otc_mfr_revenue > rx_revenue` |
| OTC > Rx ab (Tabletten) | Erster Monat wo `otc_tablets > rx_tablets` |
| Gewinn 5J | Kumulierter Operating Profit nach 60 Monaten |
| Online-Anteil M12 | Online-Apotheke Share in Monat 12 |
| Markenanteil M12 | Viagra Connect Anteil in Monat 12 |
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
| OTC Peak (Tabl./Mon.) | 1.200.000 | 2.100.000 | 2.700.000 |
| Ramp (Monate) | 24 | 18 | 12 |
| Marketing/Mon. | 300.000 | 500.000 | 750.000 |
| Neue Patienten (%) | 55% | 63% | 70% |
| Markenanteil (%) | 20% | 25% | 35% |

---

## 6. UI-Aufbau

### Dashboard-Header
- Titel, Szenario-Anzeige, Modell-Typ

### KPI-Kacheln (3 Reihen)
- **Reihe 1 "Was bringt der Switch?":** OTC Umsatz M12, Gesamtumsatz M12, OTC>Rx ab, Gewinn 5J
- **Reihe 2 "Wie verteilt sich der Markt?":** Online-Anteil M12, Markenanteil M12, Rx-Rueckgang, Therapiequote 5J
- **Reihe 3 "Lohnt es sich?":** Breakeven, Marketing-ROI, Marketing 5J, Umsatz 5J

### Chart-Tabs (5 Tabs)
1. **Rx vs. OTC** -- Tabletten-Linien + Umsatz-Balken (gestapelt)
2. **Stationaer vs. Online** -- Volumen (Stacked Area) + Share-Linien + Kanal-Umsatz
3. **Marke vs. Generika** -- Volumen (Stacked Area) + Erosion-Linie
4. **Patienten-Zuwachs** -- Volumen-Herkunft (Stacked Area) + Treatment Gap
5. **Profitabilitaet** -- 2x2 Grid: Rx/OTC Bruttogewinn, Kanal-Profit, Kumuliert, Monatlich

### Szenario-Vergleichstabelle
Nutzt `dataclasses.replace(params, **overrides)` um aktuelle Sidebar-Werte beizubehalten.

---

## 7. Datenquellen

| Thema | Quelle |
|---|---|
| ED-Praevalenz DE | Braun et al. (2000), Cologne Male Survey |
| Therapiequote | May et al. (2007); Arnold (2023) |
| UK OTC-Referenz | MHRA (2017); Lee et al. (2021), n=1.162 |
| Online-Apotheke | ABDA ZDF (2024); DatamedIQ (2022) |
| Stigma/Diskretion | PMC/Kantar (2020), n=11.456 |
| PDE5-Markt DE | IQVIA; Apotheke Adhoc |
| SVA-Entscheidungen | Handelsblatt; Citeline; BfArM |
