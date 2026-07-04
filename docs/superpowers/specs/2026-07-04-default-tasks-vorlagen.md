# Default Tasks & Vorlagen-Verwaltung

## Problem

Das System für wiederkehrende Standardaufgaben (TaskTemplates) wurde komplett implementiert (Modelle, Repository, UI-Code in Wartung/Kalender/Poolverwaltung), aber die Konfiguration in `config.toml` fehlt. Daher werden 0 Templates in die DB gesät, und die UI zeigt "Keine Vorlagen aktiv."

Zudem gibt es keine Möglichkeit, Templates zu erstellen/bearbeiten/löschen — sie können nur pro Pool aktiviert/deaktiviert werden.

## Lösung

### Phase A: config.toml befüllen

`[task_defaults]` Abschnitt in `config.toml` mit 11 Templates. Der Seed-Code in `db.py` (`_seed_task_templates`) existiert bereits und verarbeitet dieses Format.

Templates (12 Stück):

| Icon | Name | Kategorie | Intervall | Pool-Typ | Produkt |
|------|------|-----------|-----------|----------|---------|
| 🧪 | Hygiene-Messung (pH/Chlor) | chemie | 7 | all | — |
| 📊 | Vollanalyse (alle Werte) | chemie | 14 | all | — |
| 💊 | Chlor Tablette zugeben | chemie | 7 | chlorine | Chlortabs |
| ⚡ | Schockchlorung | chemie | 28 | chlorine | — |
| 🔄 | Filter rückspülen | technik | 14 | all | — |
| 🧽 | Filterpatrone reinigen | technik | 7 | all | — |
| 🔧 | Pumpenvorsieb reinigen | technik | 7 | all | — |
| 🧹 | Skimmer reinigen | reinigung | 7 | all | — |
| 🫧 | Poolboden saugen | reinigung | 14 | all | — |
| 🛡️ | Abdeckung reinigen | reinigung | 14 | all | — |
| 📏 | Wasserstand prüfen | allgemein | 7 | all | — |
| 💧 | Wasserwechsel (Teilweise) | allgemein | 28 | all | — |

### Phase B: Vorlagen-Tab in Aufgaben-Seite

Statt einer neuen Sidebar-Seite bekommt `03_Wartung.py` zwei Streamlit-Tabs:

**Tab 1: "✅ Aufgaben"** (bisheriger Inhalt, unverändert)
- Pool-Filter
- ⚡ Schnell-Aufgabe Buttons (aktive Templates des gewählten Pools)
- 📋 Ausstehende Aufgaben mit Erledigen-Button + Dosis-Erfassung
- ➕ Manuelle Aufgabe (Expander)

**Tab 2: "📋 Vorlagen"** (neuer CRUD-Bereich)
- Tabelle aller TaskTemplates mit Spalten: Icon, Name, Kategorie, Intervall, Pool-Typ, Aktionen
- "Neue Vorlage" Button → Formular (Name, Icon, Kategorie, Intervall, Pool-Typ, Produkt, Folgeaufgabe)
- Pro Zeile: Bearbeiten/Löschen Buttons
- Pro-Pool Aktivierung: kompakte Checkliste für jeden Pool

### Bestehende Integration (unverändert)

Die bereits implementierte Integration bleibt:
- **Poolverwaltung**: Checkboxen pro Template (wird jetzt sichtbar, da Templates existieren)
- **Kalender**: Template-Instanzen erscheinen blau markiert
- **Auto-Nachkontrolle**: Nach Messung wird "Nachkontrolle (Messung)"-Task erstellt
- **Dosier-Tasks**: Produktverknüpfte Templates berechnen empfohlene Dosis

## Datenmodell

Bestehend (unverändert, bereits implementiert):

- `task_templates` — Template-Definitionen (Name, Icon, Kategorie, Intervall, Pool-Typ, Produkt)
- `pool_task_defaults` — Welche Templates pro Pool aktiv sind
- `maintenance_tasks.template_id` — Verknüpfung zum Template
- `maintenance_tasks.recommended_amount/actual_amount` — Dosis-Erfassung
- `pools.auto_measurement_task_days` — Auto-Nachkontrolle Intervall

## Abgrenzung

- Keine Änderung an Datenmodell, Repository, oder Kalender
- Keine neue Sidebar-Seite — nur Tab innerhalb bestehender Seite
- Templates werden nicht automatisch für Brom-Pools aktiviert (kein Brom-Produkt konfiguriert)
