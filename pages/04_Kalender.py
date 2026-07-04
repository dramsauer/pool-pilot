import datetime
import calendar
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.models import MaintenanceTask
from utils.theme import inject_theme
from utils.nav import render_sidebar
from database.repository import (
    get_pools, get_tasks_by_date_range,
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
render_sidebar(pools)

st.title("📅 Aufgaben-Kalender")

selected_pool_id = st.session_state.get("pool_selector", 0)

now = datetime.date.today()

with st.expander("📝 Aufgabe nachtragen"):
    with st.form("retro_task"):
        retro_pool = st.selectbox(
            "Pool", options=pools, format_func=lambda p: p.name,
            key="retro_pool"
        )
        retro_title = st.text_input("Titel", placeholder="z.B. ½ Chlor-Tablette zugegeben")
        retro_date = st.date_input("Datum", value=now)
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
                )
                session.add(task)
                session.commit()
                st.success(f"✅ Aufgabe für {retro_date.strftime('%d.%m.%Y')} eingetragen!")
                st.rerun()
            else:
                st.error("Bitte einen Titel eingeben.")

if "cal_year" not in st.session_state:
    st.session_state.cal_year = now.year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = now.month

nav = st.columns([1, 3, 1])
with nav[0]:
    if st.button("◀ Vorheriger"):
        if st.session_state.cal_month == 1:
            st.session_state.cal_month = 12
            st.session_state.cal_year -= 1
        else:
            st.session_state.cal_month -= 1
        st.rerun()

with nav[1]:
    month_name = datetime.date(
        st.session_state.cal_year, st.session_state.cal_month, 1
    ).strftime("%B %Y")
    st.markdown(f"<h3 style='text-align:center'>{month_name}</h3>", unsafe_allow_html=True)

with nav[2]:
    if st.button("Nächster ▶"):
        if st.session_state.cal_month == 12:
            st.session_state.cal_month = 1
            st.session_state.cal_year += 1
        else:
            st.session_state.cal_month += 1
        st.rerun()

# Fetch tasks for the month
first_day = datetime.date(st.session_state.cal_year, st.session_state.cal_month, 1)
last_day = datetime.date(
    st.session_state.cal_year, st.session_state.cal_month,
    calendar.monthrange(st.session_state.cal_year, st.session_state.cal_month)[1]
)
pool_id_arg = None if selected_pool_id == 0 else selected_pool_id

# Ensure template instances for visible month
ensure_template_instances(session, pool_id_arg, first_day, last_day)

tasks = get_tasks_by_date_range(session, first_day, last_day, pool_id_arg)

# Group tasks by date
tasks_by_date: dict[datetime.date, list] = {}
for t in tasks:
    if t.due_date not in tasks_by_date:
        tasks_by_date[t.due_date] = []
    tasks_by_date[t.due_date].append(t)

# Build calendar grid
cal = calendar.Calendar()
month_days = list(cal.itermonthdays(st.session_state.cal_year, st.session_state.cal_month))

html = """
<style>
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-header { text-align: center; font-weight: 700; padding: 6px; background: #f0f2f6; border-radius: 4px; font-size: 0.85rem; }
.cal-day { min-height: 80px; padding: 4px; border-radius: 4px; background: white; border: 1px solid #e0e0e0; font-size: 0.75rem; }
.cal-day.other-month { background: #fafafa; color: #bbb; }
.cal-day.today { border: 2px solid #4CAF50; }
.cal-day-num { font-weight: 600; margin-bottom: 2px; }
.task-dot { display: inline-block; width: 100%; padding: 1px 3px; margin: 1px 0; border-radius: 3px; font-size: 0.65rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: default; }
.task-dot.pending { background: #ffebee; color: #c62828; }
.task-dot.completed { background: #e8f5e9; color: #2e7d32; text-decoration: line-through; }
.task-dot.followup { background: #fff3e0; color: #e65100; }
.task-dot.template { background: #e3f2fd; color: #1565c0; }
</style>
<div class="cal-grid">
"""

for day_name in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
    html += f"<div class='cal-header'>{day_name}</div>"

for day in month_days:
    if day == 0:
        html += "<div class='cal-day other-month'></div>"
        continue
    d = datetime.date(st.session_state.cal_year, st.session_state.cal_month, day)
    classes = "cal-day"
    if d == now:
        classes += " today"
    html += f"<div class='{classes}'>"
    html += f"<div class='cal-day-num'>{day}</div>"
    if d in tasks_by_date:
        for t in tasks_by_date[d]:
            if t.completed:
                cls = "completed"
            elif t.template_id:
                cls = "template"
            else:
                cls = "pending"
            label = t.title[:20] + ("…" if len(t.title) > 20 else "")
            html += f"<div class='task-dot {cls}' title='{t.title}'>{label}</div>"
    html += "</div>"

html += "</div>"

st.components.v1.html(html, height=600, scrolling=True)

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
