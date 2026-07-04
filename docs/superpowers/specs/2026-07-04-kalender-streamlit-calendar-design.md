# Kalender-Seite — streamlit-calendar Integration

**Datum:** 2026-07-04
**Sprache:** Deutsch (UI-Texte)
**Status:** Entwurf

---

## 1. Ziel

Ersetze die handgebaute HTML-Kalendergrid in `pages/04_Kalender.py` durch `streamlit-calendar` (FullCalendar-Wrapper). Die Seite wird dadurch schlanker und interaktiver.

---

## 2. Änderungen an `pages/04_Kalender.py`

### 2.1 Entfernen

| Komponente | Zeilen |
|---|---|
| Manuelle Monatsnavigation (3 Buttons + session_state) | ~30 |
| HTML/CSS-Kalendergrid + `st.components.v1.html` | ~50 |
| Aufgabenliste unterhalb des Kalenders | ~35 |
| `calendar`-Import | 1 |

### 2.2 Behalten

| Komponente | Grund |
|---|---|
| Retro-Formular (`st.expander`) | Manuelles Nachtragen von Aufgaben |
| `get_tasks_by_date_range` + `ensure_template_instances` | Datenbeschaffung |

### 2.3 Neu

| Komponente | Beschreibung |
|---|---|
| `streamlit_calendar` | Monatsansicht mit built-in Navigation |
| Event-Klick-Handler | Zeigt Task-Details + Completion-UI unterhalb des Kalenders |
| Datums-Klick-Handler | Öffnet Retro-Formular mit vorausgefülltem Datum |

---

## 3. Datenfluss

### 3.1 Tasks → Calendar Events

```python
events = []
for t in tasks:
    color = "green" if t.completed else "red"
    events.append({
        "title": t.title,
        "start": str(t.due_date),
        "end": str(t.due_date),
        "color": color,
        "allDay": True,
        "extendedProps": {"task_id": t.id, "pool_id": t.pool_id},
    })
```

Farbcodierung:
- `#2e7d32` (grün) = completed
- `#c62828` (rot) = pending
- `#1565c0` (blau) = template (ungemacht)
- `#e65100` (orange) = follow-up

### 3.2 Calendar → App (Callbacks)

```
dateClick  → st.session_state.cal_selected_date = datum
           → st.session_state.cal_show_retro = True
           → st.rerun()

eventClick → st.session_state.cal_selected_task_id = task.id
           → st.rerun()
```

### 3.3 Completion-UI (nach eventClick)

Unterhalb des Kalenders erscheint bei gesetztem `cal_selected_task_id`:

```
[Task: "½ Chlor-Tablette" | Datum: 04.07.2026 | Pool: Lay-Z-Spa]
[Notiz: ______________________________]
[Menge: [0.0] [g] ]
[✓ Erledigt] [✗ Abbrechen]
```

Bei Erfolg: `complete_task_with_notes()` → `cal_selected_task_id` zurücksetzen → `st.rerun()`.

---

## 4. Layout (final)

```
[Titel: 📅 Aufgaben-Kalender]
[📝 Aufgabe nachtragen ▼ — ausgeklappt bei dateClick, Datum vorausgefüllt]
[streamlit-calendar — Monatsansicht]
[─ Task-Detail + Completion — nur sichtbar nach eventClick ─]
```

---

## 5. Abhängigkeiten

`pyproject.toml` um `streamlit-calendar` ergänzen.

---

## 6. Offene Fragen

- Soll der Retro-Expander nach dateClick automatisch aufgeklappt sein (`expanded=True`) oder reicht Vorausfüllen? → Automatisch aufklappen.
- Soll die Completion-UI ein `st.dialog` oder ein normaler Bereich sein? → Normaler Bereich unterhalb des Kalenders (einfacher, kein Modal-Overhead).
