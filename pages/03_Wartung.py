import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools,
    get_pending_tasks,
    complete_task_with_notes,
    save_task,
    get_pending_tasks_for_pool,
    get_active_templates_for_pool,
    ensure_template_instances,
)
from database.models import Product

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("✅ Aufgaben")

# Pool filter
pools = get_pools(session)
pool_filter = None
if len(pools) > 1:
    pool_options = {0: "Alle Pools"} | {p.id: p.name for p in pools}
    selected = st.selectbox(
        "Pool filtern",
        options=list(pool_options.keys()),
        format_func=lambda x: pool_options[x],
    )
    if selected:
        pool_filter = selected

# Ensure template instances for visible window
today = datetime.date.today()
ensure_template_instances(session, pool_filter or 0, today, today + datetime.timedelta(days=90))

# Quick-add presets
st.subheader("⚡ Schnell-Aufgabe")
templates_to_show = get_active_templates_for_pool(session, pool_filter) if pool_filter else []
if not pool_filter and pools:
    templates_to_show = get_active_templates_for_pool(session, pools[0].id)

if templates_to_show:
    categories = {}
    for t in templates_to_show:
        cat = t.category or "allgemein"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)

    cat_labels = {"chemie": "🧪 Chemie", "technik": "🔧 Technik", "reinigung": "🧹 Reinigung", "allgemein": "📋 Allgemein"}
    for cat, tmpls in categories.items():
        label = cat_labels.get(cat, cat)
        cols = st.columns(len(tmpls))
        for i, tmpl in enumerate(tmpls):
            with cols[i]:
                if st.button(f"{tmpl.icon} {tmpl.name}", key=f"qa_{tmpl.id}", use_container_width=True):
                    target_pool_id = pool_filter or (pools[0].id if pools else None)
                    rec_amount = None
                    rec_unit = None
                    if tmpl.product_id:
                        product = session.query(Product).filter(Product.id == tmpl.product_id).first()
                        if product and product.dosage_factor > 0 and target_pool_id:
                            p = next((p for p in pools if p.id == target_pool_id), None)
                            if p:
                                volume_m3 = p.volume_liter / 1000
                                rec_amount = round(product.dosage_factor * volume_m3, 1)
                                rec_unit = product.unit
                    save_task(
                        session,
                        task_type="template",
                        title=tmpl.name,
                        description=tmpl.description or "",
                        due_date=today,
                        interval_days=tmpl.interval_days,
                        template_id=tmpl.id,
                        pool_id=target_pool_id,
                        product_id=tmpl.product_id,
                        product_name=tmpl.product_name,
                        recommended_amount=rec_amount,
                        recommended_unit=rec_unit,
                    )
                    st.rerun()
else:
    st.caption("Keine Vorlagen aktiv. In Poolverwaltung aktivieren.")

st.divider()

# Task list
if pool_filter:
    tasks = get_pending_tasks_for_pool(session, pool_filter)
else:
    tasks = get_pending_tasks(session)

if not tasks:
    st.success("✅ Alle Aufgaben erledigt!")
else:
    for task in tasks:
        overdue = task.due_date and task.due_date < today
        is_today = task.due_date == today
        if overdue:
            icon = "🔴"
        elif is_today:
            icon = "🟡"
        else:
            icon = "🟢"

        with st.container(border=True):
            cols = st.columns([3, 1, 2])
            with cols[0]:
                st.write(f"{icon} **{task.title}**")
                if task.description:
                    st.caption(task.description)
                if task.completed_at:
                    st.caption(
                        f"✅ Erledigt: {task.completed_at.strftime('%d.%m.%Y %H:%M')}"
                    )
                if task.recommended_amount is not None:
                    st.caption(f"Empfohlen: {task.recommended_amount:g} {task.recommended_unit or ''}")
            with cols[1]:
                if task.due_date:
                    label = (
                        "Überfällig!"
                        if overdue
                        else ("Heute" if is_today else task.due_date.strftime("%d.%m.%Y"))
                    )
                    st.write(f"Fällig: {label}")
                if task.interval_days:
                    st.caption(f"Alle {task.interval_days} Tage")
                if task.follow_up_days:
                    st.caption(f"Folge in {task.follow_up_days} Tagen")
            with cols[2]:
                if not task.completed:
                    exec_notes = st.text_input(
                        "Doku",
                        placeholder="z. B. 100g zugegeben",
                        key=f"exec_{task.id}",
                    )
                    actual_amount = None
                    actual_unit = task.recommended_unit
                    if task.recommended_amount is not None:
                        actual_amount = st.number_input(
                            "Tatsächliche Dosis",
                            value=task.recommended_amount,
                            step=0.1,
                            key=f"amt_{task.id}",
                            label_visibility="collapsed",
                            placeholder=f"Menge ({actual_unit or 'g'})",
                        )
                    if st.button(
                        "✅ Erledigt", key=f"done_{task.id}", use_container_width=True
                    ):
                        complete_task_with_notes(
                            session, task.id,
                            executed_notes=exec_notes,
                            actual_amount=actual_amount,
                            actual_unit=actual_unit,
                        )
                        st.rerun()

st.divider()

# Manual task creation
with st.expander("➕ Manuelle Aufgabe"):
    with st.form("manuelle_aufgabe"):
        pools_for_new = {p.id: p.name for p in pools}
        sel_pool_id = st.selectbox(
            "Pool",
            options=list(pools_for_new.keys()),
            format_func=lambda x: pools_for_new[x],
        )
        title = st.text_input("Titel")
        description = st.text_area("Beschreibung")
        due_date = st.date_input("Fällig am", value=today)
        interval = st.number_input(
            "Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=0
        )
        follow_up = st.number_input(
            "Folgeaufgabe in (Tagen, 0 = keine)", min_value=0, value=0
        )
        if st.form_submit_button("Speichern"):
            save_task(
                session,
                task_type="custom",
                title=title,
                description=description,
                due_date=due_date,
                interval_days=interval,
            )
            if follow_up > 0:
                save_task(
                    session,
                    task_type="custom",
                    title=f"{title} (Folge)",
                    description=f"Folgeaufgabe in {follow_up} Tagen",
                    due_date=due_date + datetime.timedelta(days=follow_up),
                    interval_days=0,
                )
            st.success("Aufgabe gespeichert!")
            st.rerun()
