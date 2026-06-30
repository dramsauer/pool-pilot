# Pool Water Balance — Redesign: Workflow-gesteuerte App

## Motivation

Die App wurde prototypisch aufgesetzt, bildet aber nicht den realen Workflow ab:
Teststreifen-Messung → Auswertung → Aktion → Dokumentation.  Zudem fehlen
Pool-Verwaltung (Multi-Pool), Produktverwaltung und Trinkwasser-Konfiguration.

Dieses Spec beschreibt den Umbau auf einen **durchgehenden, workflow-gesteuerten
Ablauf** mit der Wasserrechner-Seite als zentralem Einstiegspunkt.

## Seiten-Struktur (neu)

| Route | Titel | Zweck |
|---|---|---|
| `app.py` | 💧 Wasserrechner | Workflow: Messen → Berechnen → Aufgabe → Dokumentieren |
| `pages/01_Poolverwaltung.py` | 🏊 Pools & Produkte | Pools, Trinkwasser-Quellen, Produkte verwalten |
| `pages/02_Verlauf.py` | 📈 Verlauf | Chart-Historie + CSV-Export (wie bisher) |
| `pages/03_Wartung.py` | ✅ Aufgaben | Alle offenen/fälligen Aufgaben anzeigen/erledigen |

Die bisherige Dashboard-Seite (`app.py` alt) entfällt.

## Workflow in `app.py` (Live, kein Submit-Button)

```
┌─ Pool: [Lay-Z-Spa Ibiza ▼] ─────────────────────────┐
│                                                        │
│  ┌── Messwerte ───────────────────────────────────┐   │
│  │ pH:       [====●==========] 7,2    ⓘ          │   │
│  │ Chlor:    [=====●=========] 1,0 mg/L  ⓘ      │   │
│  │ Temp:     [======●========] 28°C              │   │
│  │ Alka:     [========●======] 145 mg/L (ⓘ)     │   │
│  │ Härte:    [========●======] 185 mg/L (ⓘ)     │   │
│  │ 📷 [📁 Hochladen] [📸 Kamera]                 │   │
│  │ 📝 Notizen (optional)                          │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌── Wasserbalance ──────────────────────────────┐   │
│  │  📊 [Plotly Gauge: LSI] + [Text-Ampel pH/Chlor]│   │
│  │  LSI: +0,3 (✅ ausgeglichen)                    │   │
│  │  RSI: 6,8 (✅ neutral)                          │   │
│  │  pH 7,2 ✅ | Chlor 1,0 ⚠️ niedrig              │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌── Empfehlung & Aktion ────────────────────────┐   │
│  │  ⚠️ Chlor zu niedrig (1,0 → Ziel min. 1,5)    │   │
│  │  → 1× Summer Fun Perfect Care Tabs 20g        │   │
│  │                                                 │   │
│  │  [📋 Aufgabe erzeugen] [✅ Erledigt melden]    │   │
│  │                                                 │   │
│  │  ┌── Ausführung dokumentieren ─────────────┐   │   │
│  │  │  "1 Tablette eingelegt um 14:30"        │   │   │
│  │  │  ✅ Aufgabe erledigt am 30.06.2026      │   │   │
│  │  │  🔄 Folgeaufgabe in 7 Tagen (vom         │   │   │
│  │  │     Produkt vorgegeben)                  │   │   │
│  │  └─────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  [💾 Messung speichern]                                │
└────────────────────────────────────────────────────────┘
```

**Live-Verhalten:** Jede Slider-Änderung feuert Neuberechnung von LSI, RSI,
Dosierempfehlung.  Plotly-Gauge + Textanzeige aktualisieren sofort.  Kein
"Berechnen"-Button.

**Speichern:** Nur bei Klick auf "💾 Messung speichern" wird der gesamte
Datensatz (Messwerte, Foto-Ref, Aufgaben-IDs) persistiert.

## Datenbank-Modell

