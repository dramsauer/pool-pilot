# Flexible Messwert-Architektur (EAV)

> **Problem:** Jeder neue messbare Parameter erfordert Schema-Migration + Änderungen an Model, Repository, UI, Verlauf und Konfiguration. Das ist spröde und fehleranfällig.

> **Lösung:** Entity-Attribute-Value (EAV) für Messwerte. Parameter werden in einer eigenen Tabelle definiert, Messwerte in einer Wertetabelle gespeichert. Neue Parameter = INSERT, kein Schema-Change.

---

## Datenmodell

### Neu: `parameters`

Zentrale Registrierung aller messbaren Parameter. Wird aus `config.toml` geseedet.

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | INTEGER PK | |
| name | VARCHAR(50) UNIQUE | Technischer Name (z. B. `"ph"`, `"chlorine"`) |
| display_name | VARCHAR(100) | Anzeigename (z. B. `"pH-Wert"`) |
| unit | VARCHAR(30) | Einheit (z. B. `"mg/L"`, `""`) |
| default_value | REAL | Startwert für Slider (nicht als "gemessen" behandelt) |
| sort_order | INTEGER | Reihenfolge für UI-Rendering |

Initial zu seedende Parameter: ph, chlorine, alkalinity, hardness, cya, bromine, salt, oxygen.

### Neu: `reading_values`

Ersetzt die festen Messwert-Spalten in `readings` (ph, chlorine, alkalinity, hardness, cya).

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | INTEGER PK | |
| reading_id | INTEGER FK → readings.id | |
| parameter_id | INTEGER FK → parameters.id | |
| value | REAL NOT NULL | Gemessener Wert |
| UNIQUE(reading_id, parameter_id) | | Ein Wert pro Parameter pro Messung |

### Neu: `instrument_capabilities`

Ersetzt die 8 Boolean-Spalten in `instruments` (can_measure_ph, can_measure_chlorine, …).

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | INTEGER PK | |
| instrument_id | INTEGER FK → instruments.id | |
| parameter_id | INTEGER FK → parameters.id | |
| UNIQUE(instrument_id, parameter_id) | | |

### Geändert: `readings`

**Entfernte Spalten:** `ph`, `chlorine`, `alkalinity`, `hardness`, `cya` (wandern in `reading_values`).

**Bleibt:** `id`, `pool_id`, `timestamp`, `temperature_c`, `lsi_value`, `rsi_value`, `csi_value`, `ccpp_value`, `dosing_recommendation`, `notes`.

Begründung: `temperature_c` ist kein Teststreifen-Parameter, sondern wird immer separat gemessen (Thermometer) und von allen Index-Berechnungen benötigt.

### Geändert: `instruments`

**Entfernte Spalten:** `can_measure_ph`, `can_measure_chlorine`, `can_measure_bromine`, `can_measure_alkalinity`, `can_measure_hardness`, `can_measure_cya`, `can_measure_salt`, `can_measure_oxygen`.

**Bleibt:** `id`, `name`, `brand`, `notes`.

---

## Config.toml Änderungen

```toml
[parameters]
  [parameters.ph]
  display_name = "pH-Wert"
  unit = ""
  default_value = 7.4
  sort_order = 10

  [parameters.chlorine]
  display_name = "Freies Chlor"
  unit = "mg/L"
  default_value = 1.5
  sort_order = 20

  [parameters.alkalinity]
  display_name = "Gesamtalkalinität"
  unit = "mg/L CaCO₃"
  default_value = 100
  sort_order = 30

  [parameters.hardness]
  display_name = "Gesamthärte"
  unit = "mg/L CaCO₃"
  default_value = 200
  sort_order = 40

  [parameters.cya]
  display_name = "Cyanursäure"
  unit = "mg/L"
  default_value = 0
  sort_order = 50

  [parameters.bromine]
  display_name = "Brom"
  unit = "mg/L"
  default_value = 0
  sort_order = 60

  [parameters.salt]
  display_name = "Salzgehalt (TDS)"
  unit = "mg/L NaCl"
  default_value = 500
  sort_order = 70

  [parameters.oxygen]
  display_name = "Sauerstoff"
  unit = "mg/L"
  default_value = 0
  sort_order = 80
```

