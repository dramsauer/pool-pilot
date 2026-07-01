# Default Tasks für die Wartung

## Problemstellung

Die Wartungsseite (03_Wartung.py) und der Kalender (04_Kalender.py) zeigen nur Aufgaben, die entweder manuell angelegt oder dynamisch aus Dosierempfehlungen generiert wurden. Es fehlt ein System für:

1. **Wiederkehrende Standardaufgaben** (pH prüfen, Filter rückspülen, etc.)
2. **Schnellanlage** von häufigen Aufgaben per Klick
3. **Auto-Nachkontrolle** nach jeder Messung

## Datenmodell

### Neue Tabelle: `task_templates`

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | Integer PK | |
| name | String(200) | Anzeigename, z.B. "pH prüfen" |
| description | Text | Optionale Beschreibung |
| category | String(50) | "chemie", "reinigung", "technik", "allgemein" |
| interval_days | Integer | Standard-Intervall in Tagen (default: 7) |
| default_follow_up_days | Integer | Autom. Folgeaufgabe (default: 0) |
| pool_type | String(20) | "chlorine", "bromine", "all" |
| icon | String(10) | Emoji-Icon für Buttons |
| product_name | String(200) nullable | Produktname für Dosier-Templates (z.B. "pH-Minus") |
| product_id | Integer FK → products.id nullable | Aufgelöste Produkt-Referenz (beim Seed gematcht) |

### Neue Tabelle: `pool_task_defaults`

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | Integer PK | |
| pool_id | Integer FK → pools.id | |
| template_id | Integer FK → task_templates.id | |
| active | Boolean | default: True |
| custom_interval_days | Integer nullable | Überschreibt template.interval_days |

### Erweiterung: `maintenance_tasks`

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| template_id | Integer FK → task_templates.id nullable | Verknüpfung zum Template |
| recommended_amount | Float nullable | Vom System empfohlene Dosis |
| recommended_unit | String(20) nullable | Einheit (g, ml, Stk) |
| actual_amount | Float nullable | Tatsächlich gegebene Dosis (wird beim Erledigen erfasst) |
| actual_unit | String(20) nullable | Einheit der tatsächlichen Dosis |
| product_name | String(200) nullable | Produktname (denormalized, für Anzeige) |

### Erweiterung: `pools`

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| auto_measurement_task_days | Integer default=7 | Tage bis zur Auto-Nachkontrolle (0=deaktiviert) |

## Konfiguration (config.toml)

Neuer Abschnitt `[task_defaults]` mit Template-Definitionen. Wird beim DB-Seed in `task_templates` geladen (upsert by name).

```toml
[task_defaults]
templates = [
  { name = "pH prüfen", category = "chemie", interval_days = 7, pool_type = "all", icon = "🧪" },
  { name = "Chlor prüfen", category = "chemie", interval_days = 7, pool_type = "chlorine", icon = "🧪" },
  { name = "pH-Minus zugeben", category = "chemie", interval_days = 0, pool_type = "all", icon = "⚗️", product_name = "pH-Minus" },
  { name = "Chlor Tablette zugeben", category = "chemie", interval_days = 0, pool_type = "chlorine", icon = "💊", product_name = "Chlortabs" },
  { name = "Filter rückspülen", category = "technik", interval_days = 14, pool_type = "all", icon = "🔄" },
  { name = "Skimmer reinigen", category = "reinigung", interval_days = 7, pool_type = "all", icon = "🧹" },
  { name = "Pumpenvorsieb reinigen", category = "technik", interval_days = 7, pool_type = "all", icon = "🔧" },
  { name = "Poolboden saugen", category = "reinigung", interval_days = 14, pool_type = "all", icon = "🫧" },
  { name = "Wasserstand prüfen", category = "allgemein", interval_days = 7, pool_type = "all", icon = "📏" },
  { name = "Schockchlorung", category = "chemie", interval_days = 28, pool_type = "chlorine", icon = "⚡" },
  { name = "Vollanalyse (alle Werte)", category = "chemie", interval_days = 14, pool_type = "all", icon = "📊" },
  { name = "CYA prüfen", category = "chemie", interval_days = 30, pool_type = "chlorine", icon = "🧪" },
]
```

