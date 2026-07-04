import datetime
import streamlit as st
from database.models import MaintenanceTask
from database.repository import get_task, save_task, update_task, delete_task


@st.dialog("✏️ Aufgabe")
def task_dialog(session, pools, products):
    state = st.session_state.get("task_dialog_state")
    if not state:
        return

    mode = state.get("mode")

    if mode == "edit":
        task = get_task(session, state["task_id"])
        if not task:
            st.session_state.task_dialog_state = None
            st.rerun()
        pool_name = next((p.name for p in pools if p.id == task.pool_id), "—")
        pool_id = task.pool_id
        is_new = False
    else:
        pool_id = state.get("pool_id")
        pool_name = next((p.name for p in pools if p.id == pool_id), "—")
        is_new = True

    st.caption(f"Pool: {pool_name}")

    edit_title = st.text_input("Titel", value=state.get("title", task.title if not is_new else ""))
    edit_date = st.date_input("Datum", value=state.get("due_date", task.due_date if not is_new else datetime.date.today()))
    edit_completed = st.checkbox("Erledigt", value=state.get("completed", task.completed if not is_new else False))

    prefill_product_name = state.get("product_name")
    prefill_product_id = state.get("product_id")
    default_product_index = 0
    if prefill_product_id:
        default_product_index = next((i for i, p in enumerate([None] + products) if p and p.id == prefill_product_id), 0)
    elif prefill_product_name and mode == "create":
        default_product_index = next((i for i, p in enumerate([None] + products) if p and p.name == prefill_product_name), 0)
    elif not is_new and task.product_id:
        default_product_index = next((i for i, p in enumerate([None] + products) if p and p.id == task.product_id), 0)

    edit_product = st.selectbox(
        "Produkt",
        options=[None] + products,
        format_func=lambda p: "Kein Produkt" if p is None else f"{p.name} ({p.typ})",
        index=default_product_index,
    )

    if not is_new:
        default_amount = task.actual_amount or task.recommended_amount
        default_unit = task.actual_unit or task.recommended_unit or "g"
    else:
        default_amount = state.get("recommended_amount")
        default_unit = state.get("recommended_unit", "g")

    col_amt, col_unit = st.columns([2, 1])
    with col_amt:
        edit_amount = st.number_input("Menge", value=default_amount or 0.0, step=0.1, format="%.1f")
    with col_unit:
        edit_unit = st.text_input("Einheit", value=default_unit)

    edit_notes = st.text_area("Notiz", value=state.get("notes", task.executed_notes if not is_new else ""))

    if not is_new and task.interval_days:
        st.caption(f"Intervall: alle {task.interval_days} Tage")

    col_save, col_delclose = st.columns(2)
    with col_save:
        if st.button("💾 Speichern", use_container_width=True, type="primary"):
            if is_new:
                save_task(
                    session,
                    task_type=state.get("task_type", "manual"),
                    title=edit_title,
                    description=edit_notes,
                    due_date=edit_date,
                    pool_id=pool_id,
                    product_id=edit_product.id if edit_product else None,
                    product_name=edit_product.name if edit_product else None,
                    recommended_amount=edit_amount,
                    recommended_unit=edit_unit,
                )
            else:
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
                update_task(session, state["task_id"], **update_kwargs)
            st.session_state.task_dialog_state = None
            st.rerun()
    with col_delclose:
        if not is_new and st.button("🗑 Löschen", use_container_width=True):
            delete_task(session, state["task_id"])
            st.session_state.task_dialog_state = None
            st.rerun()
        if st.button("❌ Schließen", use_container_width=True):
            st.session_state.task_dialog_state = None
            st.rerun()
