# Pharma Launch Forecast

> **Sprache:** [English](README.md) | Deutsch

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pharma-launch-forecasts.streamlit.app/)

Interaktive Prognosemodelle fuer pharmazeutische Produktlancierungen in Deutschland. Entwickelt mit Python, Streamlit und Plotly.

> **Live-Demo:** [pharma-launch-forecasts.streamlit.app](https://pharma-launch-forecasts.streamlit.app/)

Fuenf Prognose-Engines demonstrieren die Bandbreite an Launch-Szenarien, mit denen ein Strategic Portfolio Manager konfrontiert wird:

| | Use Case 1 | Use Case 2 | Use Case 3 | Use Case 4a/4b | Use Case 5 |
|---|---|---|---|---|---|
| **Szenario** | Eliquis Generika-Eintritt | GLP-1: Mounjaro vs. Ozempic | Rx-to-OTC Switch (PPI) | Sildenafil OTC Switch (2 Modelle) | Eye Care Franchise |
| **Typ** | Generikum vs. Originator | Marke vs. Marke | Dual Channel (Rx + OTC) | Omnichannel + Stigma-Markt | Sequenzieller Portfolio-Launch |
| **Markt** | Reif, erodierend | Expandierend, wachstumsstark | Kanaluebergang | Stigma-getrieben, unterversorgt | Spezialitaeten, fragmentiert |
| **Kernmechanik** | Aut-idem, Rabattvertraege | Indikationsschichtung, Lieferfaehigkeit | Verbraucherbewusstsein, Preisgestaltung | Dual-Channel, Patienten-Funnel | AMNOG-Preisbildung, Facharzt-Adoption |
| **LOE** | Mai 2026 | n/a (patentgeschuetzt) | n/a (OTC-Switch) | n/a (BfArM SVA ausstehend) | n/a (Pipeline-Launches) |
| **Preisbildung** | Festbetrag / Generika-Erosion | AMNOG Erstattungsbetrag | Freie OTC-Preisgestaltung | Marke vs. Generikum OTC | AMNOG 3-Phasen-Lebenszyklus |

## Screenshots

Starten Sie die Apps lokal, um die interaktiven Dashboards zu erkunden (siehe [Erste Schritte](#erste-schritte)).

## Architektur

```
pharma-launch-forecast/
├── models/
│   ├── forecast_engine.py           # Generic Entry Engine (Eliquis)
│   ├── brand_competition_engine.py  # Brand Competition Engine (GLP-1)
│   ├── rx_otc_engine.py             # Rx-to-OTC Switch Engine (PPI)
│   ├── sildenafil_otc_engine.py     # Sildenafil OTC Engine (volumenbasiert)
│   ├── sildenafil_patient_engine.py # Sildenafil OTC Engine (patientenbasiert)
│   └── ophthalmology_engine.py     # Ophthalmologie Portfolio Engine (Eye Care Franchise)
├── app/
│   ├── app.py                       # Multi-Page-Einstiegspunkt (st.navigation)
│   ├── main.py                      # Seite: Eliquis Generika-Eintritt
│   ├── glp1.py                      # Seite: GLP-1 Markenwettbewerb
│   ├── rx_otc.py                    # Seite: Rx-to-OTC Switch (PPI)
│   ├── sildenafil.py                # Seite: Sildenafil OTC Switch (volumenbasiert)
│   ├── sildenafil_patient.py        # Seite: Sildenafil OTC Switch (patientenbasiert)
│   └── ophthalmology.py             # Seite: Eye Care Franchise
├── data/
│   ├── market_data.py               # NOAK/DOAK Marktdaten (synthetisch)
│   └── glp1_market_data.py          # GLP-1 Marktdaten (synthetisch)
├── exports/
│   ├── build_excel_model.py                    # Excel-Generator: Eliquis
│   ├── build_glp1_excel.py                     # Excel-Generator: GLP-1
│   ├── build_rx_otc_excel.py                   # Excel-Generator: Rx-to-OTC
│   ├── build_sildenafil_excel.py               # Excel-Generator: Sildenafil
│   └── build_ophthalmology_excel.py            # Excel-Generator: Ophthalmologie
├── docs/
│   ├── Modell_Volumen.md             # Dokumentation: volumenbasiertes Sildenafil-Modell
│   ├── Modell_Patient.md             # Dokumentation: patientenbasiertes Sildenafil-Modell
│   ├── KNOWLEDGE_BASE.md             # Gemeinsame Wissensbasis
│   └── QUALITY_TESTS.md              # Qualitaetstestdefinitionen
└── requirements.txt
```

## Use Case 1: Eliquis Generika-Eintritt (Mai 2026)

**Frage:** Was passiert, wenn das meistverordnete Antikoagulans seinen Patentschutz verliert?

Zwei Perspektiven mit unabhaengigen Parametersaetzen:

- **Originator (BMS/Pfizer):** Quantifizierung des Umsatzrisikos. Modelliert Marktanteilserosion ueber exponentiellen Verfall mit konfigurierbarem Boden, Authorized-Generika-Strategie und Preisverteidigung.
- **Generika-Herausforderer:** Marktchancen-Dimensionierung. Modelliert die Marktdurchdringung ueber eine logistische S-Kurve mit einer **Entscheidungskaskade**, die Volumen nach Prioritaet zuweist:

| Prioritaet | Volumenquelle | Mechanismus | Regulatorische Grundlage |
|---|---|---|---|
| 1 (hoechste) | Rabattvertrag | Krankenkassen-Mehrfachvergabe, reduziert um Aut-idem-Ausschluss | Par.130a SGB V (Rabattvertraege) |
| 2 | Aut-idem | Substitution auf Apothekenebene (Nicht-Rabattvertrags-Rest) | SGB V Par.129 (obligatorische Generika-Substitution) |
| 3 | Organisch | Aerztliches Umstellen, Aufnahme in Hausliste (Residual) | Standard Market Access |

**Wesentliche Modellmerkmale:**
- Entscheidungskaskade: Rabattvertrag > Aut-idem > Organisch (keine Doppelzaehlung)
- **Deterministische Rabattvertragsmodellierung:** Pro-Kasse-Checkboxen (gewonnen/verloren) statt Gewinnwahrscheinlichkeiten. Rabattvertragsvolumen bereinigt um Aut-idem-Ausschluss (zeitabhaengig, gleiche Kurve wie Aut-idem-Kanal) und Mehrfachvergabe (Standard: 2 Hauptpartner, 50% Anteil)
- **Rabattvertragsszenario-Band:** Bear (kein Rabattvertrag) / Base (Nutzerauswahl) / Bull (alle Kassen gewonnen) als transparentes Risiko-Overlay auf dem Volumenchart
- Aut-idem-Anstiegskurve gekoppelt an den Festbetrag-Zeitplan
- Pro-Kasse-Rabattvertragsmodellierung (TK, BARMER, DAK, AOKs) mit deterministischem Gewonnen/Verloren und Anlauf
- Volumenzerlegung: organisch vs. Aut-idem vs. Rabattvertrag
- Originator-Preisverteidigung und Authorized-Generika-Kannibalisierung
- **Analogie-Leitplanken:** Benchmark-Validierung gegen veroeffentlichte Generika-Penetrationsdaten (Fischer & Stargardt 2016, GaBi Journal, Bayer Q-Reports, PMC) mit +/-15pp Toleranzbaendern

## Use Case 2: GLP-1 Markenwettbewerb

**Frage:** Wird Mounjaro Ozempic auf dem deutschen GLP-1-Markt ueberholen?

Zwei Perspektiven mit symmetrischer Modellstruktur:

- **Eli Lilly (Mounjaro/Tirzepatid):** Herausforderer mit wachsendem Marktanteil dank ueberlegener Wirksamkeitsdaten
- **Novo Nordisk (Ozempic/Semaglutid):** Verteidigung der Marktfuehrerschaft trotz Lieferengpaessen

**Wesentliche Modellmerkmale:**
- Marktexpansion mit logistischer Daempfung (GLP-1-Segment waechst 25-36% p.a.)
- Indikationsmultiplikator-System: T2D (Basis) + Adipositas + CV-Risiko + MASH/NASH
- Modellierung von Lieferengpaessen mit Kapazitaetsnormalisierungs-Zeitplan
- Szenario-Presets: Base Case, Bull (Lilly), Bull (Novo)
- AMNOG-Preisbildung mit vertraulichen Erstattungsbetraegen

**Eingearbeitete Realweltdaten:**
- 6,33 Mio. T2D-Patienten in Deutschland, 13,9% unter GLP-1 (BARMER 2025)
- Wegovy von GKV-Erstattung ausgeschlossen (G-BA Juni 2024: Lifestyle-Arzneimittel)
- Mounjaro: erster vertraulicher Erstattungsbetrag in Deutschland ueberhaupt (Aug 2025)
- Ozempic-Lieferengpaesse seit 2022

## Use Case 3: Rx-to-OTC Switch (PPI)

**Frage:** Was passiert, wenn ein verschreibungspflichtiges Medikament rezeptfrei erhaeltlich wird?

Referenzfall: Omeprazol/Pantoprazol 20mg PPI-Switch in Deutschland (Juli 2009).

Zwei Perspektiven:

- **Hersteller:** Dual-Channel-Umsatzmodellierung. Rx-Volumen sinkt, waehrend OTC hochlaeuft, aber OTC erreicht voellig neue Patienten.
- **Markt:** Kategorie-Disruption. OTC-Launch kannibalisierte Antazida und liess H2-Antagonisten einbrechen.

**Wesentliche Modellmerkmale:**
- Dual-Channel-Dynamik: Rx exponentieller Verfall + OTC logistischer S-Kurven-Anlauf
- Marktexpansion: 70% des OTC-Volumens von genuinen Neupatienten (hatten nie Rx)
- Angrenzende Kategorie-Kannibalisierung (Antazida, H2-Antagonisten)
- Consumer-Awareness S-Kurve gekoppelt an Marketingausgaben
- PPI-typische Saisonalitaet (GI-Beschwerden-Peak im Herbst/Winter)
- Preiselastizitaet: Patient zahlt 100% OTC (vs. GKV-Zuzahlung fuer Rx)
- Apothekenmargenstruktur: freie OTC-Preisgestaltung vs. reguliertes Rx (AMPreisV)
- Drei Szenarien: Konservativ / Base Case / Optimistisch

**Eingearbeitete Realweltdaten:**
- OTC-Markt Deutschland 2024: EUR 10,15 Mrd. (+7,1%, IQVIA)
- PPI OTC-Switch 2009: nur ~3% des PPI-Volumens wechselten zu OTC (Partial Switch)
- 11,9% Sodbrennen-Marktexpansion im 1. Jahr nach Switch
- Antazida-Kannibalisierung: -EUR 11 Mio.; H2-Antagonisten: -46%
- OTC-PPI max. 14 Tabletten/20mg gemaess BfArM

## Use Case 4: Sildenafil Rx-to-OTC Switch (Viatris/Viagra)

**Frage:** Wie gross ist die kommerzielle Chance, wenn Sildenafil in Deutschland rezeptfrei wird?

Zwei komplementaere Modelle mit identischer Kanal-/Preislogik, aber unterschiedlichen Ansaetzen zur Marktgroessenschaetzung. Referenz: UK Viagra Connect (OTC seit Maerz 2018).

### Modell 4a: Volumenbasiert (`sildenafil_otc_engine.py`)

OTC-Spitzenvolumen ist ein **direkter Input** (Tabletten/Monat). Einfach, schnell fuer Szenarioanalyse.

### Modell 4b: Patientenbasiert (`sildenafil_patient_engine.py`)

OTC-Spitze wird **berechnet** aus einem epidemiologischen Patienten-Funnel (Praevalenz -> Behandlungsluecke -> adressierbarer Pool -> Patienten x Nutzungsfrequenz). Best-Practice-Ansatz fuer Pharma-Launches.

> Beide Modelle konvergieren zum gleichen Base-Case-Peak (~2,1 Mio. Tabletten/Monat), jedoch ueber unterschiedliche Wege. Ausfuehrliche Dokumentation: [`docs/Modell_Volumen.md`](docs/Modell_Volumen.md), [`docs/Modell_Patient.md`](docs/Modell_Patient.md).

**Was diese Modelle besonders macht:**
- **Dual-Channel-Distribution:** Zwei Apothekenkanäle (stationaere Apotheke, Online-Apotheke) -- apothekenpflichtig, kein Drogeriemarkt -- mit zeitabhaengiger Anteilsentwicklung und kanalspezifischen Margenstrukturen
- **Diskretionseffekt:** Parametrisierte stigma-getriebene Kanalverschiebung (Baseline + Sensitivitaet), die widerspiegelt, dass 36% der ED-Patienten Anonymitaet als Schluesselfaktor nennen (PMC 2020)
- **Rx-OTC-Konsistenz:** Rx-Rueckgang wird **abgeleitet** aus der OTC-Migration, nicht unabhaengig gesetzt -- Tabletten/Patienten koennen nicht gleichzeitig in beiden Pools existieren
- **Rx-Herstellerpreisbildung:** Sowohl Rx- als auch OTC-Umsatz verwenden Ab-Werk-Umsatz (Herstellerumsatz) fuer Konsistenz, mit `rx_manufacturer_share = 52%`
- **Marken- vs. Generika-OTC:** Viagra Connect Anteilserosion mit Preisaufschlag, proportional auf Kanaele verteilt
- **Tadalafil-Wettbewerbsgraben:** Cialis/Tadalafil bleibt verschreibungspflichtig; einige Patienten migrieren zum bequemen OTC-Sildenafil
- **Schliessung der Behandlungsluecke:** Neue OTC-Patienten erhoehen die effektive Therapierate -- abgeleitet aus tatsaechlichen Patientenvolumina, nicht unabhaengig gesetzt
- **Marketing-Taper:** Gradueller 6-monatiger linearer Uebergang vom Launch-Budget zur Erhaltung (keine Stufenfunktion)
- **Profitabilitaets-KPIs:** Break-even-Monat, Marketing-ROI (5J), separates Rx/OTC-Rohertragstracking

**Wesentliche Modellmerkmale:**
- Dual-Channel Rx/OTC mit migrationsbasiertem Rx-Rueckgang (keine Doppelzaehlung)
- Logistische S-Kurve fuer OTC-Anlauf und Tadalafil-Migration
- Saisonalitaet (Valentinstag, Sommer-Peak; Herbst/Winter-Tief)
- Preiselastizitaet mit jaehrlicher Verbunderosion durch Generikawettbewerb
- Patientenbasiertes Modell ergaenzt: Rx-Migrationsobergrenze (kann Rx-Pool nicht uebersteigen), explizite Patienten-Funnel-Tabelle
- Drei Szenarien: Konservativ (SVA-Auflagen) / Base Case / Optimistisch (BMG erzwingt Switch)

**Eingearbeitete Realweltdaten:**
- ~5 Mio. Maenner mit maessiger bis vollstaendiger ED in Deutschland, nur ~30% behandelt (Braun et al. 2000; May et al. 2007; Arnold 2023)
- UK Viagra Connect: 63% therapie-naive Patienten (Lee et al. 2021, n=1.162)
- BfArM SVA lehnte OTC-Switch 3x ab (2022, 2023, 2025), aber BMG unterstuetzt ihn oeffentlich
- Generika-Rx: EUR 0,95-2,30/Tablette; Viagra Marke: EUR 8-14/Tablette
- Online-Apotheke OTC-Anteil: ~23% allgemein, ~45%+ fuer Stigma-Kategorien (ABDA 2024, ecommercegermany.com)
- PMC/Kantar (2020, n=11.456): 36% der ED-Patienten nennen Diskretion/Scham als Treiber fuer den Online-Kauf

## Use Case 5: Eye Care Franchise -- Ophthalmologie-Portfolio

**Frage:** Wie sollte ein Spezial-Pharma-Unternehmen drei Ophthalmologie-Produkte sequenziell auf den deutschen Markt bringen?

Modelliert sequenziellen Markteintritt mit gemeinsamem Aussendienst, AMNOG-Preislebenszyklus und produktuebergreifenden Synergien. Basierend auf realen Pipeline-Assets (Oyster Point, Famy Life Sciences Akquisitionen).

**Produktportfolio:**

| Produkt | Indikation | Launch | Phase | Besonderheit |
|---|---|---|---|---|
| RYZUMVI (Phentolamin) | Mydriasis-Umkehr | Monat 1 | FDA-zugelassen | First-in-Class DE, Pro-Prozedur-Preisgestaltung |
| MR-141 (Phentolamin) | Presbyopie | Monat 18 | Phase III | 15 Mio. anspruchsberechtigte Patienten, Lifestyle-nah |
| Tyrvaya (Vareniclin) | Trockenes Auge | Monat 42 | FDA-zugelassen, kein EMA-Filing | Groesster Markt (EUR 430 Mio.), neuartiger MOA |

**Was dieses Modell besonders macht:**
- **Sequenzieller Portfolio-Launch:** Drei Produkte zu unterschiedlichen Zeitpunkten, aufbauend auf gemeinsamer Infrastruktur
- **AMNOG-Preislebenszyklus:** Freie Preisgestaltung (6 Monate) -> G-BA Nutzenbewertung -> Verhandelter Erstattungsbetrag -> Jaehrliche Erosion
- **Facharzt-Adoptions-S-Kurve:** Logistische Diffusion ueber 6.600+ GKV-Ophthalmologen
- **Aussendienstskalierung mit Synergien:** P2-Launch kostet 70%, P3 kostet 60% der Standalone-Kosten (gemeinsame Reps, KOLs, Kongresspraesenz)
- **MVZ-Kanalwachstum:** Modellierung des Konsolidierungstrends in ophthalmologischen Praxen (+8% p.a.)
- **Wettbewerbsdynamik:** iKervis (Santen), Vevizye (Novaliq/Thea), Vuity (AbbVie), OTC kuenstliche Traenen

**Wesentliche Modellmerkmale:**
- Pro-Produkt-Patientenvolumen, Verordneradoption, Marktanteil und Preiskurven
- Portfolio-GuV: Umsatzzerlegung nach Produkt, kumulierter Gewinn, ROI-Tracking
- GTM-Investitionen: Aussendienst, MSLs, Marketing, Kongresse, KOL-Programme, digitale Kanaele
- Drei Szenarien: Base Case / Aggressiv (schneller Aufbau) / Konservativ (Tyrvaya verzoegert)

**Eingearbeitete Realweltdaten:**
- 8.250+ Augenärzte in Deutschland, 6.600 GKV-Vertragsaerzte (KBV 2024)
- Trockenes Auge: ~10 Mio. betroffen, 1,5-1,9 Mio. diagnostiziert, nur 36% erhalten Rx
- Markt trockenes Auge DE: ~EUR 430 Mio. (Rx+OTC), CAGR 5,7% (Grand View Research)
- iKervis (Santen): EUR 120-135/Monat, nur schwere Keratitis
- Vevizye (Novaliq/Thea): EU-zugelassen Okt. 2024, maessige bis schwere DED
- RYZUMVI FDA-zugelassen Aug. 2023, Tyrvaya FDA-zugelassen Okt. 2021
- Oeffentliche Pipeline- und Investor-Relations-Daten

## Excel-Modelle

Vorgefertigte Excel-Arbeitsmappen sind in [`exports/`](exports/) zum direkten Download enthalten. Jede hat professionell formatierte Blaetter:

1. **INPUTS** - Alle Parameter in bearbeitbaren gelben Zellen
2. **Marktdaten** - Wettbewerbslandschaft und Marktkontext
3. **Forecast** - Monatliche Prognose mit vollstaendiger Datentabelle + eingebetteten Diagrammen
4. **Dashboard** - Executive Summary mit Szenarienvergleich
5. **Methodik** - Transparenzmatrix, die jeden Datenpunkt als FAKT / ANNAHME / MODELL / LUECKE klassifiziert

| Datei | Use Case | Blaetter |
|---|---|---|
| [`Eliquis_Launch_Forecast_v2.xlsx`](exports/Eliquis_Launch_Forecast_v2.xlsx) | Generika-Eintritt | 6 |
| [`GLP1_Brand_Competition_Forecast.xlsx`](exports/GLP1_Brand_Competition_Forecast.xlsx) | Markenwettbewerb | 6 |
| [`RxToOTC_Switch_Forecast.xlsx`](exports/RxToOTC_Switch_Forecast.xlsx) | Rx-to-OTC Switch (PPI) | 5 |
| [`Sildenafil_OTC_Switch_Forecast.xlsx`](exports/Sildenafil_OTC_Switch_Forecast.xlsx) | Sildenafil OTC (Omnichannel) | 6 |
| [`Ophthalmology_Portfolio_Forecast.xlsx`](exports/Ophthalmology_Portfolio_Forecast.xlsx) | Eye Care Franchise | 6 |

Regenerieren Sie sie nach Parameteraenderungen:

```bash
python exports/build_excel_model.py         # Eliquis
python exports/build_glp1_excel.py          # GLP-1
python exports/build_rx_otc_excel.py        # Rx-to-OTC (PPI)
python exports/build_sildenafil_excel.py    # Sildenafil OTC
python exports/build_ophthalmology_excel.py # Ophthalmologie-Portfolio
```

## Erste Schritte

```bash
# Klonen
git clone https://github.com/leelesemann-sys/pharma-launch-forecast.git
cd pharma-launch-forecast

# Abhaengigkeiten installieren
pip install -r requirements.txt

# Multi-Page-App starten (alle 5 Use Cases)
streamlit run app/app.py
```

## Datenhinweis

Alle Daten sind synthetisch und basieren auf oeffentlich zugaenglichen Quellen:

- BARMER Gesundheitswesen aktuell 2025
- G-BA Nutzenbewertung (Tirzepatid, Semaglutid)
- IQVIA Pharmamarkt Deutschland (oeffentliche Zusammenfassungen)
- EMA European Public Assessment Reports
- GKV-Arzneimittelindex, Lauer-Taxe (oeffentliche Preise)
- BfArM Sachverstaendigenausschuss-Protokolle (Sildenafil OTC-Entscheidungen)
- MHRA / PAGB Frontier Economics (UK Viagra Connect Auswirkungen)
- PMC Lee et al. 2021 (UK Real-World-Studie, n=1.162)
- Cologne Male Survey (Braun et al., Nature)
- Oeffentliche Investor-Relations- und Pipeline-Veroeffentlichungen
- FDA/EMA European Public Assessment Reports (RYZUMVI, Tyrvaya, Vevizye)
- KBV/BAeK Aerztestatistik 2024 (Ophthalmologische Belegschaft)
- Grand View Research (DE Markt trockenes Auge)
- Santen (iKervis Preise), Novaliq/Thea (Vevizye EU-Zulassung)

Keine proprietaeren IQVIA-Daten, keine vertraulichen Unternehmensdaten. Die Modelle dienen der Demonstration von Prognosemethodik, nicht der Anlageberatung.

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Interaktive Dashboards
- **Plotly** - Diagramme (Doppelachse, gestapelte Flaechen, gruppierte Balken)
- **XlsxWriter** - Professionelle Excel-Generierung mit Formatierung und eingebetteten Diagrammen
- **Pandas / NumPy** - Datenverarbeitung und mathematische Modelle

## Lizenz

MIT
