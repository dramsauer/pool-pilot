# Kalender Event-Popup + Retro-Form-Erweiterung — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add event-click popup to calendar with full task editing + extend retro form with product selection.

**Architecture:** Three independent changes: (1) new repo functions, (2) extend retro form, (3) add eventClick callback + st.dialog. Each builds on the previous.

**Tech Stack:** Python, Streamlit, SQLAlchemy, streamlit-calendar

---

### Task 1: Repository — delete_task + update_task

**Files:**
- Modify: `database/repository.py` (append at end)
- Test: `tests/test_repository.py`

- [ ] **Step 1: Write test for update_task**

```python
def test_update_task():
    session = setup()
    task = save_task(
        session, task_type="test", title="Original",
        due_date=datetime.date(2026, 7, 1),
    )
    updated = update_task(session, task.id, title="Geändert", due_date=datetime.date(2026, 7, 4))
    assert updated.title == "Geändert"
    assert updated.due_date == datetime.date(2026, 7, 4)
    session.close()
```

- [ ] **Step 2: Write test for delete_task**

```python
def test_delete_task():
    session = setup()
    task = save_task(
        session, task_type="test", title="Zu löschen",
        due_date=datetime.date.today(),
    )
    task_id = task.id
    delete_task(session, task_id)
    deleted = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    assert deleted is None
    session.close()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_repository.py::test_update_task tests/test_repository.py::test_delete_task -v`
Expected: FAIL (functions not defined)

- [ ] **Step 4: Add import + functions to repository.py**

Append `update_task` and `delete_task` to the import line at top and at end of file:

```python
def update_task(session: Session, task_id: int, **kwargs) -> MaintenanceTask | None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        session.commit()
    return task


def delete_task(session: Session, task_id: int) -> None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        session.delete(task)
        session.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_repository.py::test_update_task tests/test_repository.py::test_delete_task -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add database/repository.py tests/test_repository.py
git commit -m "feat: add update_task and delete_task repository functions"
```

---

### Task 2: Retro-Formular erweitern

**Files:**
- Modify: `pages/04_Kalender.py`

- [ ] **Step 1: Import get_products hinzufügen**

Add `get_products` to the import from `database.repository`.

- [ ] **Step 2: Products laden**

Nach `pools = get_pools(session)` und vor dem Retro-Formular:

```python
products = get_products(session)
```

- [ ] **Step 3: Product-Dropdown + Menge ins Retro-Formular einbauen**

Nach dem `retro_date`-Feld und vor `retro_done`:

```python
retro_product = st.selectbox(
    "Produkt", options=[None] + products,
    format_func=lambda p: "Kein Produkt" if p is None else f"{p.name} ({p.typ})",
    key="retro_product",
)
retro_amount = None
retro_unit = None
if retro_product is not None:
    default_amount = round(retro_product.dosage_factor * retro_pool.volume_liter / 1000, 1)
    col_amt, col_unit = st.columns([2, 1])
    with col_amt:
        retro_amount = st.number_input("Menge", value=default_amount, step=0.1, format="%.1f")
    with col_unit:
        retro_unit = st.text_input("Einheit", value=retro_product.unit)
```

- [ ] **Step 4: Product-Felder beim Speichern übernehmen**

Im `save_task`-Block, nach `executed_notes=retro_notes`:

```python
product_id=retro_product.id if retro_product else None,
product_name=retro_product.name if retro_product else None,
recommended_amount=retro_amount,
recommended_unit=retro_unit,
```

- [ ] **Step 5: Manuell testen**

Run: `streamlit run Wasserrechner.py`
Expected: Retro-Form zeigt Product-Dropdown + Mengenfeld, Speichern übernimmt die Werte.

- [ ] **Step 6: Commit**

```bash
git add pages/04_Kalender.py
git commit -m "feat: add product selection + amount to retro task form"
```

---

### Task 3: Event-Click Popup

**Files:**
- Modify: `pages/04_Kalender.py`