Instrumente referenzieren Parameter stattdessen über eine Liste:

```toml
[instruments.pool_total_5in1]
name = "POOL Total 5 in 1"
brand = "POOL"
capabilities = ["ph", "chlorine", "alkalinity", "hardness", "cya"]
notes = "5 Parameter: pH, Chlor, Alk, CYA, Härte"
```

---

## Datenfluss

### Messung speichern

1. Nutzer wählt Instrument → UI zeigt Slider nur für dessen `capabilities`
2. Nutzer gibt Werte ein (Sliders) + Temperatur (separat)
3. `save_reading(session, pool_id, values={"ph": 7.4, "chlorine": 1.5, ...}, temperature_c=35, ...)`
4. Repository speichert:
   - `Reading` (mit pool_id, timestamp, temperature_c)
   - `ReadingValue` Einträge (einer pro Parameter in `values`)
5. Berechnungen (LSI/CSI/Dosing) laufen wie gehabt über ein `WaterTest(values, temperature_c)`

### Messung abrufen

- `get_readings()` gibt `Reading`-Objekte mit `.values`-Property (dict parameter_name → wert)
- Die Property joined `reading_values` + `parameters` und returned ein Dict

### Parameter in Berechnungen

- `WaterTest` bekommt `values: dict[str, float]` + benannte Properties (z. B. `ph → values["ph"]`) für Rückwärtskompatibilität des Dosing-Codes
- Fehlt ein benötigter Parameter: die betroffene Berechnung (LSI/CSI/Dosing-Schritt) wird übersprungen, der Nutzer sieht einen Hinweis welcher Wert fehlt
- `default_value` wird NIE als "echter" Messwert für Berechnungen verwendet – nur als Slider-Startwert

---

## UI-Änderungen

### Wasserrechner.py (dynamisch)

- Parameterliste kommt aus `Parameter`-Tabelle (gefiltert auf Sichtbare des Instruments)
- Slider werden in einer Schleife gerendert: `for cap in instrument.capabilities: slider(parameter.display_name, ...)`
- Anordnung: Reihenfolge aus `parameters`-Tabelle (sort_order)

### 02_Verlauf.py (dynamisch)

- DataFrame-Spalten aus vorhandenen `ReadingValue`-Keys
- Chart: Subplot pro Parameter (oder gruppiert wie bisher)
- Neue Parameter tauchen automatisch auf

### 01_Poolverwaltung.py (CRUD)

- Instrument-Edit zeigt Checkboxen dynamisch aus `parameters`-Tabelle
- Neues Instrument: alle Parameter als Checkboxen

---

## Migration

1. `parameters`-Tabelle anlegen und seeden
2. `reading_values`-Tabelle anlegen
3. `instrument_capabilities`-Tabelle anlegen
4. Daten aus `readings.ph`, `.chlorine`, `.alkalinity`, `.hardness`, `.cya` in `reading_values` kopieren
5. Alte Spalten aus `readings` droppen
6. Alte Boolean-Spalten aus `instruments` droppen
7. Bestehende `Instrument`-Einträge: Capabilities aus alten Booleans ableiten und in `instrument_capabilities` einfügen

---

## Nicht betroffen

- `pools`-Tabelle (unverändert)
- `trinkwasser`-Tabelle (ph_default, alkalinity_default, hardness_default bleiben als convenience)
- `products`, `maintenance_tasks`, `task_templates`, `photos` (unverändert)
- Export/Import (kopiert gesamte SQLite-DB, neue Tabellen kommen automatisch mit – `TABLE_CATEGORIES` muss um neue Tabellen erweitert werden)
