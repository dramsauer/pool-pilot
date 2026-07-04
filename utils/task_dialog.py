import datetime
import streamlit as st
from database.repository import get_task, update_task, delete_task


@st.dialog("✏️ Aufgabe bearbeiten")
def task_dialog(task_id, session, pools, products):
    task = get_task(session, task_id)
    if not task:
        st.session_state.cal_selected_task_id = None
        st.rerun()

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