### Tabelle: `pools` (NEU)

| Spalte | Typ | Default | Beschreibung |
|---|---|---|---|
| id | Integer PK | auto | |
| name | String(200) | | Pool-Name (z. B. "Lay-Z-Spa Ibiza") |
| volume_liter | Float | | Wasservolumen |
| pool_type | String(20) | "chlorine" | chlorine / bromine |
| ph_min | Float | 7.2 | Zielbereich min |
| ph_max | Float | 7.6 | Zielbereich max |
| chlorine_min | Float | 0.5 | |
| chlorine_max | Float | 3.0 | |
| alkalinity_min | Float | 80 | |
| alkalinity_max | Float | 120 | |
| hardness_min | Float | 150 | |
| hardness_max | Float | 250 | |
| temperature_default | Float | 35 | |
| trinkwasser_id | Integer FK → trinkwasser.id | NULL | Optional verknüpfte Quelle |
| created_at | DateTime | now | |

### Tabelle: `trinkwasser` (NEU)

| Spalte | Typ | Default | Beschreibung |
|---|---|---|---|
| id | Integer PK | auto | |
| name | String(200) | | Quellenname (z. B. "Stamsried – Kreiswerke Cham") |
| ph_default | Float | 7.5 | Typischer pH |
| alkalinity_default | Float | 145 | mg/L als CaCO₃ |
| calcium_hardness_default | Float | 185 | mg/L als CaCO₃ |
| notes | Text | | Z. B. "Stand 03/2025" |

### Tabelle: `products` (NEU — aus config.toml migriert)

| Spalte | Typ | Default | Beschreibung |
|---|---|---|---|
| id | Integer PK | auto | |
| name | String(200) | | Produktname |
| typ | String(20) | | ph_minus / ph_plus / chlorine |
| dosage_factor | Float | 0 | g pro 0,1 pH-Delta pro m³ |
| unit | String(20) | "g" | g / Tabletten |
| active_chlorine_per_tab | Float | NULL | Nur für Chlor: mg aktives Chlor pro Tablette |
| interval_days | Integer | 0 | 0 = einmalig, 7 = wöchentlich wiederholend |
| notes | Text | | |

### Tabelle: `readings` (erweitert)

| Spalte | Änderung |
|---|---|
| + pool_id | Integer FK → pools.id, NOT NULL |
| + photo_id | Integer FK → photos.id, NULL (optional) |

Bestehende Spalten bleiben unverändert.

### Tabelle: `photos` (erweitert)

| Spalte | Änderung |
|---|---|
| + reading_id | Integer FK → readings.id, NULL |
| + image_data | LargeBinary, NULL (für eingebettete Kamera-Bilder) |

### Tabelle: `maintenance_tasks` (erweitert)

| Spalte | Änderung |
|---|---|
| + pool_id | Integer FK → pools.id |
| + reading_id | Integer FK → readings.id, NULL |
| + product_id | Integer FK → products.id, NULL |
| + parent_task_id | Integer FK → maintenance_tasks.id, NULL (für Folgeaufgaben) |
| + executed_at | DateTime, NULL |
| + executed_notes | Text, NULL |
| + follow_up_days | Integer, default 0 |

## Datenmigration (config.toml → DB)

Beim ersten Start nach dem Umbau:

1. Lies `config.toml`
2. Erstelle Standard-Trinkwasser-Quelle "Stamsried – Kreiswerke Cham (03/2025)"
   mit den recherchierten Werten (pH=7.5, Alka=145, Härte=185)
3. Erstelle Pool "Lay-Z-Spa Ibiza" (1000 L, Chlor) mit Zielwerten aus config.toml,
   verknüpft mit Trinkwasser-Quelle
4. Erstelle Produkte:
   - "Summer Fun pH-Minus Granulat" (Typ: ph_minus, Faktor: 1.4, Einheit: g)
   - "Summer Fun pH-Plus Granulat" (Typ: ph_plus, Faktor: 0.74, Einheit: g)
   - "Summer Fun Perfect Care Tabs 20g" (Typ: chlorine, 18mg Cl/Tablette,
     Intervall: 7 Tage)

