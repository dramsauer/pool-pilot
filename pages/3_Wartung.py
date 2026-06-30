import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools, get_pending_tasks, complete_task_with_notes,
    save_task, get_pending_tasks_for_pool,
)

st.set_page_config(page_title="Wartung", page_icon="✅")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("✅ Aufgaben")

# Pool filter
pools = get_pools(session)
pool_filter = None
if len(pools) > 1:
    pool_options = {0: "Alle Pools"} | {p.id: p.name for p in pools}
    selected = st.selectbox("Pool filtern", options=list(pool_options.keys()),
                            format_func=lambda x: pool_options[x])
    if selected:
        pool_filter = selected

if pool_filter:
    tasks = get_pending_tasks_for_pool(session, pool_filter)
else:
    tasks = get_pending_tasks(session)

if not tasks:
    st.success("✅ Alle Aufgaben erledigt!")
else:
    for task in tasks:
        overdue = task.due_date and task.due_date < datetime.date.today()
        today = task.due_date == datetime.date.today()
        if overdue:
            icon = "🔴"
        elif today:
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
                    st.caption(f"✅ Erledigt: {task.completed_at.strftime('%d.%m.%Y %H:%M')}")
            with cols[1]:
                if task.due_date:
                    label = "Überfällig!" if overdue else ("Heute" if today else task.due_date.strftime("%d.%m.%Y"))
                    st.write(f"Fällig: {label}")
                if task.interval_days:
                    st.caption(f"Alle {task.interval_days} Tage")
                if task.follow_up_days:
                    st.caption(f"Folge in {task.follow_up_days} Tagen")
            with cols[2]:
                if not task.completed:
                    exec_notes = st.text_input("Doku", placeholder="z. B. 100g zugegeben",
                                               key=f"exec_{task.id}")
                    if st.button("✅ Erledigt", key=f"done_{task.id}", use_container_width=True):
                        complete_task_with_notes(session, task.id, executed_notes=exec_notes)
                        st.rerun()

st.divider()

# Manual task creation
with st.expander("➕ Manuelle Aufgabe"):
    with st.form("manuelle_aufgabe"):
        pools_for_new = {p.id: p.name for p in pools}
        sel_pool_id = st.selectbox("Pool", options=list(pools_for_new.keys()),
                                   format_func=lambda x: pools_for_new[x])
        title = st.text_input("Titel")
        description = st.text_area("Beschreibung")
        due_date = st.date_input("Fällig am", value=datetime.date.today())
        interval = st.number_input("Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=0)
        follow_up = st.number_input("Folgeaufgabe in (Tagen, 0 = keine)", min_value=0, value=0)
        if st.form_submit_button("Speichern"):
            save_task(session, task_type="custom", title=title,
                      description=description, due_date=due_date,
                      interval_days=interval)
            if follow_up > 0:
                save_task(session, task_type="custom",
                          title=f"{title} (Folge)",
                          description=f"Folgeaufgabe in {follow_up} Tagen",
                          due_date=due_date + datetime.timedelta(days=follow_up),
                          interval_days=0)
            st.success("Aufgabe gespeichert!")
            st.rerun()
