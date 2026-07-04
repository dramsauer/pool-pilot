# Kalender — Event-Popup + Retro-Form-Erweiterung

**Datum:** 2026-07-04
**Sprache:** Deutsch (UI-Texte)
**Status:** Entwurf

---

## 1. Ziel

Bei Klick auf ein Kalender-Event öffnet sich ein Popup (`st.dialog`) mit allen Task-Details und Editieroptionen inkl. Erledigen/Löschen. Gleichzeitig wird das Retro-Formular um Produkt-Auswahl + Menge erweitert.

---

## 2. Datenhaltung

Zwei neue Repository-Funktionen in `database/repository.py`:

- `delete_task(session, task_id)` — Task aus DB löschen
- `update_task(session, task_id, **kwargs)` — Beliebige Felder überschreiben

Dem `create_task`-Aufruf im Retro-Formular `product_id`, `product_name`, `recommended_amount`, `recommended_unit` hinzufügen.

---

## 3. Retro-Formular (erweitert)

Bestehendes Formular in `04_Kalender.py` um folgende Felder ergänzen (nur sichtbar wenn Produkt gewählt):
- `retro_product`: Dropdown aus `get_products(session)`, erster Eintrag = "Kein Produkt"
- `retro_amount`: Zahl, default = berechnet aus `product.dosage_factor * pool.volume_liter / 1000`
- `retro_unit`: String, default = `product.unit`

---

## 4. Event-Klick Popup

### 4.1 Calendar → App

- Events erhalten `extendedProps: {"task_id": t.id}`
- `callbacks=["eventClick"]` an `st_calendar` übergeben
- Bei Klick: `task_id` in `session_state`, `st.rerun()`

### 4.2 Dialog-Layout

```python
if st.session_state.get("cal_selected_task_id"):
    task = get_task(session, st.session_state.cal_selected_task_id)
    with st.dialog(f"✏️ {task.title}"):
        # Pool (read-only), Datum, Erledigt-Checkbox
        # Produkt-Dropdown, Menge
        # Notiz (textarea)
        # Erstellt/Intervall (read-only, falls vorhanden)
        # Speichern, Löschen (mit Bestätigung), Schließen
```

### 4.3 Aktionen

| Aktion | Verhalten |
|---|---|
| Speichern | `update_task()` mit allen Feldern → session_state löschen → rerun |
| Erledigt umschalten | `completed` togglen, bei True: `completed_at = now()`, bei False: `completed_at = None` |
| Löschen | Bestätigungs-Checkbox → `delete_task()` → session_state löschen → rerun |
| Schließen | session_state löschen → rerun |

---

## 5. Repository-Änderungen

```python
def delete_task(session: Session, task_id: int) -> None:
    """Remove a task from the database entirely."""
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        session.delete(task)
        session.commit()

def update_task(session: Session, task_id: int, **kwargs) -> MaintenanceTask | None:
    """Update arbitrary fields on a task."""
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        session.commit()
    return task
```
