# Pool Water Balance - Design Specification

**Datum:** 2026-06-30
**Sprache:** Deutsch (UI-Texte)
**Architektur:** Multi-page Streamlit App mit DevContainer

---

## 1. Projektübersicht

Interaktive Web-Anwendung zur Berechnung und Überwachung des Wasserhaushalts von Schwimmbädern. Unterstützt Chlor-, Salzwasser- und alternative Desinfektionssysteme. Berechnungen basieren auf LSI (Langelier Saturation Index) und RSI (Ryznar Stability Index).

---

## 2. Architektur

### 2.1 Technologie-Stack
- **Frontend:** Streamlit (Multi-page App via `pages/` Verzeichnis)
- **Backend/Logik:** Python-Modul `pool_calculations/` (unabhängig testbar)
- **Datenbank:** SQLite mit SQLAlchemy ORM
- **Visualisierung:** Plotly (interaktive Charts)
- **Bildverarbeitung:** Pillow
- **Entwicklung:** VS Code DevContainer (Python 3.11+)

### 2.2 Verzeichnisstruktur
```
pool-water-balance/
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── app.py                      # Entry Point (Dashboard)
├── pages/
│   ├── 1_Wasserrechner.py      # LSI/RSI Berechnung
│   ├── 2_Dosierung.py          # Chemikalien-Dosierung
│   ├── 3_Verlauf.py            # Historie & Trends
│   ├── 4_Wartung.py            # Wartungsplan
│   └── 5_Fotos.py              # Foto-Dokumentation
├── pool_calculations/
│   ├── __init__.py
│   ├── lsi.py                  # LSI Berechnung
│   ├── rsi.py                  # RSI Berechnung
│   ├── dosing.py               # Dosierberechnungen
│   └── models.py               # Dataclasses/Enums
├── database/
│   ├── __init__.py
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
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 3. Datenmodell (SQLite)

### 3.1 `pool_configs`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| name | TEXT | Pool-Name (z. B. "Hauptpool") |
| volume_liter | REAL | Wasservolumen in Litern |
| pool_type | TEXT | 'chlorine', 'salt', 'alternative' |
| target_ph_min | REAL | Ziel-pH Minimum (Standard: 7.2) |
| target_ph_max | REAL | Ziel-pH Maximum (Standard: 7.6) |
| target_chlorine_min | REAL | Ziel-Chlor Minimum (mg/L) |
| target_chlorine_max | REAL | Ziel-Chlor Maximum (mg/L) |
| target_alkalinity_min | REAL | Ziel-Alkalinität Minimum (mg/L CaCO₃) |
| target_alkalinity_max | REAL | Ziel-Alkalinität Maximum (mg/L CaCO₃) |
| target_hardness_min | REAL | Ziel-Härte Minimum (mg/L CaCO₃) |
| target_hardness_max | REAL | Ziel-Härte Maximum (mg/L CaCO₃) |
| created_at | TIMESTAMP | Erstellungsdatum |

### 3.2 `readings`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| pool_id | INTEGER FK | Referenz auf pool_configs |
| timestamp | TIMESTAMP | Messzeitpunkt |
| ph | REAL | pH-Wert |
| chlorine_free | REAL | Freies Chlor (mg/L) |
| chlorine_total | REAL | Gesamtchlor (mg/L) |
| alkalinity | REAL | Alkalinität (mg/L CaCO₃) |
| hardness | REAL | Calciumhärte (mg/L CaCO₃) |
| temperature_c | REAL | Wassertemperatur (°C) |
| cyanuric_acid | REAL | Zyanursäure (mg/L) |
| salt_ppm | REAL | Salzgehalt (ppm) |
| lsi_value | REAL | Berechneter LSI |
| rsi_value | REAL | Berechneter RSI |
| notes | TEXT | Notizen |

### 3.3 `maintenance_tasks`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| pool_id | INTEGER FK | Referenz auf pool_configs |
| task_type | TEXT | 'filter_clean', 'backwash', 'chemical_check', 'equipment_check', 'custom' |
| title | TEXT | Aufgaben-Titel |
| description | TEXT | Beschreibung |
| due_date | DATE | Fälligkeitsdatum |
| interval_days | INTEGER | Wiederholungsintervall (0 = einmalig) |
| completed | BOOLEAN | Erledigt |
| completed_at | TIMESTAMP | Erledigungszeitpunkt |
| notes | TEXT | Notizen |

### 3.4 `photos`
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Eindeutige ID |
| pool_id | INTEGER FK | Referenz auf pool_configs |
| timestamp | TIMESTAMP | Aufnahmezeitpunkt |
| image_path | TEXT | Relativer Pfad zum Bild |
| caption | TEXT | Bildunterschrift |
| tags | TEXT | Komma-getrennte Tags |

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

### 4.3 Dosierberechnungen
Stöchiometrische Berechnungen pro Chemikalie:

| Chemikalie | Zweck | Formel (vereinfacht) |
|------------|-------|---------------------|
| pH-Heber (Na₂CO₃) | pH ↑ | g = (ΔpH × Vol × 0.74) / 1000 |
| pH-Senker (NaHSO₄) | pH ↓ | g = (ΔpH × Vol × 1.4) / 1000 |
| Chlor-Granulat (Ca(OCl)₂) | Chlor ↑ | g = (ΔCl × Vol) / (0.65 × 1000) |
| Flüssigchlor (NaOCl 12%) | Chlor ↑ | ml = (ΔCl × Vol) / (0.12 × 1000) |
| Alkalinitätsheber (NaHCO₃) | Alk ↑ | g = (ΔAlk × Vol × 1.5) / 1000 |
| Härteheber (CaCl₂) | Härte ↑ | g = (ΔHärte × Vol × 1.33) / 1000 |
| Zyanursäure | Stabilisator ↑ | g = (ΔCYA × Vol) / 1000 |
| Salz (NaCl) | Salzwasser-Pool | kg = (ΔSalt × Vol) / 1_000_000 |

*Hinweis: Exakte Faktoren hängen von Produktreinheit ab; Konfiguration über UI anpassbar.*

---

## 5. UI-Seiten (Deutsch)

### 5.1 Dashboard (`app.py`)
- Übersicht aller Pools mit aktuellem Status (LSI/RSI Ampel)
- Letzte Messwerte pro Pool
- Nächste fällige Wartungsaufgaben
- Schnellzugriff: Neue Messung erfassen

### 5.2 Wasserrechner (`pages/1_Wasserrechner.py`)
- Eingabeformular: pH, Chlor, Alkalinität, Härte, Temp, CYA, Salz
- Pool-Auswahl (Konfiguration)
- Live-Berechnung von LSI & RSI bei Eingabe
- Grafische Anzeige: LSI/RSI Skala mit Farbcodierung
- Empfehlung: "Wasser ist korrosiv / ausgeglichen / kalkausfällend"
- Speichern als Messwert in Historie

### 5.3 Dosierung (`pages/2_Dosierung.py`)
- Zielwerte eingeben (oder aus Pool-Config übernehmen)
- Aktuelle Werte aus letzter Messung laden
- Berechnung: Welche Chemikalien in welcher Menge?
- Ausgabe: Tabelle mit Chemikalie, Menge, Einheit, Hinweis
- Optional: Einkaufsliste exportieren (CSV/PDF)

### 5.4 Verlauf (`pages/3_Verlauf.py`)
- Pool-Auswahl
- Zeitreihen-Charts (Plotly): pH, Chlor, Alkalinität, Härte, LSI, RSI
- Filter: Zeitraum (Woche, Monat, Jahr, benutzerdefiniert)
- Tabellarische Ansicht aller Messwerte
- Export: CSV, JSON

### 5.5 Wartung (`pages/4_Wartung.py`)
- Liste aller Aufgaben (offen / erledigt / überfällig)
- Neue Aufgabe anlegen: Typ, Titel, Beschreibung, Fälligkeitsdatum, Intervall
- Aufgabe als erledigt markieren
- Automatische Wiederholung basierend auf Intervall
- Erinnerungen: Überfällige Aufgaben hervorheben

### 5.6 Fotos (`pages/5_Fotos.py`)
- Foto hochladen (Drag & Drop oder Dateiauswahl)
- Automatische Verkleinerung/Thumbnail (Pillow)
- Metadaten: Pool, Datum, Caption, Tags
- Galerie-Ansicht mit Filter (Pool, Tag, Zeitraum)
- Löschen von Fotos

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
- **UI Tests:** Playwright für kritische User Flows (optional, später)
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
python-dateutil>=2.8
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