Nach der Migration wird `config.toml` nicht mehr für Pool-/Produktdaten
verwendet (nur noch als Fallback).

## Pool-Verwaltungs-Seite (`01_Poolverwaltung.py`)

Drei Bereiche via `st.tabs()`:

### Tab 1: Pools
- Liste aller Pools mit Name + Volumen
- Neu anlegen / Bearbeiten / Löschen
- Pro Pool: Name, Volumen, Typ, Zielbereiche
- Trinkwasser-Quelle zuweisen (Dropdown über alle Quellen)
- "Als Standard setzen" (wird beim Workflow vorausgewählt)

### Tab 2: Trinkwasser
- Liste aller Quellen
- Neu anlegen mit Defaults (Stamsried-Werte vorausgefüllt)
- pH, Alkalinität, Calciumhärte + Notizen

### Tab 3: Produkte
- Liste aller Produkte
- Neu / Bearbeiten / Löschen
- Mit Hilfetexten für jeden Parameter

## Aufgaben-Seite (`03_Wartung.py`)

- Filter nach Pool (Dropdown, falls mehrere)
- Aufgabenliste gruppiert: Überfällig (🔴) → Heute (🟡) → Diese Woche (🟢)
- Pro Aufgabe: Titel, Pool, fällig seit, verknüpfte Messung, verknüpftes Produkt
- "Erledigt" mit Dokumentations-Textfeld: "100g pH-Minus zugegeben"
- Wenn Produkt ein Intervall hat: automatisch Folgeaufgabe erzeugen

## Änderungen an Berechnungslogik

- `pool_calculations/dosing.py`: Produkte nicht mehr hardcoded, sondern aus
  `products`-Tabelle lesen → Dosierungslogik bleibt gleich
- `models.py`: PoolConfig, WaterTest, DosingRecommendation bleiben, aber
  `PoolConfig` wird aus DB-Pool-Eintrag befüllt (statt config.toml)

## UI-Komponenten (Hilfetexte)

Jeder Parameter in der Mess-Eingabe bekommt ein `ⓘ` via `st.help()` oder
`st.tooltip()`:

| Parameter | Hilfetext |
|---|---|
| pH | "Der pH-Wert sollte zwischen 7,2 und 7,6 liegen. Unter 7,0 korrosiv, über 8,0 schlechte Chlorwirkung." |
| Chlor | "Freies Chlor (mg/L). Soll zwischen 0,5 und 3,0 mg/L liegen. Teststreifen messen freies Chlor." |
| Alkalinität | "Säurepufferkapazität in mg/L CaCO₃. Verhindert pH-Schwankungen. Ziel: 80–120 mg/L." |
| Calciumhärte | "Calcium-Ionen in mg/L CaCO₃ (nicht Gesamthärte). Wichtig für LSI-Berechnung. Ziel: 150–250 mg/L." |
| Temperatur | "Wassertemperatur in °C. Beeinflusst LSI/RSI direkt." |

## Test-Strategie

Bestehende Tests (22 Stück) laufen weiter. Zusätzlich:

- Tests für neue Repository-Funktionen (pool CRUD, product CRUD, trinkwasser CRUD)
- Tests für Dosing-Logik mit DB-Produkten (statt hardcoded)
- Tests für Workflow-Verkettung (Aufgabe → Folgeaufgabe)
- Test für Datenmigration (config.toml → DB)

## Technische Randbedingungen

- Python 3.9+ (Host), 3.11+ (Docker)
- SQLite via SQLAlchemy (kein Wechsel)
- Streamlit + Plotly (bleibt)
- Kein Authentifizierung / Multi-User
- Parameter-Hilfetexte via st.markdown + CSS oder st.tooltip
