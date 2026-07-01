# Daten-Export / -Import

Export aller Daten als `.zip` (pool.db + Fotos) mit der Möglichkeit, aus einem Backup-ZIP zu importieren — mit wahlweisem Merge pro Kategorie.

## Motivation

- Datensicherung / Backup
- Migration zwischen Instanzen (lokal ↔ Docker)
- Wiederherstellung nach Datenverlust
- Teilweises Zusammenführen von Datensätzen aus verschiedenen Quellen

## Ort & Navigation

- **Neue Seite:** `pages/09_Datenverwaltung.py`
- **Navigation:** In `Wasserrechner.py` Sidebar ein `st.sidebar.expander("Weitere")` mit `st.page_link("pages/09_Datenverwaltung.py", label="🔐 Daten-Export/-Import")`
- Die Auto-Navigation von Streamlit listet die Seite am Ende (hohe Nummer = weniger prominent)

## Export

Der Export erstellt ein ZIP-Archiv des gesamten `data/`-Verzeichnisses.

**Technik:**
- `zipfile.ZipFile` schreibt `pool.db` + alle Dateien aus `photos/` in einen `io.BytesIO`
- `st.download_button(data=bytes_io.getvalue(), file_name=..., mime="application/zip")`
- Dateiname: `poolpilot-backup-YYYY-MM-DD.zip`

**UI:**
```
┌─ Daten exportieren ────────────────────────┐
│                                             │
│  📦 [ Vollständiges Backup herunterladen ]  │
│    pool.db + alle Fotos im ZIP              │
│                                             │
└─────────────────────────────────────────────┘
```

## Import

### User Flow

1. **ZIP-Upload** — `st.file_uploader` akzeptiert `.zip`
2. **Analyse** — ZIP wird inspiziert:
   - Existiert `pool.db`? (validierung)
   - Wenn nein: Fehler, kein Import möglich
   - Wenn ja: Importierte DB öffnen (separater SQLAlchemy Engine, read-only), Tabellen-Counts ermitteln
   - Vergleich mit aktueller DB (Anzahl pro Kategorie)
3. **Kategorie-Auswahl** — Pro Kategorie wählt der User:
   - **Ersetzen** — aktuelle Einträge löschen, importierte einfügen
   - **Zusammenführen** — per Key abgleichen, Duplikate überspringen, neue hinzufügen
   - **Überspringen** — Kategorie ignorieren
4. **Ausführen** — Bestätigungsdialog → Merge-Execution
5. **Ergebnis** — Zusammenfassung pro Kategorie

### Kategorien & Merge-Keys

| Kategorie | Beschreibung | Merge-Key |
|---|---|---|
| Pools | Pool-Konfigurationen | `name` |
| Produkte | Chemikalien | `name` |
| Instrumente | Messgeräte | `name` |
| Trinkwasser-Quellen | Leitungswasser-Analysen | `name` |
| Aufgaben-Vorlagen | TaskTemplates | `title` |
| Messwerte | Readings + zugehörige Photos | `timestamp` + `pool_id` |
| Aufgaben | MaintenanceTasks | `title` + `due_date` |

### Merge-Modi im Detail

**Ersetzen:**
- Alle aktuellen Records der Kategorie löschen (CASCADE via ORM)
- Alle importierten Records einfügen → neue IDs

**Zusammenführen:**
- Pro importierten Record: anhand des Merge-Keys in aktueller DB suchen
- Treffer → bestehenden Record behalten, ID-Mapping vormerken
- Kein Treffer → neuen Record einfügen, ID-Mapping vormerken

**Überspringen:**
- Keine Änderungen an dieser Kategorie
- ID-Mapping wird nicht aufgebaut → abhängige Kategorien können nicht importieren

### Abhängigkeits-Reihenfolge & ID-Remapping

Die Ausführung erfolgt strikt nach FK-Abhängigkeiten. Für jede Kategorie wird ein ID-Mapping aufgebaut: `id_map[kategorie][importierte_id] = aktuelle_id`.

