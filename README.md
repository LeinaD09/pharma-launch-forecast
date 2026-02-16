# Pharma Launch Forecast

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pharma-launch-forecasts.streamlit.app/)

Interactive forecast models for pharmaceutical product launches in Germany. Built with Python, Streamlit, and Plotly.

> **Live Demo:** [pharma-launch-forecasts.streamlit.app](https://pharma-launch-forecasts.streamlit.app/)

Five forecasting engines demonstrate the breadth of launch scenarios a Strategic Portfolio Manager faces:

| | Use Case 1 | Use Case 2 | Use Case 3 | Use Case 4a/4b | Use Case 5 |
|---|---|---|---|---|---|
| **Scenario** | Eliquis Generic Entry | GLP-1: Mounjaro vs. Ozempic | Rx-to-OTC Switch (PPI) | Sildenafil OTC Switch (2 Modelle) | Eye Care Franchise |
| **Type** | Generic vs. Originator | Brand vs. Brand | Dual Channel (Rx + OTC) | Omnichannel + Stigma-Markt | Sequential Portfolio Launch |
| **Market** | Mature, eroding | Expanding, high-growth | Channel transition | Stigma-driven, underserved | Specialty, fragmented |
| **Key Mechanic** | Aut-idem, Rabattvertraege | Indication layering, supply | Consumer awareness, pricing | Dual-Channel, Patienten-Funnel | AMNOG pricing, Facharzt adoption |
| **LOE** | May 2026 | n/a (patent protected) | n/a (OTC switch) | n/a (BfArM SVA pending) | n/a (pipeline launches) |
| **Pricing** | Festbetrag / generic erosion | AMNOG Erstattungsbetrag | Free OTC pricing | Brand vs. generic OTC | AMNOG 3-phase lifecycle |

## Screenshots

Run the apps locally to explore the interactive dashboards (see [Getting Started](#getting-started)).

## Architecture

```
pharma-launch-forecast/
├── models/
│   ├── forecast_engine.py           # Generic Entry engine (Eliquis)
│   ├── brand_competition_engine.py  # Brand Competition engine (GLP-1)
│   ├── rx_otc_engine.py             # Rx-to-OTC Switch engine (PPI)
│   ├── sildenafil_otc_engine.py     # Sildenafil OTC engine (volume-based)
│   ├── sildenafil_patient_engine.py # Sildenafil OTC engine (patient-based)
│   └── ophthalmology_engine.py     # Ophthalmology Portfolio engine (Eye Care Franchise)
├── app/
│   ├── app.py                       # Multi-page entry point (st.navigation)
│   ├── main.py                      # Page: Eliquis Generic Entry
│   ├── glp1.py                      # Page: GLP-1 Brand Competition
│   ├── rx_otc.py                    # Page: Rx-to-OTC Switch (PPI)
│   ├── sildenafil.py                # Page: Sildenafil OTC Switch (volume-based)
│   ├── sildenafil_patient.py        # Page: Sildenafil OTC Switch (patient-based)
│   └── ophthalmology.py             # Page: Eye Care Franchise
├── data/
│   ├── market_data.py               # NOAK/DOAK market data (synthetic)
│   └── glp1_market_data.py          # GLP-1 market data (synthetic)
├── exports/
│   ├── build_excel_model.py                    # Excel generator: Eliquis
│   ├── build_glp1_excel.py                     # Excel generator: GLP-1
│   ├── build_rx_otc_excel.py                   # Excel generator: Rx-to-OTC
│   ├── build_sildenafil_excel.py               # Excel generator: Sildenafil
│   └── build_ophthalmology_excel.py            # Excel generator: Ophthalmology
├── docs/
│   ├── Modell_Volumen.md             # Documentation: volume-based Sildenafil model
│   ├── Modell_Patient.md             # Documentation: patient-based Sildenafil model
│   ├── KNOWLEDGE_BASE.md             # Shared knowledge base
│   └── QUALITY_TESTS.md              # Quality test definitions
└── requirements.txt
```

## Use Case 1: Eliquis Generic Entry (May 2026)

**Question:** What happens when the #1 anticoagulant loses patent protection?

Two perspectives with independent parameter sets:

- **Originator (BMS/Pfizer):** Revenue-at-Risk quantification. Models market share erosion via exponential decay with configurable floor, authorized generic strategy, and price defense.
- **Generic Challenger:** Market opportunity sizing. Models uptake via logistic S-curve with a **decision cascade** that allocates volume by priority:

| Priority | Volume Source | Mechanism | Regulatory Basis |
|---|---|---|---|
| 1 (highest) | Tender | Krankenkasse multi-award contracts, reduced by aut-idem exclusion | Par.130a SGB V (Rabattvertraege) |
| 2 | Aut-idem | Pharmacy-level substitution (non-tender remainder) | SGB V Par.129 (mandatory generic substitution) |
| 3 | Organic | Physician switching, formulary listing (residual) | Standard market access |

**Key model features:**
- Decision cascade: Tender > Aut-idem > Organic (no double-counting)
- Tender volume adjusted for **aut-idem exclusion** (physician override) and **multi-award contracts** (3-4 partners per Kasse)
- Aut-idem ramp curve tied to Festbetrag (reference pricing) timeline
- Per-Kasse tender modeling (TK, BARMER, DAK, AOKs) with win probabilities and ramp
- Volume decomposition: organic vs. aut-idem vs. tender
- Originator price defense and authorized generic cannibalization
- **Analogie-Leitplanken:** Benchmark validation against published generic penetration data (Fischer & Stargardt 2016, GaBi Journal, Bayer Q-reports, PMC) with +/-15pp tolerance bands

## Use Case 2: GLP-1 Brand Competition

**Question:** Will Mounjaro overtake Ozempic in the German GLP-1 market?

Two perspectives with symmetric model structure:

- **Eli Lilly (Mounjaro/Tirzepatid):** Challenger gaining share with superior efficacy data
- **Novo Nordisk (Ozempic/Semaglutid):** Defending market leadership despite supply constraints

**Key model features:**
- Market expansion with logistic dampening (GLP-1 segment growing 25-36% p.a.)
- Indication multiplier system: T2D (base) + Obesity + CV risk + MASH/NASH
- Supply constraint modeling with capacity normalization timeline
- Scenario presets: Base Case, Bull (Lilly), Bull (Novo)
- AMNOG pricing with confidential reimbursement amounts

**Real-world data points incorporated:**
- 6.33M T2D patients in Germany, 13.9% on GLP-1 (BARMER 2025)
- Wegovy excluded from GKV coverage (G-BA June 2024: Lifestyle-Arzneimittel)
- Mounjaro: first-ever confidential Erstattungsbetrag in Germany (Aug 2025)
- Ozempic supply constraints since 2022

## Use Case 3: Rx-to-OTC Switch (PPI)

**Question:** What happens when a prescription drug becomes available over the counter?

Reference case: Omeprazol/Pantoprazol 20mg PPI switch in Germany (July 2009).

Two perspectives:

- **Manufacturer:** Dual-channel revenue modeling. Rx volume decays as OTC ramps up, but OTC reaches entirely new patients.
- **Market:** Category disruption. OTC launch cannibalized antacids and collapsed H2-antagonists.

**Key model features:**
- Dual-channel dynamics: Rx exponential decay + OTC logistic S-curve ramp
- Market expansion: 70% of OTC volume from genuinely new patients (never had Rx)
- Adjacent category cannibalization (antacids, H2-antagonists)
- Consumer awareness S-curve tied to marketing spend
- PPI-typical seasonality (GI complaints peak in autumn/winter)
- Price elasticity: patient pays 100% OTC (vs. GKV copay for Rx)
- Pharmacy margin structure: free OTC pricing vs. regulated Rx (AMPreisV)
- Three scenarios: Konservativ / Base Case / Optimistisch

**Real-world data points incorporated:**
- OTC market Germany 2024: EUR 10.15B (+7.1%, IQVIA)
- PPI OTC switch 2009: only ~3% of PPI volume moved to OTC (partial switch)
- 11.9% heartburn market expansion in year 1 post-switch
- Antacid cannibalization: -EUR 11M; H2-antagonists: -46%
- OTC PPI max 14 tablets/20mg per BfArM

## Use Case 4: Sildenafil Rx-to-OTC Switch (Viatris/Viagra)

**Question:** What is the commercial opportunity if Sildenafil becomes OTC in Germany?

Two complementary models with identical channel/pricing logic but different approaches to market sizing. Reference: UK Viagra Connect (OTC since March 2018).

### Model 4a: Volume-Based (`sildenafil_otc_engine.py`)

OTC peak volume is a **direct input** (tablets/month). Simple, fast for scenario analysis.

### Model 4b: Patient-Based (`sildenafil_patient_engine.py`)

OTC peak is **computed** from an epidemiological patient funnel (prevalence → treatment gap → addressable pool → patients × usage frequency). Best-practice approach for pharma launches.

> Both models converge to the same Base Case peak (~2.1M tablets/month) but via different paths. Detailed documentation: [`docs/Modell_Volumen.md`](docs/Modell_Volumen.md), [`docs/Modell_Patient.md`](docs/Modell_Patient.md).

**What makes these models unique:**
- **Dual-channel distribution:** Two pharmacy channels (stationaere Apotheke, Online-Apotheke) -- apothekenpflichtig, no Drogerie -- with time-dependent share evolution and channel-specific margin structures
- **Discretion effect:** Parametrized stigma-driven channel shift (baseline + sensitivity) reflecting that 36% of ED patients cite anonymity as key factor (PMC 2020)
- **Rx-OTC consistency:** Rx decline is **derived** from OTC migration, not set independently -- tablets/patients cannot exist in both pools simultaneously
- **Rx manufacturer pricing:** Both Rx and OTC revenue use ex-factory (manufacturer) revenue for consistency, with `rx_manufacturer_share = 52%`
- **Brand vs. generic OTC:** Viagra Connect share erosion with price premium, proportionally distributed across channels
- **Tadalafil competitive moat:** Cialis/Tadalafil remains Rx-only; some patients migrate to convenient OTC sildenafil
- **Treatment gap closure:** New OTC patients raise the effective therapy rate -- derived from actual patient volumes, not set independently
- **Marketing taper:** Gradual 6-month linear transition from launch budget to maintenance (not a step function)
- **Profitability KPIs:** Breakeven month, Marketing-ROI (5J), separate Rx/OTC gross profit tracking

**Key model features:**
- Dual-channel Rx/OTC with migration-based Rx decline (no double-counting)
- Logistic S-curve for OTC ramp and Tadalafil migration
- Seasonality (Valentine's, summer peak; autumn/winter trough)
- Price elasticity with compound annual erosion from generic competition
- Patient-based model adds: Rx migration cap (cannot exceed Rx pool), explicit patient funnel table
- Three scenarios: Konservativ (SVA-Auflagen) / Base Case / Optimistisch (BMG erzwingt Switch)

**Real-world data points incorporated:**
- ~5M men with moderate-to-complete ED in Germany, only ~30% treated (Braun et al. 2000; May et al. 2007; Arnold 2023)
- UK Viagra Connect: 63% new-to-therapy patients (Lee et al. 2021, n=1,162)
- BfArM SVA rejected OTC switch 3x (2022, 2023, 2025) but BMG publicly supports it
- Generic Rx: EUR 0.95-2.30/tablet; Viagra brand: EUR 8-14/tablet
- Online pharmacy OTC share: ~23% general, ~45%+ for stigma categories (ABDA 2024, ecommercegermany.com)
- PMC/Kantar (2020, n=11,456): 36% of ED patients cite discretion/shame as driver for online purchase

## Use Case 5: Eye Care Franchise – Ophthalmology Portfolio

**Question:** How should a specialty pharma company sequence three ophthalmology products into the German market?

Models sequential market entry with shared field force, AMNOG pricing lifecycle, and cross-product synergies. Based on real-world pipeline assets (Oyster Point, Famy Life Sciences acquisitions).

**Product Portfolio:**

| Product | Indication | Launch | Phase | Unique Aspect |
|---|---|---|---|---|
| RYZUMVI (phentolamine) | Mydriasis reversal | Month 1 | FDA-approved | First-in-class DE, per-procedure pricing |
| MR-141 (phentolamine) | Presbyopia | Month 18 | Phase III | 15M eligible patients, lifestyle-adjacent |
| Tyrvaya (varenicline) | Dry Eye Disease | Month 42 | FDA-approved, no EMA filing | Largest market (EUR 430M), novel MOA |

**What makes this model unique:**
- **Sequential portfolio launch:** Three products at different times, building on shared infrastructure
- **AMNOG pricing lifecycle:** Free pricing (6 months) → G-BA Nutzenbewertung → Negotiated Erstattungsbetrag → Annual erosion
- **Facharzt adoption S-curve:** Logistic diffusion across 6,600+ GKV ophthalmologists
- **Field force scaling with synergies:** P2 launch costs 70%, P3 costs 60% of standalone (shared reps, KOLs, congress presence)
- **MVZ channel growth:** Modeling the consolidation trend in ophthalmology practices (+8% p.a.)
- **Competitive dynamics:** iKervis (Santen), Vevizye (Novaliq/Thea), Vuity (AbbVie), OTC artificial tears

**Key model features:**
- Per-product patient volume, prescriber adoption, market share, and pricing curves
- Portfolio P&L: revenue decomposition by product, cumulative profit, ROI tracking
- GTM investment: sales reps, MSLs, marketing, congress, KOL programs, digital channels
- Three scenarios: Base Case / Aggressiv (schneller Aufbau) / Konservativ (Tyrvaya verzoegert)

**Real-world data points incorporated:**
- 8,250+ ophthalmologists in Germany, 6,600 GKV Vertragsaerzte (KBV 2024)
- Dry eye: ~10M affected, 1.5-1.9M diagnosed, only 36% get Rx
- Dry eye market DE: ~EUR 430M (Rx+OTC), CAGR 5.7% (Grand View Research)
- iKervis (Santen): EUR 120-135/month, severe keratitis only
- Vevizye (Novaliq/Thea): EU-approved Oct 2024, moderate-to-severe DED
- RYZUMVI FDA-approved Aug 2023, Tyrvaya FDA-approved Oct 2021
- Public pipeline and investor relations data

## Excel Models

Pre-built Excel workbooks are included in [`exports/`](exports/) for direct download. Each has professionally formatted sheets:

1. **INPUTS** - All parameters in editable yellow cells
2. **Marktdaten** - Competitive landscape and market context
3. **Forecast** - Monthly forecast with full data table + embedded charts
4. **Dashboard** - Executive summary with scenario comparison
5. **Methodik** - Transparency matrix classifying every data point as FAKT / ANNAHME / MODELL / LUECKE

| File | Use Case | Sheets |
|---|---|---|
| [`Eliquis_Launch_Forecast_v2.xlsx`](exports/Eliquis_Launch_Forecast_v2.xlsx) | Generic Entry | 6 |
| [`GLP1_Brand_Competition_Forecast.xlsx`](exports/GLP1_Brand_Competition_Forecast.xlsx) | Brand Competition | 6 |
| [`RxToOTC_Switch_Forecast.xlsx`](exports/RxToOTC_Switch_Forecast.xlsx) | Rx-to-OTC Switch (PPI) | 5 |
| [`Sildenafil_OTC_Switch_Forecast.xlsx`](exports/Sildenafil_OTC_Switch_Forecast.xlsx) | Sildenafil OTC (Omnichannel) | 6 |
| [`Ophthalmology_Portfolio_Forecast.xlsx`](exports/Ophthalmology_Portfolio_Forecast.xlsx) | Eye Care Franchise | 6 |

Regenerate them after modifying parameters:

```bash
python exports/build_excel_model.py         # Eliquis
python exports/build_glp1_excel.py          # GLP-1
python exports/build_rx_otc_excel.py        # Rx-to-OTC (PPI)
python exports/build_sildenafil_excel.py    # Sildenafil OTC
python exports/build_ophthalmology_excel.py # Ophthalmology Portfolio
```

## Getting Started

```bash
# Clone
git clone https://github.com/leelesemann-sys/pharma-launch-forecast.git
cd pharma-launch-forecast

# Install dependencies
pip install -r requirements.txt

# Run multi-page app (all 5 use cases)
streamlit run app/app.py
```

## Data Disclaimer

All data is synthetic and based on publicly available sources:

- BARMER Gesundheitswesen aktuell 2025
- G-BA Nutzenbewertung (Tirzepatid, Semaglutid)
- IQVIA Pharmamarkt Deutschland (public summaries)
- EMA European Public Assessment Reports
- GKV-Arzneimittelindex, Lauer-Taxe (public pricing)
- BfArM Sachverstaendigenausschuss protocols (Sildenafil OTC decisions)
- MHRA / PAGB Frontier Economics (UK Viagra Connect impact)
- PMC Lee et al. 2021 (UK real-world study, n=1,162)
- Cologne Male Survey (Braun et al., Nature)
- Public investor relations and pipeline disclosures
- FDA/EMA European Public Assessment Reports (RYZUMVI, Tyrvaya, Vevizye)
- KBV/BAeK Aerztestatistik 2024 (ophthalmology workforce)
- Grand View Research (DE dry eye market)
- Santen (iKervis pricing), Novaliq/Thea (Vevizye EU approval)

No proprietary IQVIA data, no confidential company data. The models are designed to demonstrate forecasting methodology, not to provide investment advice.

## Tech Stack

- **Python 3.10+**
- **Streamlit** - Interactive dashboards
- **Plotly** - Charts (dual-axis, stacked areas, grouped bars)
- **XlsxWriter** - Professional Excel generation with formatting and embedded charts
- **Pandas / NumPy** - Data processing and mathematical models

## License

MIT
