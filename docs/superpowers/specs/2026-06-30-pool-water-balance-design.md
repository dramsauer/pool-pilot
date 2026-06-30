# Pool Water Balance - Design Specification

**Datum:** 2026-06-30
**Sprache:** Deutsch (UI-Texte)
**Architektur:** Multi-page Streamlit App mit DevContainer

---

## 1. Projektübersicht

Interaktive Web-Anwendung zur Berechnung und Überwachung des Wasserhaushalts für den eigenen Pool.

### 1.1 Pool-Konfiguration (Single-User, voreingestellt)
| Eigenschaft | Wert |
|-------------|------|
| **Pool** | Lay-Z-Spa Ibiza (Bestway) |
| **Maße** | 180 × 180 × 66 cm |
| **Wasservolumen** | ~1000 Liter (Standard-Einstellung, anpassbar) |
| **Pool-Typ** | Chlor (Trichlor-Tabletten) |

### 1.2 Eingesetzte Mittel
| Mittel | Produkt | Wirkstoff | Faktor |
|--------|---------|-----------|--------|
| **Chlor** | Summer Fun Perfect Care Tabs 20g | Trichlor (stabilisiert, ~90% av. Cl) | 1 Tablette = 18 g freies Chlor / 1000 L |
| **pH-Senker** | Summer Fun pH-Minus Granulat | NaHSO₄ (Natriumhydrogensulfat) | 1.4 g pro m³ pro 0.1 pH ↓ |
| **pH-Heber** | Summer Fun pH-Plus Granulat | Na₂CO₃ (Natriumcarbonat) | 0.74 g pro m³ pro 0.1 pH ↑ |

### 1.3 Teststreifen
- **Marke:** Summer Fun Wasserteststreifen (pH, Chlor, Brom)
- **Messbereiche:** pH (6.2–8.4), Chlor (0–10 mg/L), Brom (0–20 mg/L)

---

## 2. Architektur

### 2.1 Technologie-Stack
- **Frontend:** Streamlit (Multi-page App via `pages/` Verzeichnis)
- **Backend/Logik:** Python-Modul `pool_calculations/` (unabhängig testbar)
- **Datenbank:** SQLite mit SQLAlchemy ORM
- **Visualisierung:** Plotly (interaktive Charts)
- **Bildverarbeitung:** Pillow
- **Entwicklung:** VS Code DevContainer (Python 3.11+)

### 2.2 Single-User Ansatz
- Keine Multi-Pool-Verwaltung (fester Pool "Lay-Z-Spa Ibiza" voreingestellt)
- Pool-Daten in `config.toml` statt in DB-Tabelle
- Messwerte & Historie in SQLite
- Vereinfachtes Datenmodell (keine Pool-Konfig-Tabelle nötig)