- [ ] **Step 1: Import get_task, update_task, delete_task hinzufügen**

Add to import from `database.repository`.

- [ ] **Step 2: extendedProps an Events anhängen**

```python
events.append({
    "title": t.title,
    "start": str(t.due_date),
    "end": str(t.due_date),
    "color": color,
    "allDay": True,
    "extendedProps": {"task_id": t.id},
})
```

- [ ] **Step 3: cal_result erfassen + eventClick auswerten**

```python
cal_result = st_calendar(
    events=events, options=cal_options,
    callbacks=["eventClick"], key="pool_calendar",
)

if cal_result is not None and cal_result.get("callback") == "eventClick":
    st.session_state.cal_selected_task_id = cal_result["eventClick"]["event"]["extendedProps"]["task_id"]
    st.rerun()
```

- [ ] **Step 4: Dialog-Block einfügen (vor st.divider())**

```python
if st.session_state.get("cal_selected_task_id"):
    task = get_task(session, st.session_state.cal_selected_task_id)
    if not task:
        st.session_state.cal_selected_task_id = None
        st.rerun()

    with st.dialog(f"✏️ {task.title}"):
        pool_name = next((p.name for p in pools if p.id == task.pool_id), "—")
        st.caption(f"Pool: {pool_name}")

        edit_title = st.text_input("Titel", value=task.title)
        edit_date = st.date_input("Datum", value=task.due_date or datetime.date.today())
        edit_completed = st.checkbox("Erledigt", value=task.completed)

        edit_product = st.selectbox(
            "Produkt",
            options=[None] + products,
            format_func=lambda p: "Kein Produkt" if p is None else f"{p.name} ({p.typ})",
            index=(0 if not task.product_id else next((i for i, p in enumerate([None] + products) if p and p.id == task.product_id), 0)),
        )
        edit_amount = task.actual_amount or task.recommended_amount
        edit_unit = task.actual_unit or task.recommended_unit or "g"
        col_amt, col_unit = st.columns([2, 1])
        with col_amt:
            edit_amount = st.number_input("Menge", value=edit_amount or 0.0, step=0.1, format="%.1f")
        with col_unit:
            edit_unit = st.text_input("Einheit", value=edit_unit)

        edit_notes = st.text_area("Notiz", value=task.executed_notes or "")

        if task.created_at:
            st.caption(f"Erstellt: {task.created_at.strftime('%d.%m.%Y %H:%M')}")
        if task.interval_days:
            st.caption(f"Intervall: alle {task.interval_days} Tage")

        col_save, col_delete, col_close = st.columns(3)
        with col_save:
            if st.button("💾 Speichern", use_container_width=True, type="primary"):
                update_kwargs = dict(
                    title=edit_title,
                    due_date=edit_date,
                    completed=edit_completed,
                    executed_notes=edit_notes,
                    actual_amount=edit_amount,
                    actual_unit=edit_unit,
                    product_id=edit_product.id if edit_product else None,
                    product_name=edit_product.name if edit_product else None,
                )
                if edit_completed and not task.completed:
                    update_kwargs["completed_at"] = datetime.datetime.now()
                elif not edit_completed:
                    update_kwargs["completed_at"] = None
                update_task(session, task.id, **update_kwargs)
                st.session_state.cal_selected_task_id = None
                st.rerun()
        with col_delete:
            if st.button("🗑 Löschen", use_container_width=True):
                delete_task(session, task.id)
                st.session_state.cal_selected_task_id = None
                st.rerun()
        with col_close:
            if st.button("❌ Schließen", use_container_width=True):
                st.session_state.cal_selected_task_id = None
                st.rerun()
```

- [ ] **Step 5: Manuell testen**

Run: `streamlit run Wasserrechner.py`
Expected: Klick auf Kalender-Event öffnet Dialog, Editieren/Erledigen/Löschen funktioniert.

- [ ] **Step 6: Commit**

```bash
git add pages/04_Kalender.py
git commit -m "feat: add event-click popup with full task editing and deletion"
```
