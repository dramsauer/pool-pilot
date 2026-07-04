import datetime
import streamlit as st
from streamlit_calendar import calendar as st_calendar
from database.db import get_engine, init_db, get_session
from database.models import MaintenanceTask
from utils.theme import inject_theme
from utils.nav import render_sidebar
from database.repository import (
    get_pools, get_products, get_tasks_by_date_range,
    complete_task_with_notes,
    ensure_template_instances,
)

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)
inject_theme()

engine = get_engine()
init_db(engine)
session = get_session(engine)

pools = get_pools(session)
products = get_products(session)
render_sidebar(pools)

st.title("📅 Aufgaben-Kalender")

selected_pool_id = st.session_state.get("pool_selector", 0)

with st.expander("📝 Aufgabe nachtragen"):
    with st.form("retro_task"):
        retro_pool = st.selectbox(
            "Pool", options=pools, format_func=lambda p: p.name,
            key="retro_pool"
        )
        retro_title = st.text_input("Titel", placeholder="z.B. ½ Chlor-Tablette zugegeben")
        retro_date = st.date_input("Datum", value=datetime.date.today())
        retro_product = st.selectbox(
            "Produkt", options=[None] + products,
            format_func=lambda p: "Kein Produkt" if p is None else f"{p.name} ({p.typ})",
            key="retro_product",
        )
        retro_amount = None
        retro_unit = None
        if retro_product is not None and retro_product.dosage_factor > 0:
            default_amount = round(retro_product.dosage_factor * retro_pool.volume_liter / 1000, 1)
            col_amt, col_unit = st.columns([2, 1])
            with col_amt:
                retro_amount = st.number_input("Menge", value=default_amount, step=0.1, format="%.1f")
            with col_unit:
                retro_unit = st.text_input("Einheit", value=retro_product.unit)
        retro_done = st.checkbox("Bereits erledigt", value=True)
        retro_notes = st.text_area("Notiz (optional)", placeholder="Details…")
        if st.form_submit_button("💾 Aufgabe eintragen"):
            if retro_title.strip():
                task = MaintenanceTask(
                    pool_id=retro_pool.id,
                    task_type="manual",
                    title=retro_title.strip(),
                    description=retro_notes,
                    due_date=retro_date,
                    completed=retro_done,
                    completed_at=datetime.datetime.combine(retro_date, datetime.time(12, 0)) if retro_done else None,
                    executed_notes=retro_notes,
                    product_id=retro_product.id if retro_product else None,
                    product_name=retro_product.name if retro_product else None,
                    recommended_amount=retro_amount,
                    recommended_unit=retro_unit,
                )
                session.add(task)
                session.commit()
                st.success(f"✅ Aufgabe für {retro_date.strftime('%d.%m.%Y')} eingetragen!")
                st.rerun()
            else:
                st.error("Bitte einen Titel eingeben.")

# Fetch tasks for the current month
today = datetime.date.today()
first_day = today.replace(day=1)
if today.month == 12:
    last_day = today.replace(day=31)
else:
    last_day = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)

pool_id_arg = None if selected_pool_id == 0 else selected_pool_id

ensure_template_instances(session, pool_id_arg, first_day, last_day)
tasks = get_tasks_by_date_range(session, first_day, last_day, pool_id_arg)

events = []
for t in tasks:
    if t.completed:
        color = "#2e7d32"
    elif t.template_id:
        color = "#1565c0"
    elif t.follow_up_days and t.follow_up_days > 0:
        color = "#e65100"
    else:
        color = "#c62828"
    events.append({
        "title": t.title,
        "start": str(t.due_date),
        "end": str(t.due_date),
        "color": color,
        "allDay": True,
    })

cal_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "",
    },
    "height": 600,
    "dayMaxEvents": 3,
}

st_calendar(events=events, options=cal_options, key="pool_calendar")

st.divider()
st.subheader("📋 Aufgaben des Monats")
if tasks:
    for t in tasks:
        pool_name = next((p.name for p in pools if p.id == t.pool_id), "—")
        status = "✅ Erledigt" if t.completed else "🔴 Offen"
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{t.title}**")
                details = f"📅 {t.due_date.strftime('%d.%m.%Y')} · {pool_name} · {status}"
                if t.recommended_amount is not None:
                    details += f" · Empfohlen: {t.recommended_amount:g} {t.recommended_unit or ''}"
                if t.actual_amount is not None:
                    details += f" · Gegeben: {t.actual_amount:g} {t.actual_unit or ''}"
                st.caption(details)
            with col2:
                if not t.completed:
                    notes = st.text_input(
                        "Notiz", key=f"notes_{t.id}", label_visibility="collapsed",
                        placeholder="Notiz…"
                    )
                    actual_amount = None
                    actual_unit = t.recommended_unit
                    if t.recommended_amount is not None:
                        actual_amount = st.number_input(
                            "Dosis", value=t.recommended_amount, step=0.1,
                            key=f"amt_cal_{t.id}", label_visibility="collapsed",
                            placeholder=f"Menge ({actual_unit or 'g'})",
                        )
                    if st.button("Erledigt", key=f"done_{t.id}"):
                        complete_task_with_notes(
                            session, t.id, notes,
                            actual_amount=actual_amount,
                            actual_unit=actual_unit,
                        )
                        st.rerun()
else:
    st.info("Keine Aufgaben in diesem Monat.")