### 2.3 Verzeichnisstruktur
```
pool-water-balance/
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── app.py                      # Streamlit Start (Dashboard)
├── pages/
│   ├── 1_Wasserrechner.py      # LSI/RSI + Dosierung in einer Seite
│   ├── 2_Verlauf.py            # Historie & Trends
│   ├── 3_Wartung.py            # Wartungsplan
│   └── 4_Fotos.py              # Foto-Dokumentation
├── pool_calculations/
│   ├── __init__.py
│   ├── lsi.py                  # LSI Berechnung
│   ├── rsi.py                  # RSI Berechnung
│   ├── dosing.py               # Dosierberechnungen
│   └── models.py               # Dataclasses/Enums
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite Setup + SQLAlchemy Engine
│   ├── models.py               # SQLAlchemy Models
│   └── repository.py           # Data Access Layer
├── utils/
│   ├── __init__.py
│   └── helpers.py              # Formatierung, Validierung
├── tests/
│   ├── test_lsi.py
│   ├── test_rsi.py
│   ├── test_dosing.py
│   └── test_database.py
├── config.toml                 # Pool-Konfiguration
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 3. Datenmodell (SQLite)

Keine Pool-Konfiguration in DB (Single-User, Config via `config.toml`).

### 3.1 `readings`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| timestamp | TIMESTAMP | Messzeitpunkt |
| ph | REAL | pH-Wert |
| chlorine | REAL | Freies Chlor (mg/L) |
| alkalinity | REAL | Alkalinität (mg/L CaCO₃) |
| hardness | REAL | Calciumhärte (mg/L CaCO₃) |
| temperature_c | REAL | Wassertemperatur (°C) |
| lsi_value | REAL | Berechneter LSI |
| rsi_value | REAL | Berechneter RSI |
| dosing_recommendation | TEXT | JSON: empfohlene Dosierung |
| notes | TEXT | Notizen |

### 3.2 `maintenance_tasks`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| task_type | TEXT | 'wasserwechsel', 'filter_reinigen', 'chemie_pruefen', 'custom' |
| title | TEXT | Aufgaben-Titel |
| description | TEXT | Beschreibung |
| due_date | DATE | Fälligkeitsdatum |
| interval_days | INTEGER | Wiederholungsintervall (0 = einmalig) |
| completed | BOOLEAN | Erledigt |
| completed_at | TIMESTAMP | Erledigungszeitpunkt |

### 3.3 `photos`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| timestamp | TIMESTAMP | Aufnahmezeitpunkt |
| image_path | TEXT | Relativer Pfad zum Bild |
| caption | TEXT | Bildunterschrift |

### 3.4 `config.toml` (keine DB-Tabelle)
```toml
[pool]
name = "Lay-Z-Spa Ibiza"
volume_liter = 1000
pool_type = "chlorine"

[targets]
ph_min = 7.2
ph_max = 7.6
chlorine_min = 0.5
chlorine_max = 3.0
alkalinity_min = 80
alkalinity_max = 120
hardness_min = 150
hardness_max = 250
temperature_default = 35

[products]
  [products.ph_minus]
  name = "Summer Fun pH-Minus Granulat"
  factor = 1.4
  unit = "g"

  [products.ph_plus]
  name = "Summer Fun pH-Plus Granulat"
  factor = 0.74
  unit = "g"

  [products.chlorine_tabs]
  name = "Summer Fun Perfect Care Tabs 20g"
  active_chlorine_per_tab = 18.0
  unit = "Tabletten"
```

---

## 4. Berechnungslogik

### 4.1 LSI (Langelier Saturation Index)
```
LSI = pH + TF + CF + AF - 12.1

TF (Temperatur-Faktor):     Basiert auf Wassertemperatur (°C)
CF (Calcium-Faktor):        Basiert auf Calciumhärte (mg/L CaCO₃)
AF (Alkalinitäts-Faktor):   Basiert auf Gesamtalkalinität (mg/L CaCO₃)
```

**Interpretation:**
- LSI < -0.5: Korrosiv (Unterschutz)
- -0.5 ≤ LSI ≤ +0.5: Ausgeglichen (Ideal)
- LSI > +0.5: Neigt zu Ausfällungen/Kalk

### 4.2 RSI (Ryznar Stability Index)
```
pHs = (9.3 + A + B) - (C + D)  (Sättigungs-pH)
RSI = 2 × pHs - pH

