import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import save_task, get_pending_tasks, complete_task

st.set_page_config(page_title="Wartung", page_icon="📋")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("📋 Wartungsplan")

with st.expander("➕ Neue Aufgabe"):
    with st.form("neue_aufgabe"):
        task_type = st.selectbox("Typ", ["wasserwechsel", "filter_reinigen", "chemie_pruefen", "custom"])
        title = st.text_input("Titel")
        if task_type == "wasserwechsel":
            title = title or "Wasserwechsel"
        elif task_type == "filter_reinigen":
            title = title or "Filter reinigen"
        elif task_type == "chemie_pruefen":
            title = title or "Chemie prüfen"
        description = st.text_area("Beschreibung")
        due_date = st.date_input("Fällig am", value=datetime.date.today())
        interval_days = st.number_input("Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=3)
        if st.form_submit_button("Speichern"):
            save_task(session, task_type=task_type, title=title,
                      description=description, due_date=due_date,
                      interval_days=interval_days)
            st.success("Aufgabe gespeichert!")
            st.rerun()

st.subheader("Offene Aufgaben")
tasks = get_pending_tasks(session)
if not tasks:
    st.success("Alle Aufgaben erledigt! ✅")
else:
    for task in tasks:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            overdue = task.due_date and task.due_date < datetime.date.today()
            icon = "🔴" if overdue else "🟡"
            st.write(f"{icon} **{task.title}**")
            if task.description:
                st.caption(task.description)
        with col2:
            if task.due_date:
                st.write(f"Fällig: {task.due_date}")
            if task.interval_days:
                st.caption(f"Alle {task.interval_days} Tage")
        with col3:
            if st.button("✅ Erledigt", key=f"done_{task.id}"):
                complete_task(session, task.id)
                st.rerun()

st.page_link("app.py", label="← Zurück zum Dashboard", use_container_width=True)