```
1. Instruments        (keine FK-Abhängigkeiten)
2. Trinkwasser        (keine FK-Abhängigkeiten)
3. Products           (keine FK-Abhängigkeiten)
4. TaskTemplates      (keine FK-Abhängigkeiten)
5. Pools              (keine FK-Abhängigkeiten)
   ↓
6. PoolTaskDefaults   (FK: pools, task_templates) — automatisch
   ↓
7. Readings           (FK: pools → id_map["pools"])
   ↓
8. Photos             (FK: readings → id_map["readings"] + Dateien kopieren)
   ↓
9. MaintenanceTasks   (FK: pools, readings, products → id_map)
```

**Warnhinweis:** Wenn eine Eltern-Kategorie auf "Überspringen" gesetzt ist und eine Kind-Kategorie nicht, wird vor dem Import eine Warnung angezeigt.

### Fotos

- **Ersetzen:** Alte Dateien in `data/photos/` + DB-Einträge löschen → importierte Dateien kopieren + DB-Einträge anlegen
- **Zusammenführen:** Nach `reading_id` + Dateinamen abgleichen, neue hinzufügen
- **Überspringen:** Keine Änderung

### Transaktionsverhalten

Pro Kategorie einzeln transaktional — bei Fehler in einer Kategorie wird nur diese zurückgerollt, andere laufen weiter. Der User sieht eine detaillierte Ergebnisübersicht.

## UI-Layout

```
╔══════════════════════════════════════════════════╗
║  Daten-Export / -Import                          ║
║                                                  ║
║  ─── Export ─────────────────────────────────    ║
║  [Vollständiges Backup herunterladen]            ║
║                                                  ║
║  ─── Import ─────────────────────────────────    ║
║  [⬆ ZIP-Datei auswählen]   [Analysieren]        ║
║                                                  ║
║  ZIP-Inhalt: 3 Pools, 15 Produkte, ... 0 Fotos  ║
║                                                  ║
║  Kategorie          Aktuell  Import  Aktion       ║
║  ─────────────────  ───────  ──────  ───────     ║
║  Pools                  2        3  [Zusammenf. ▼]║
║  Produkte              10        8  [Ersetzen  ▼] ║
║  ...                                            ║
║                                                  ║
║  ⚠ Hinweis: "Messwerte" erfordert "Pools"-Import ║
║                                                  ║
║  [🚀 Import durchführen]                         ║
║                                                  ║
║  ─── Ergebnis ──────────────────────────         ║
║  ✅ Pools: 1 neu, 2 aktualisiert                 ║
║  ✅ Produkte: 8 ersetzt                          ║
║  ...                                             ║
╚══════════════════════════════════════════════════╝
```

## Neue & geänderte Dateien

| Datei | Änderung |
|---|---|
| `pages/09_Datenverwaltung.py` | **NEU** — Streamlit-UI für Export/Import |
| `utils/export_import.py` | **NEU** — Kernlogik (ZIP, Analyse, Merge) |
| `Wasserrechner.py` | **ÄNDERN** — Sidebar-Link "Weitere" hinzufügen |
| `tests/test_export_import.py` | **NEU** — Tests |

## Tests

- Export erzeugt gültiges ZIP mit korrektem Inhalt
- Import eines Exports → Roundtrip (Daten identisch)
- Merge-Modi: Replace / Merge / Skip
- ID-Remapping bei FK-Abhängigkeiten
- Fehlerfälle: kaputtes ZIP, fehlende `pool.db`, leere DB
- Teilweiser Import (eine Kategorie schlägt fehl, andere laufen durch)

## Fehlerbehandlung & Edge Cases

- **Ungültiges ZIP:** Fehlermeldung, kein Import
- **Schema-Version abweichend:** Warnhinweis (prüfbar via `_db_version` oder Tabellen-Struktur)
- **Dateikonflikte bei Fotos:** Bei Namensgleichheit automatischen Suffix anhängen
- **Große Uploads:** Kein hartes Limit (Streamlit-eigene Grenzen beachten)
- **DB-Verbindungsfehler:** Rollback pro Kategorie, klare Fehlermeldung