A = (log10(TDS) - 1) / 10
B = -13.12 × log10(°C + 273) + 34.55
C = log10(CaH) - 0.4
D = log10(Alk)
```

**Interpretation:**
- RSI < 6.0: Stark kalkausfällend
- 6.0–7.0: Leicht kalkausfällend
- 7.0–7.5: Stabil
- 7.5–8.5: Leicht korrosiv
- > 8.5: Stark korrosiv

### 4.3 Dosierberechnungen (produktspezifisch)

| Produkt | Wirkung | Formel |
|---------|---------|--------|
| **pH-Minus Granulat** (NaHSO₄) | pH senken | `g = (aktueller_pH - ziel_pH) × volumen_m³ × 1.4` |
| **pH-Plus Granulat** (Na₂CO₃) | pH heben | `g = (ziel_pH - aktueller_pH) × volumen_m³ × 0.74` |
| **Perfect Care Tabs 20g** | Chlor erhöhen | `tabletten = ceil((ziel_Cl - aktuelles_Cl) × volumen_m³ / 18.0)` |

**Beispiel (1000L / 1 m³):**
- pH 6.8 → Ziel 7.4: `(7.4 - 6.8) × 1 × 0.74 = 0.44 g` pH-Plus Granulat
- pH 8.0 → Ziel 7.4: `(8.0 - 7.4) × 1 × 1.4 = 0.84 g` pH-Minus Granulat
- Chlor 0 → Ziel 1.5: `ceil(1.5 × 1 / 18.0) = 1` Tablette

*Hinweis: Faktoren sind produktspezifisch und in `config.toml` einstellbar.*

---

## 5. UI-Seiten (Deutsch)

### 5.1 Dashboard (`app.py`)
- Pool-Info (Name, Volumen, aktueller Status)
- Letzte Messwerte (aus DB)
- Wasserbalance-Ampel (LSI/RSI) auf Basis der letzten Messung
- Nächste fällige Wartungsaufgaben
- Schnellzugriff: "Neue Messung" Button

### 5.2 Wasserrechner + Dosierung (`pages/1_Wasserrechner.py`)
- **Eingabeformular:** pH, Chlor, Alkalinität, Härte, Temperatur (Slider/Numpad)
- **Live-Berechnung von LSI & RSI** bei jeder Eingabeänderung
- **Grafik:** Farbige LSI/RSI-Skala mit Zeigerposition
- **Bewertung:** "Wasser ist korrosiv / ausgeglichen / kalkausfällend" (farblich)
- **Dosierempfehlung:** Tabelle mit Chemikalie, Menge, Einheit
  - pH zu niedrig → pH-Plus Granulat (X g)
  - pH zu hoch → pH-Minus Granulat (X g)
  - Chlor zu niedrig → ¼/½/1 Tablette(n) Perfect Care Tabs
  - (Wenn alles OK: grüner Haken, "Wasser ist im Gleichgewicht")
- **Speichern:** Messwert + Dosierempfehlung in Historie übernehmen

### 5.3 Verlauf (`pages/2_Verlauf.py`)
- Zeitreihen-Charts (Plotly): pH, Chlor, LSI, RSI
- Filter: Zeitraum (letzte Woche, Monat, alles)
- Tabellarische Ansicht aller Messwerte
- Export als CSV

### 5.4 Wartung (`pages/3_Wartung.py`)
- Aufgabenliste: offen / erledigt / überfällig
- Aufgaben: Wasserwechsel alle 2-3 Tage, Filter reinigen, Chemie prüfen
- Neue Aufgabe anlegen, als erledigt markieren
- Automatische Wiederholung

### 5.5 Fotos (`pages/4_Fotos.py`)
- Foto hochladen (Kamera/Datei)
- Thumbnail-Galerie
- Bildunterschriften
- Bilder löschen

---

## 6. DevContainer Konfiguration

### 6.1 `.devcontainer/devcontainer.json`
```json
{
  "name": "Pool Water Balance",
  "build": { "dockerfile": "Dockerfile" },
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-python.pylance", "ms-toolsai.jupyter"]
    }
  },
  "forwardPorts": [8501],
  "postCreateCommand": "pip install -r requirements.txt",
  "remoteUser": "vscode"
}
```

### 6.2 `.devcontainer/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

---

## 7. Testing-Strategie

- **Unit Tests:** `pool_calculations/` Module (LSI, RSI, Dosing) - pytest
- **Integration Tests:** Database Repository CRUD Operationen
- **Coverage Ziel:** ≥ 80% für Berechnungslogik

---

## 8. Abhängigkeiten (`requirements.txt`)

```
streamlit>=1.35
sqlalchemy>=2.0
plotly>=5.20
pillow>=10.0
pandas>=2.1
pytest>=7.4
```

---

## 9. Nächste Schritte

1. Design Review & Freigabe durch User
2. Implementation Plan erstellen (writing-plans Skill)
3. Repository initialisieren, DevContainer einrichten
4. Datenbank-Modelle & Migrationen
5. Berechnungsmodul implementieren & testen
6. Streamlit Pages bauen
7. Integration & E2E-Test
8. Dokumentation (README, User Guide)

---

*Dieses Dokument dient als Basis für die Implementierung. Änderungen bedürfen der Abstimmung.*