## Seeding (db.py)

- `init_db()` erstellt alle Tabellen
- Lädt Templates aus config.toml in `task_templates` (upsert by name)
- Dabei: `product_name` in Templates wird gegen `products`-Tabelle aufgelöst (Match by name) – bei Treffer wird `product_id` in `TaskTemplate` gesetzt (neue Spalte `product_id` FK)
- Beim Anlegen eines neuen Pools werden passende Templates (pool_type match oder "all") via `pool_task_defaults` aktiviert

## Recurring Task Generation

- Kein Pre-Generieren hunderter Instanzen
- Beim Aufruf von Wartung/Kalender: Prüfen, ob für das sichtbare Fenster bereits Instanzen in `maintenance_tasks` existieren
- Fehlende Instanzen werden on-the-fly generiert (Referenz: letzte completed Instanz oder Pool-Erstellungsdatum + interval_days)
- Beim Abschließen einer Template-Aufgabe: Nächste Instanz automatisch anlegen

## Quick-Add Presets (03_Wartung.py)

- Oberhalb der Aufgabenliste: Buttons gruppiert nach Kategorie
- Jeder Button erzeugt eine Aufgabe aus dem Template mit heutigem Datum
- Buttons zeigen icon + name, z.B. `🧪 pH prüfen`
- Bei Dosier-Templates (mit `product_name`): Aktuelle Dosis-Produktdaten aus products-Tabelle laden; `recommended_amount` und `recommended_unit` aus dem Produkt-Dosierfaktor und Pool-Volumen berechnen

## Produktverknüpfung in Tasks

- Beim Erstellen einer Aufgabe aus Dosierempfehlung (Wasserrechner.py): `product_id`, `product_name`, `recommended_amount`, `recommended_unit` setzen
- `TaskTemplate.product_name` wird beim Seed aufgelöst: Passendes Produkt aus `products`-Tabelle suchen und `product_id` im generierten Task setzen
- Bei Quick-Add aus einem Dosier-Template: Aktuellen Dosierfaktor + Poolvolumen verwenden, um empfohlene Menge zu berechnen

## Task-Completion mit Dosismenge (03_Wartung.py + 04_Kalender.py)

- Wenn ein Task `recommended_amount` gesetzt hat, zeigt das "Erledigt"-Formular zusätzlich ein Feld für die tatsächliche Dosis an:
  - Angezeigter Hinweis: "Empfohlen: {recommended_amount} {recommended_unit}"
  - Input-Feld: `actual_amount` (Zahl) und `actual_unit` (Dropdown/Pre-Fill)
  - Speichern in `actual_amount` / `actual_unit`
- Bestehende Tasks (ohne recommended_amount): Verhalten sich wie bisher (nur Notizfeld)
- In der History/Ansicht: Angezeigte Differenz zwischen empfohlener und tatsächlicher Dosis (z.B. "200g empfohlen, 150g gegeben")

## Auto-Measurement Task (Wasserrechner.py)

- Nach dem Speichern einer Messung: Wenn `pool.auto_measurement_task_days > 0`, Aufgabe "Nachkontrolle (Messung)" anlegen
- Fällig in `auto_measurement_task_days` Tagen
- Zusätzlich zu bestehenden Dosier-Folgeaufgaben

## Pool-Konfiguration (01_Poolverwaltung.py)

- Pool-Edit-Formular: Number-Input für `auto_measurement_task_days`
- Pool-Edit-Formular: Multi-Select oder Toggle-Liste für aktive Task-Templates

## Kalender-Integration (04_Kalender.py)

- Generierte Template-Instanzen erscheinen wie normale Aufgaben im Kalender
- Abschließen im Kalender erzeugt nächste Instanz
- Template-Aufgaben visuell erkennbar (eigenes CSS/Tag)
